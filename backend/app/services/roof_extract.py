"""CPU image-to-vector extraction using OpenCV (Apache-2.0).

Image coordinates are percentages, origin TOP LEFT. Output roof coordinates
use a tight image bounding box, origin BOTTOM LEFT. No physical scale is guessed.
"""
from __future__ import annotations
import base64
import io
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


def data_url(image, ext=".png"):
    ok, data=cv2.imencode(ext,image)
    if not ok: raise ValueError("Không mã hóa được ảnh.")
    return "data:image/"+("jpeg" if ext==".jpg" else "png")+";base64,"+base64.b64encode(data).decode()


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
        mask=np.uint8((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD))
        algorithm='opencv_grabcut'
        notes.append("Tách vùng theo màu và cạnh; bóng, cây hoặc mái cùng màu có thể làm sai biên. Thêm điểm giữ/loại hoặc chấm biên để sửa.")
    else:raise ValueError("Phương pháp tách biên không hợp lệ.")
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
    bx,by,bw,bh=cv2.boundingRect(approx)
    # Keep exact tight pixel extents to avoid accidental independent X/Y stretching.
    ex,ey=max(1,bw-1),max(1,bh-1)
    polygon_image=[{'x':round(float(px)/w*100,5),'y':round(float(py)/h*100,5)} for px,py in approx]
    polygon_roof=[{'x':round(float(px-bx)/ex*100,5),'y':round((1-float(py-by)/ey)*100,5)} for px,py in approx]
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
        opening_roof.append([{'x':round(float(px-bx)/ex*100,5),'y':round((1-float(py-by)/ey)*100,5)} for px,py in ring])
    if opening_image:notes.append(f"Giữ {len(opening_image)} khoảng trống từ mặt nạ. Vùng tối cũng có thể bị nhận nhầm; kỹ sư phải kiểm tra trên ảnh.")
    overlay=image.copy();cv2.drawContours(overlay,[approx],-1,(60,190,245),2)
    tint=overlay.copy();cv2.fillPoly(tint,[approx],(70,180,90));overlay=cv2.addWeighted(overlay,.78,tint,.22,0)
    for shape in accepted:
        ring=np.int32(shape.exterior.coords)
        hole_mask=np.zeros((h,w),np.uint8);cv2.fillPoly(hole_mask,[ring],1)
        overlay[hole_mask.astype(bool)]=image[hole_mask.astype(bool)]
        cv2.polylines(overlay,[ring],True,(70,90,230),2)
    return {'algorithm':algorithm,'polygon_image_pct':polygon_image,'roof_polygon_pct':polygon_roof,'openings_image_pct':opening_image,'roof_openings_pct':opening_roof,'discarded_regions':len(significant),'roof_bbox_image_pct':[bx/w*100,by/h*100,ex/w*100,ey/h*100],
        'roof_aspect_ratio':ex/ey,'roof_width_px':ex,'roof_height_px':ey,'image_width_px':w,'image_height_px':h,
        'roof_crop_data_url':data_url(image[by:by+bh,bx:bx+bw],'.jpg'),'overlay_data_url':data_url(overlay,'.jpg'),
        'elapsed_ms':round((perf_counter()-start)*1000,1),'notes':notes+['Độ dài theo mét chỉ xác định sau khi hiệu chuẩn bằng số đo thật. Đây chưa phải kiểm chứng độ chính xác hình học ngoài hiện trường.']}
