"""CPU image-to-vector extraction using OpenCV (Apache-2.0).

Image coordinates are percentages, origin TOP LEFT. Output roof coordinates
use a tight image bounding box, origin BOTTOM LEFT. No physical scale is guessed.
"""
from __future__ import annotations
import base64
import io
import math
from typing import Literal
from time import perf_counter
import numpy as np
import cv2
from pydantic import Field
from app.schemas import StrictModel, NormalizedPoint
from app.services.vision import _image, VisionError

cv2.setNumThreads(2)


class TraceRequest(StrictModel):
    image_data_url: str = Field(max_length=18_000_000)
    input_kind: str = "drone"
    method: str = "grabcut"
    rect: list[float] = Field(default_factory=lambda:[5,5,90,90],min_length=4,max_length=4)
    foreground: list[NormalizedPoint] = Field(default_factory=list,max_length=100)
    background: list[NormalizedPoint] = Field(default_factory=list,max_length=100)
    polygon: list[NormalizedPoint] = Field(default_factory=list,max_length=100)
    openings: list[list[NormalizedPoint]] = Field(default_factory=list,max_length=24)
    quad: list[NormalizedPoint] = Field(default_factory=list,max_length=4)
    quad_aspect_ratio: float | None = Field(default=None,ge=.02,le=50)
    detail: float = Field(default=.003,ge=.0005,le=.02)
    straighten: bool = True
    # Photos of patched or two-tone roofs give ragged colour masks: 'orthogonal' snaps walls to right angles,
    # 'rectangle' keeps the smallest enclosing rectangle. Manual outlines are never reshaped.
    regularize: Literal['none','orthogonal','rectangle'] = 'none'


def _tidy_mask(mask,background,w,h,notes):
    """Colour masks of real roofs have pinholes and gaps where sheets, patches or shade differ in colour.
    Bridge narrow gaps, and fill every hole the user did not mark as background: a hole is a courtyard
    only when the engineer says so (a 'Loại nền' point inside it), never because a patch looked darker."""
    k=max(3,int(round(min(h,w)*.012))|1)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    contours,hierarchy=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    filled=0
    if hierarchy is not None:
        for i,entry in enumerate(hierarchy[0]):
            if entry[3]==-1:continue
            if any(cv2.pointPolygonTest(contours[i],(float(p.x*w/100),float(p.y*h/100)),False)>=0 for p in background):continue
            cv2.drawContours(mask,contours,i,1,-1);filled+=1
    if filled:notes.append(f"Đã lấp {filled} lỗ nhỏ do mái khác màu/bóng đổ. Sân trong thật: chấm 'Loại nền −' vào giữa sân rồi tách lại.")
    return mask


def _orthogonal(points,min_len):
    """Snap an outline whose walls run along the axes to a right-angled polygon.
    Each edge becomes horizontal or vertical at the length-weighted position of its pixels; steps shorter
    than min_len (ragged colour edges) are dropped. Returns None when no right-angled shape fits."""
    pts=np.asarray(points,np.float64);edges=[]
    for i in range(len(pts)):
        a,b=pts[i],pts[(i+1)%len(pts)];dx,dy=b-a;length=math.hypot(dx,dy)
        if length<1e-9:continue
        horizontal=abs(dx)>=abs(dy)
        edges.append(['h' if horizontal else 'v',(a[1]+b[1])/2 if horizontal else (a[0]+b[0])/2,length])
    def merge(items):
        i=0
        while len(items)>4 and i<len(items):
            j=(i+1)%len(items)
            if items[i][0]==items[j][0]:
                total=items[i][2]+items[j][2]
                items[i]=[items[i][0],(items[i][1]*items[i][2]+items[j][1]*items[j][2])/total,total];del items[j];i=0
            else:i+=1
        return items
    edges=merge(edges)
    while len(edges)>4:
        shortest=min(range(len(edges)),key=lambda k:edges[k][2])
        if edges[shortest][2]>=min_len:break
        del edges[shortest];edges=merge(edges)
    if len(edges)<4 or len(edges)%2:return None
    corners=[]
    for k,e in enumerate(edges):
        f=edges[(k+1)%len(edges)]
        if e[0]==f[0]:return None
        corners.append((e[1] if e[0]=='v' else f[1],e[1] if e[0]=='h' else f[1]))
    return np.asarray(corners)


def _regularize(approx,contour,mode,notes):
    from shapely.geometry import Polygon
    original=Polygon(approx)
    if mode=='rectangle':
        shaped=np.round(cv2.boxPoints(cv2.minAreaRect(contour))).astype(np.int32)
    else:
        skew=_skew_deg(approx);centre=tuple(float(v) for v in approx.mean(axis=0))
        matrix=cv2.getRotationMatrix2D(centre,skew,1);inverse=cv2.invertAffineTransform(matrix)
        turned=np.asarray(approx,np.float64)@matrix[:,:2].T+matrix[:,2]
        span=float(max(np.ptp(turned[:,0]),np.ptp(turned[:,1])))
        snapped=_orthogonal(turned,max(4.,.03*span))
        if snapped is None:
            notes.append("Chưa nắn được biên thành các cạnh vuông góc; giữ biên theo màu. Chọn 'Hình chữ nhật' hoặc chấm biên tay nếu cần.");return approx
        shaped=np.round(snapped@inverse[:,:2].T+inverse[:,2]).astype(np.int32)
    candidate=Polygon(shaped)
    if not candidate.is_valid or not original.area or not .8<=candidate.area/original.area<=1.25:
        notes.append("Biên nắn thẳng lệch quá nhiều so với vùng mái tìm được; giữ biên theo màu để kỹ sư kiểm tra.");return approx
    notes.append("Đã nắn biên thành "+("hình chữ nhật nhỏ nhất bao vùng mái." if mode=='rectangle' else f"{len(shaped)} cạnh vuông góc theo hướng tường chính (bỏ răng cưa do mái khác màu)."))
    return shaped


def data_url(image, ext=".png"):
    ok, data=cv2.imencode(ext,image)
    if not ok: raise ValueError("Không mã hóa được ảnh.")
    return "data:image/"+("jpeg" if ext==".jpg" else "png")+";base64,"+base64.b64encode(data).decode()


def _skew_deg(points):
    """Dominant wall direction of an outline (image coords, y down), in (-45, 45].
    Edges are weighted by length modulo 90°, so an L-shaped or stepped roof keeps its own axes.
    cv2.getRotationMatrix2D with this angle turns those walls onto the image axes.
    Returns 0 for outlines without a dominant direction (under 35 % of the perimeter)."""
    pts=np.asarray(points,np.float64).reshape(-1,2);d=np.roll(pts,-1,axis=0)-pts
    length=np.hypot(d[:,0],d[:,1]);angle=np.degrees(np.arctan2(d[:,1],d[:,0]))%90
    if len(pts)<3 or length.sum()<=0:return 0.
    gap=lambda a:(angle-a+45)%90-45
    best=max(np.arange(0,90,.5),key=lambda a:length[np.abs(gap(a))<=1.5].sum())
    near=np.abs(gap(best))<=1.5
    if length[near].sum()<.35*length.sum():return 0.
    skew=(best+np.average(gap(best)[near],weights=length[near]))%90
    return float(skew-90 if skew>45 else skew)


def _refine_band(image,mask,keep,drop,w,h):
    """Re-decide a band around a GrabCut edge by colour. GrabCut with a box alone tends to swell
    by 2-4 % of the image along soft or compressed edges, enough to fail the measured-frame check.
    Colour clusters come from the confident inside and from a ring just outside (not the whole
    photo), so textured sheet roofs and shaded parts keep several clusters each. The user's
    keep/remove points always win. Returns the GrabCut mask unchanged if refinement looks wrong."""
    band=max(4,round(min(h,w)*.02));kernel=np.ones((3,3),np.uint8)
    lab=cv2.cvtColor(image,cv2.COLOR_BGR2LAB).astype(np.float32);original=mask;current=mask.copy()
    def centres(pixels):
        pixels=pixels[::max(1,len(pixels)//4000)]
        k=min(3,len(pixels))
        _,_,c=cv2.kmeans(pixels,k,None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,20,.5),2,cv2.KMEANS_PP_CENTERS)
        return c
    for _ in range(3):
        inner=cv2.erode(current,kernel,iterations=band);outer=cv2.dilate(current,kernel,iterations=band)
        ring=(cv2.dilate(current,kernel,iterations=3*band)==1)&(outer==0)
        if inner.sum()<50 or ring.sum()<50:return original
        fg,bg=centres(lab[inner==1]),centres(lab[ring])
        edge=(outer==1)&(inner==0);pixels=lab[edge]
        near=lambda c:np.min(np.linalg.norm(pixels[:,None,:]-c[None],axis=2),axis=1)
        updated=current.copy();updated[edge]=near(fg)<near(bg)
        current=cv2.morphologyEx(updated,cv2.MORPH_OPEN,kernel)
    radius=max(2,int(min(h,w)*.008))
    for points,value in [(keep,1),(drop,0)]:
        for p in points:cv2.circle(current,(int(p.x*w/100),int(p.y*h/100)),radius,value,-1)
    before,after=int(original.sum()),int(current.sum())
    return current if before and .7<=after/before<=1.15 else original


def decode_image(url):
    try:
        header,payload=url.split(',',1)
        if not header.startswith('data:image/') or ';base64' not in header:
            raise ValueError()
        raw=base64.b64decode(payload,validate=True)
        from PIL import Image,ImageOps
        with Image.open(io.BytesIO(raw)) as image:
            if image.width*image.height>40_000_000: raise ValueError()
            image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((1200,1200))
            return cv2.cvtColor(np.array(image),cv2.COLOR_RGB2BGR)
    except Exception as exc:raise ValueError("Ảnh không hợp lệ hoặc quá lớn.") from exc


def prepare_image(data,mime):
    normalized=_image(data,mime)
    image=cv2.imdecode(np.frombuffer(normalized,np.uint8),cv2.IMREAD_COLOR)
    return {"image_data_url":data_url(image,'.jpg'),"width_px":image.shape[1],"height_px":image.shape[0]}


def extract_roof(req:TraceRequest):
    start=perf_counter();image=decode_image(req.image_data_url);h,w=image.shape[:2]
    cv2.setRNGSeed(0)   # GrabCut and k-means draw from OpenCV's shared RNG: same photo, same outline
    notes=[]
    if req.quad:
        if len(req.quad)!=4:raise ValueError("Chọn đủ bốn góc theo vòng quanh một mặt phẳng hình chữ nhật.")
        points=np.float32([[p.x*w/100,p.y*h/100] for p in req.quad])
        from shapely.geometry import Polygon
        if not Polygon(points).is_valid or not cv2.isContourConvex(points.astype(np.int32)):
            raise ValueError("Bốn góc hiệu chỉnh phải theo vòng, tạo tứ giác lồi.")
        width=max(np.linalg.norm(points[1]-points[0]),np.linalg.norm(points[2]-points[3]))
        height=max(np.linalg.norm(points[3]-points[0]),np.linalg.norm(points[2]-points[1]))
        if min(width,height)<10:raise ValueError("Vùng hiệu chỉnh quá nhỏ.")
        if req.quad_aspect_ratio is not None:
            # A homography alone cannot recover the real rectangle aspect ratio.
            ratio=req.quad_aspect_ratio
            longest=min(1200,max(width,height,20*max(ratio,1/ratio)))
            width,height=(longest,longest/ratio) if ratio>=1 else (longest*ratio,longest)
        nw,nh=max(20,int(width)),max(20,int(height))
        matrix=cv2.getPerspectiveTransform(points,np.float32([[0,0],[nw-1,0],[nw-1,nh-1],[0,nh-1]]))
        corrected=cv2.warpPerspective(image,matrix,(nw,nh))
        return {"rectified":True,"image_data_url":data_url(corrected,'.jpg'),"width_px":nw,"height_px":nh,"elapsed_ms":round((perf_counter()-start)*1000,1),"notes":["Đã hiệu chỉnh một mặt phẳng từ bốn góc. Tỷ lệ theo hai cạnh đã nhập nếu có; không hiệu chỉnh được nhiều mặt mái cùng lúc."]}
    x,y,rw,rh=req.rect
    if min(x,y)<0 or min(rw,rh)<1 or x+rw>100.01 or y+rh>100.01:
        raise ValueError("Khung chọn phải nằm trong ảnh và đủ lớn.")
    x0,y0=max(1,int(x*w/100)),max(1,int(y*h/100))
    x1,y1=min(w-1,int((x+rw)*w/100)),min(h-1,int((y+rh)*h/100))
    mask=np.zeros((h,w),np.uint8)
    if req.method=='manual':
        if len(req.polygon)<3:raise ValueError("Chọn ít nhất ba điểm biên trên ảnh.")
        pts=np.int32([[p.x*w/100,p.y*h/100] for p in req.polygon])
        from shapely.geometry import Polygon
        if not Polygon(pts).is_valid:raise ValueError("Biên chọn không được tự cắt.")
        cv2.fillPoly(mask,[pts],1)
        holes=[]
        for ring in req.openings:
            if len(ring)<3 or len(ring)>100:raise ValueError("Khoảng trống cần từ 3 đến 100 đỉnh.")
            hole=np.int32([[p.x*w/100,p.y*h/100] for p in ring])
            shape=Polygon(hole)
            if not shape.is_valid or shape.area<1 or not Polygon(pts).contains(shape):
                raise ValueError("Khoảng trống phải hợp lệ và nằm hoàn toàn bên trong biên mái.")
            if any(shape.intersects(previous) for previous in holes):raise ValueError("Các khoảng trống không được chồng hoặc chạm nhau.")
            holes.append(shape);cv2.fillPoly(mask,[hole],0)
        algorithm='manual_image_trace'
    elif req.method=='plan':
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        edges=cv2.Canny(gray,60,160)
        edges=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8),iterations=2)
        edges[:y0]=0;edges[y1:]=0;edges[:,:x0]=0;edges[:,x1:]=0
        contours,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        candidates=[c for c in contours if cv2.contourArea(c)>.015*w*h]
        if not candidates:raise ValueError("Chưa thấy đường viền khép kín. Khoanh sát mái hoặc dùng công cụ chấm biên.")
        cv2.drawContours(mask,[max(candidates,key=cv2.contourArea)],-1,1,-1)
        algorithm='opencv_canny_contours'
        notes.append("Đường nét bản vẽ có thể lẫn khung giấy/chữ; cần đối chiếu lớp phủ trước khi áp dụng.")
    elif req.method=='grabcut':
        mask[y0:y1,x0:x1]=cv2.GC_PR_FGD
        if req.polygon:
            mask[y0:y1,x0:x1]=cv2.GC_PR_BGD
            pts=np.int32([[p.x*w/100,p.y*h/100] for p in req.polygon])
            cv2.fillPoly(mask,[pts],cv2.GC_PR_FGD)
        radius=max(2,int(min(h,w)*.008))
        for points,value in [(req.foreground,cv2.GC_FGD),(req.background,cv2.GC_BGD)]:
            for p in points:cv2.circle(mask,(int(p.x*w/100),int(p.y*h/100)),radius,value,-1)
        try:
            cv2.grabCut(image,mask,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),4,cv2.GC_INIT_WITH_MASK)
        except cv2.error as exc:raise ValueError("Chưa tách được vùng mái. Chọn lại khung, thêm điểm giữ mái và loại nền.") from exc
        mask=_refine_band(image,np.uint8((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD)),req.foreground,req.background,w,h)
        algorithm='opencv_grabcut'
        notes.append("Tách vùng theo màu và cạnh; bóng, cây hoặc mái cùng màu có thể làm sai biên. Thêm điểm giữ/loại hoặc chấm biên để sửa.")
    else:raise ValueError("Phương pháp tách biên không hợp lệ.")
    if req.method=='grabcut':mask=_tidy_mask(mask,req.background,w,h,notes)
    contours,hierarchy=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:raise ValueError("Không tìm được vùng mái. Khoanh lại hoặc thêm điểm giữ mái.")
    external=[i for i,entry in enumerate(hierarchy[0]) if entry[3]==-1]
    main=max(external,key=lambda i:cv2.contourArea(contours[i]));contour=contours[main]
    significant=[i for i in external if i!=main and cv2.contourArea(contours[i])>=.003*h*w]
    if significant:notes.append(f"Có {len(significant)} vùng rời khác chưa đưa vào biên. Hãy trích riêng từng phần mái; không tự nối qua khoảng trống.")
    if cv2.contourArea(contour)<.003*h*w:raise ValueError("Vùng tìm được quá nhỏ; cần chọn lại mái.")
    tolerance=req.detail*cv2.arcLength(contour,True)
    approx=cv2.approxPolyDP(contour,tolerance,True).reshape(-1,2)
    while len(approx)>50:
        tolerance*=1.3;approx=cv2.approxPolyDP(contour,tolerance,True).reshape(-1,2)
    if len(approx)<3:raise ValueError("Đường biên chưa hợp lệ.")
    if req.regularize!='none' and req.method!='manual':approx=_regularize(approx,contour,req.regularize,notes)
    # A roof photographed at an angle has an axis-aligned box larger than its sides, so measured
    # width/length could never match it. Straighten the roof along its minimum-area rectangle;
    # the frame then measures the roof's own sides and the caller turns north by the same angle.
    skew=_skew_deg(approx) if req.straighten else 0.
    matrix=cv2.getRotationMatrix2D(tuple(float(v) for v in approx.mean(axis=0)),skew,1) if abs(skew)>=1 else None
    turn=(lambda pts:np.asarray(pts,np.float64)@matrix[:,:2].T+matrix[:,2]) if matrix is not None else (lambda pts:np.asarray(pts,np.float64))
    if matrix is None:
        skew=0.
        bx,by,bw,bh=cv2.boundingRect(approx)
        # Keep exact tight pixel extents to avoid accidental independent X/Y stretching.
        ex,ey=max(1,bw-1),max(1,bh-1)
        crop=image[by:by+bh,bx:bx+bw]
    else:
        straight=turn(approx);bx,by=(float(v) for v in straight.min(axis=0))
        ex,ey=(max(1.,float(v)) for v in straight.max(axis=0)-straight.min(axis=0))
        shifted=matrix.copy();shifted[:,2]-=(bx,by)
        crop=cv2.warpAffine(image,shifted,(int(np.ceil(ex))+1,int(np.ceil(ey))+1),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        notes.append(f"Mái nghiêng {abs(skew):.1f}° trong ảnh; bản vẽ đã được xoay thẳng theo cạnh mái và hướng Bắc xoay theo cùng góc.")
    frame=lambda pts:[{'x':round(float(px-bx)/ex*100,5),'y':round((1-float(py-by)/ey)*100,5)} for px,py in turn(pts)]
    polygon_image=[{'x':round(float(px)/w*100,5),'y':round(float(py)/h*100,5)} for px,py in approx]
    polygon_roof=frame(approx)
    # Preserve interior rings, and check simplified topology before returning.
    from shapely.geometry import Polygon
    outer_shape=Polygon(approx)
    if not outer_shape.is_valid:raise ValueError("Biên đơn giản hóa bị tự cắt; chọn nhiều chi tiết hơn hoặc sửa biên thủ công.")
    opening_image=[];opening_roof=[];accepted=[]
    for i,entry in enumerate(hierarchy[0]):
        if entry[3]!=main or cv2.contourArea(contours[i])<max(4,.0005*h*w):continue
        epsilon=max(.5,req.detail*cv2.arcLength(contours[i],True))
        ring=cv2.approxPolyDP(contours[i],epsilon,True).reshape(-1,2)
        while len(ring)>80:
            epsilon*=1.3;ring=cv2.approxPolyDP(contours[i],epsilon,True).reshape(-1,2)
        shape=Polygon(ring) if len(ring)>=3 else None
        if shape is None or not shape.is_valid or not outer_shape.contains(shape) or any(shape.intersects(p) for p in accepted):
            notes.append("Một khoảng trống có biên chưa hợp lệ; hãy kiểm tra và vẽ lại trước khi xác nhận.");continue
        if len(accepted)>=24:notes.append("Chỉ giữ tối đa 24 khoảng trống; cần kiểm tra phần còn lại.");break
        accepted.append(shape)
        opening_image.append([{'x':round(float(px)/w*100,5),'y':round(float(py)/h*100,5)} for px,py in ring])
        opening_roof.append(frame(ring))
    if opening_image:notes.append(f"Giữ {len(opening_image)} khoảng trống từ mặt nạ. Vùng tối cũng có thể bị nhận nhầm; kỹ sư phải kiểm tra trên ảnh.")
    overlay=image.copy();cv2.drawContours(overlay,[approx],-1,(60,190,245),2)
    tint=overlay.copy();cv2.fillPoly(tint,[approx],(70,180,90));overlay=cv2.addWeighted(overlay,.78,tint,.22,0)
    for shape in accepted:
        ring=np.int32(shape.exterior.coords)
        hole_mask=np.zeros((h,w),np.uint8);cv2.fillPoly(hole_mask,[ring],1)
        overlay[hole_mask.astype(bool)]=image[hole_mask.astype(bool)]
        cv2.polylines(overlay,[ring],True,(70,90,230),2)
    return {'algorithm':algorithm,'polygon_image_pct':polygon_image,'roof_polygon_pct':polygon_roof,'openings_image_pct':opening_image,'roof_openings_pct':opening_roof,'discarded_regions':len(significant),'roof_bbox_image_pct':[bx/w*100,by/h*100,ex/w*100,ey/h*100],
        'roof_aspect_ratio':ex/ey,'roof_width_px':ex,'roof_height_px':ey,'image_width_px':w,'image_height_px':h,'straighten_deg':round(skew,3),
        'roof_crop_data_url':data_url(crop,'.jpg'),'overlay_data_url':data_url(overlay,'.jpg'),
        'elapsed_ms':round((perf_counter()-start)*1000,1),'notes':notes+['Độ dài theo mét chỉ xác định sau khi hiệu chuẩn bằng số đo thật. Đây chưa phải kiểm chứng độ chính xác hình học ngoài hiện trường.']}
