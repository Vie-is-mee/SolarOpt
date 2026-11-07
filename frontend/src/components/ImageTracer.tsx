import {useEffect,useLayoutEffect,useRef,useState,type CSSProperties,type ReactNode,type SVGProps} from 'react'
import {studioApi} from '../services/studioApi'
import type {Point,TraceResult,CalibrationRecord} from '../studioTypes'
import {assessCalibration,pixelDistance,MAX_ROOF_SIDE_M} from '../imageCalibration'

type Tool='box'|'keep'|'remove'|'polygon'|'edit'|'opening'|'measure'|'check'|'quad'
export type TraceApplication={result:TraceResult;width:number;height:number;target:'roof'|'obstacle';calibrated:boolean;referenceLength?:number;sourceImage:string;calibrationRecord:CalibrationRecord}
type Shape='orthogonal'|'rectangle'|'none'
/** A brush stroke: centre line in image percent, radius as a fraction of the image width (what the server paints). */
type Stroke={points:Point[];radius:number}
type Ref={index:number;opening?:number}
type Drag={kind:'box-new';from:Point}|{kind:'box-move';from:Point;rect:number[]}|{kind:'box-resize';handle:string;rect:number[]}
 |({kind:'vertex'}&Ref)|{kind:'brush'}|{kind:'pan';x:number;y:number;left:number;top:number}
type Snapshot={rect:number[];outline:Point[];openings:Point[][];keep:Stroke[];drop:Stroke[];closed:boolean}

const EDGE_PX=48,EDGE_SPEED=18      // auto-scroll zone at the edge of the visible photo, and its top speed in px per frame
const ZOOMS=[1,1.5,2,3,4]
const HANDLE=10,CLOSE_PX=12          // vertex handle size and the distance that snaps onto the first vertex, screen px
const MAX_STROKES=80,MAX_STROKE_POINTS=400
const BOX_HANDLES=['nw','n','ne','e','se','s','sw','w']

const icon=(body:ReactNode)=><svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{body}</svg>
const brush=(sign:'+'|'-')=><><path d="M9.6 2.3l4.1 4.1-5 5-4.1-4.1z"/><path d="M4.6 7.3c-1.5.2-2.3 1.3-2.3 2.7 0 1.2-.5 2.2-1 3 2.6.5 4.9-.4 5.4-2.6"/><path d={sign==='+'?'M12 10.5v4M10 12.5h4':'M10 12.5h4'} strokeWidth="1.6"/></>
const TOOLS:{group:string;items:{id:Tool;label:string;key:string;icon:ReactNode}[]}[]=[
 {group:'Chọn vùng mái',items:[
  {id:'box',label:'Khung chọn',key:'V',icon:icon(<><path d="M2.5 4.5v-2h2M11.5 2.5h2v2M13.5 11.5v2h-2M4.5 13.5h-2v-2"/><rect x="5" y="5" width="6" height="6" strokeDasharray="1.6 1.4"/></>)},
  {id:'keep',label:'Cọ giữ mái',key:'B',icon:icon(brush('+'))},
  {id:'remove',label:'Cọ xóa nền',key:'E',icon:icon(brush('-'))}]},
 {group:'Đường biên',items:[
  {id:'polygon',label:'Bút vẽ biên',key:'P',icon:icon(<><path d="M2.5 13.5l1.6-4.7 6-6 3.1 3.1-6 6z"/><path d="M8.6 4.3l3.1 3.1"/><circle cx="5.6" cy="10.4" r=".8"/></>)},
  {id:'edit',label:'Sửa đỉnh',key:'A',icon:icon(<><path d="M3 2.5l8.5 4.8-3.6 1.1-1.3 3.7z" fill="currentColor" stroke="none"/><rect x="10.5" y="10.5" width="3" height="3"/></>)},
  {id:'opening',label:'Sân trong',key:'H',icon:icon(<><rect x="2" y="2.5" width="12" height="11" rx="1"/><rect x="5.5" y="6" width="5" height="4" strokeDasharray="1.4 1.2"/></>)}]},
 {group:'Đo và hiệu chỉnh',items:[
  {id:'measure',label:'Đo tham chiếu',key:'M',icon:icon(<><path d="M1.8 11.2l9.4-9.4 3 3-9.4 9.4z"/><path d="M4.5 8.5l1.3 1.3M6.6 6.4l1.3 1.3M8.7 4.3l1.3 1.3"/></>)},
  {id:'check',label:'Đo kiểm tra',key:'C',icon:icon(<><path d="M1.8 11.2l7-7 3 3-7 7z"/><path d="M10 12.2l1.6 1.6 3-3.4"/></>)},
  {id:'quad',label:'4 góc phối cảnh',key:'Q',icon:icon(<><path d="M3.5 4l9-1.5 1.5 10.5-12 .5z"/><circle cx="3.5" cy="4" r="1"/><circle cx="12.5" cy="2.5" r="1"/></>)}]},
]
const ALL_TOOLS=TOOLS.flatMap(g=>g.items)
const HINTS:Record<Tool,string>={
 box:'Kéo để vẽ khung mới bao quanh mái; kéo ô vuông ở góc/cạnh để đổi cỡ, kéo nút giữa hoặc viền khung để dời. Kéo tới mép khung nhìn thì ảnh tự cuộn theo.',
 keep:'Tô lên phần chắc chắn là mái, nhất là các mảng khác màu (tôn mới, vá, bóng đổ). [ và ] đổi cỡ cọ.',
 remove:'Tô lên cây, sân, mái nhà bên… cần loại khỏi vùng mái. [ và ] đổi cỡ cọ.',
 polygon:'Bấm lần lượt các góc mái. Bấm lại đỉnh đầu (hoặc Enter) để khép biên. Giữ Shift để vẽ thẳng theo 45°, Backspace bỏ đỉnh cuối.',
 edit:'Kéo ô vuông để dời đỉnh, kéo chấm giữa cạnh để thêm đỉnh. Chọn đỉnh rồi Delete (hoặc bấm đúp) để xóa.',
 opening:'Bấm các góc sân trong / giếng trời, bấm lại đỉnh đầu (hoặc Enter) để khép. Esc hủy vùng đang vẽ.',
 measure:'Bấm hai đầu một đoạn đã đo thật trên cùng mặt phẳng mái.',
 check:'Bấm hai đầu một đoạn đo độc lập và nhập chiều dài thật để đối chiếu tỷ lệ.',
 quad:'Bấm 4 góc theo vòng: trên trái → trên phải → dưới phải → dưới trái, chỉ cho một mặt phẳng hình chữ nhật.'}

export function ImageTracer({image,kind,measuredLong,measuredShort,onLongChange,onApply}:{image:string;kind:string;measuredLong?:number;measuredShort?:number;onLongChange?:(v:string)=>void;onApply:(v:TraceApplication)=>void|Promise<void>}){
 const [url,setUrl]=useState(''),[size,setSize]=useState({w:100,h:100}),[tool,setTool]=useState<Tool>('box')
 const [rect,setRect]=useState([5,5,90,90]),[outline,setOutline]=useState<Point[]>([]),[closed,setClosed]=useState(false),[measure,setMeasure]=useState<Point[]>([]),[quad,setQuad]=useState<Point[]>([])
 const [keep,setKeep]=useState<Stroke[]>([]),[drop,setDrop]=useState<Stroke[]>([]),[live,setLive]=useState<Stroke|null>(null),[brushPx,setBrushPx]=useState(16)
 const [result,setResult]=useState<TraceResult|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const [knownLength,setKnownLength]=useState(5),[useReference,setUseReference]=useState(false),[detail,setDetail]=useState(.003),[shape,setShape]=useState<Shape>(kind==='plan'?'none':'orthogonal'),[localLong,setLocalLong]=useState(''),[target,setTarget]=useState<'roof'|'obstacle'>(kind==='partial'?'obstacle':'roof')
 const [quadWidth,setQuadWidth]=useState(10),[quadDepth,setQuadDepth]=useState(8)
 const [openings,setOpenings]=useState<Point[][]>([]),[holeDraft,setHoleDraft]=useState<Point[]>([]),[check,setCheck]=useState<Point[]>([]),[checkLength,setCheckLength]=useState(0),[overlayOpacity,setOverlayOpacity]=useState(.18),[zoom,setZoom]=useState(1)
 const [hover,setHover]=useState<Point|null>(null),[selected,setSelected]=useState<Ref|null>(null),[shown,setShown]=useState(0),[panning,setPanning]=useState(false),[,setHistoryTick]=useState(0)
 const section=useRef<HTMLElement>(null),svg=useRef<SVGSVGElement>(null),stage=useRef<HTMLDivElement>(null),requestId=useRef(0)
 const drag=useRef<Drag|null>(null),stroke=useRef<{target:'keep'|'remove';stroke:Stroke}|null>(null),space=useRef(false)
 const engaged=useRef(false),pointer=useRef<{clientX:number;clientY:number}|null>(null),edgeFrame=useRef(0),zoomAnchor=useRef<{fx:number;fy:number;cx:number;cy:number}|null>(null)
 const edits=useRef<{past:Snapshot[];future:Snapshot[]}>({past:[],future:[]})
 const W=size.w,H=size.h,k=shown>0?shown/W:1,u=(px:number)=>px/k,X=(p:Point)=>p.x*W/100,Y=(p:Point)=>p.y*H/100
 const pts=(list:Point[])=>list.map(p=>`${X(p)},${Y(p)}`).join(' ')
 const ring=(list:Point[])=>'M'+list.map(p=>`${X(p)} ${Y(p)}`).join('L')+'Z'

 // ---- history -------------------------------------------------------------------------------
 const snapshot=():Snapshot=>structuredClone({rect,outline,openings,keep,drop,closed})
 function saveEdit(){edits.current.past.push(snapshot());edits.current.past=edits.current.past.slice(-60);edits.current.future=[];setHistoryTick(t=>t+1)}
 function undoEdit(redo=false){const from=redo?edits.current.future:edits.current.past,to=redo?edits.current.past:edits.current.future;const s=from.pop();if(!s)return;to.push(snapshot())
  setRect(s.rect);setOutline(s.outline);setOpenings(s.openings);setKeep(s.keep);setDrop(s.drop);setClosed(s.closed);setResult(null);setHoleDraft([]);setSelected(null);setHistoryTick(t=>t+1)}
 function clearAll(){saveEdit();setKeep([]);setDrop([]);setOutline([]);setClosed(false);setOpenings([]);setHoleDraft([]);setCheck([]);setMeasure([]);setQuad([]);setResult(null);setSelected(null)}

 useEffect(()=>{setTarget(kind==='partial'?'obstacle':'roof');setResult(null)},[kind])
 useEffect(()=>{let alive=true;requestId.current++;setResult(null);setOutline([]);setClosed(false);setOpenings([]);setHoleDraft([]);setCheck([]);setCheckLength(0);edits.current={past:[],future:[]};setKeep([]);setDrop([]);setMeasure([]);setQuad([]);setRect([5,5,90,90]);setError('');setSelected(null)
  if(image.startsWith('data:'))setUrl(image)
  else fetch(image).then(r=>r.blob()).then(b=>{const reader=new FileReader();reader.onload=()=>{if(alive)setUrl(String(reader.result))};reader.readAsDataURL(b)}).catch(()=>setError('Không đọc được ảnh nguồn.'))
  return()=>{alive=false}
 },[image])
 useEffect(()=>{if(!url)return;const im=new Image();im.onload=()=>setSize({w:im.naturalWidth,h:im.naturalHeight});im.src=url},[url])
 // Handles and lines keep their on-screen size at every zoom, so they need the photo's drawn width.
 useEffect(()=>{const el=svg.current;if(!el)return;const ro=new ResizeObserver(([entry])=>setShown(entry.contentRect.width));ro.observe(el);return()=>ro.disconnect()},[])
 useLayoutEffect(()=>{const w=svg.current?.getBoundingClientRect().width;if(w)setShown(w)},[size,zoom])
 useEffect(()=>()=>cancelAnimationFrame(edgeFrame.current),[])

 // ---- calibration (unchanged rules) -----------------------------------------------------------
 const distance=pixelDistance(measure,size.w,size.h)
 const calibrated=useReference&&distance>1&&knownLength>0
 // The long side of the roof comes from the project fields; a traced object (target 'obstacle') has its own.
 const typedLong=localLong.trim()?Number(localLong):undefined,long=target==='roof'?measuredLong??typedLong:typedLong
 const calibration=assessCalibration({pixelWidth:result?.roof_width_px||0,pixelHeight:result?.roof_height_px||0,measuredLong:long,measuredShort:target==='roof'?measuredShort:undefined,referencePixels:calibrated&&result?distance*result.image_width_px/size.w:0,referenceMetres:knownLength})
 // When a reference segment exists, the entered frame dimensions are checks,
 // never an independent scale that can distort the traced geometry.
 const actualWidth=calibration.width,actualHeight=calibration.height
 const checkPixels=pixelDistance(check,size.w,size.h)*(result?result.image_width_px/size.w:1),predictedCheck=checkPixels*calibration.scale
 const checkMismatch=check.length===2&&checkLength>0?Math.abs(predictedCheck-checkLength)/checkLength:0
 const scaleReady=calibrated||(long!==undefined&&Number.isFinite(long)&&long>=.1&&long<=MAX_ROOF_SIDE_M)
 // Only an impossible scale blocks. A disagreeing second side or check segment is shown as a warning:
 // the engineer decides, and the outline keeps the photo's proportions either way.
 const applyBlockedReason=busy?'Đang xử lý ảnh.':!scaleReady?'Nhập cạnh dài nhất của mái (hoặc đo một đoạn tham chiếu) để quy đổi ảnh ra mét.':!calibration.sound||actualWidth<.1||actualHeight<.1?'Chưa quy đổi được kích thước từ biên này; khoanh lại vùng mái.':Math.max(actualWidth,actualHeight)>MAX_ROOF_SIDE_M?`Mái dài hơn ${MAX_ROOF_SIDE_M} m; chia thành từng khu và trích riêng.`:''
 const warning=calibration.checked&&!calibration.acceptable?`Cạnh ngắn bạn nhập lệch ${(calibration.mismatch*100).toFixed(0)}% so với ảnh. Thường do biên ôm cả sân/mái nhà bên, ảnh chụp xiên, hoặc nhập nhầm số. Vẫn áp dụng được theo cạnh dài; nên xem lại lớp phủ xanh.`:checkMismatch>.03?`Đoạn kiểm tra lệch ${(checkMismatch*100).toFixed(1)}% so với tỷ lệ ảnh; nên kiểm tra lại trước khi xác nhận.`:''

 // ---- pointer geometry ------------------------------------------------------------------------
 function point(e:{clientX:number;clientY:number}):Point{const p=svg.current!.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const v=p.matrixTransform(svg.current!.getScreenCTM()!.inverse());return {x:Math.max(0,Math.min(100,v.x/W*100)),y:Math.max(0,Math.min(100,v.y/H*100))}}
 const drawnWidth=()=>svg.current?.getBoundingClientRect().width||shown
 const screenDist=(a:Point,b:Point)=>Math.hypot((a.x-b.x)*W/100,(a.y-b.y)*H/100)*Math.max(drawnWidth(),1)/W
 /** Shift: keep the new edge at a multiple of 45° from the previous vertex, measured in image pixels. */
 function constrain(p:Point,last:Point|undefined,shift:boolean):Point{
  if(!shift||!last)return p
  const dx=(p.x-last.x)*W/100,dy=(p.y-last.y)*H/100,a=Math.round(Math.atan2(dy,dx)/(Math.PI/4))*Math.PI/4,len=Math.hypot(dx,dy)
  return {x:Math.max(0,Math.min(100,last.x+Math.cos(a)*len*100/W)),y:Math.max(0,Math.min(100,last.y+Math.sin(a)*len*100/H))}
 }
 const last=(list:Point[])=>list[list.length-1]
 function capture(e:React.PointerEvent<SVGSVGElement>){try{e.currentTarget.setPointerCapture(e.pointerId)}catch{/* pointer already released */}}

 function addBrushPoint(p:Point){
  const s=stroke.current;if(!s)return
  const last=s.stroke.points[s.stroke.points.length-1]
  if(screenDist(last,p)<Math.max(2,brushPx*.3))return
  if(s.stroke.points.length>=MAX_STROKE_POINTS){commitStroke();stroke.current={target:s.target,stroke:{points:[last,p],radius:s.stroke.radius}}}
  else s.stroke={...s.stroke,points:[...s.stroke.points,p]}
  setLive(stroke.current!.stroke)
 }
 function commitStroke(){const s=stroke.current;if(!s)return;(s.target==='keep'?setKeep:setDrop)(list=>[...list,s.stroke].slice(-MAX_STROKES))}

 /** Moves whatever is being dragged to the pointer; false when nothing (or only the view) is being dragged. */
 function dragTo(at:{clientX:number;clientY:number}){
  const d=drag.current;if(!d)return false
  if(d.kind==='pan'){const s=stage.current;if(s){s.scrollLeft=d.left-(at.clientX-d.x);s.scrollTop=d.top-(at.clientY-d.y)}return false}
  const p=point(at)
  if(d.kind==='vertex'){if(d.opening===undefined)setOutline(a=>a.map((v,i)=>i===d.index?p:v));else setOpenings(a=>a.map((r,j)=>j===d.opening?r.map((v,i)=>i===d.index?p:v):r));return true}
  if(d.kind==='brush'){addBrushPoint(p);return true}
  if(d.kind==='box-new'){const s=d.from;setRect([Math.min(s.x,p.x),Math.min(s.y,p.y),Math.max(1,Math.abs(p.x-s.x)),Math.max(1,Math.abs(p.y-s.y))]);return true}
  if(d.kind==='box-move'){const [x,y,w,h]=d.rect;setRect([Math.max(0,Math.min(100-w,x+p.x-d.from.x)),Math.max(0,Math.min(100-h,y+p.y-d.from.y)),w,h]);return true}
  let [x1,y1]=d.rect,x2=d.rect[0]+d.rect[2],y2=d.rect[1]+d.rect[3]
  if(d.handle.includes('w'))x1=p.x;if(d.handle.includes('e'))x2=p.x;if(d.handle.includes('n'))y1=p.y;if(d.handle.includes('s'))y2=p.y
  setRect([Math.min(x1,x2),Math.min(y1,y2),Math.max(1,Math.abs(x2-x1)),Math.max(1,Math.abs(y2-y1))]);return true
 }
 // Dragging near (or past) the edge of the visible photo scrolls toward the pointer, the zoomed frame first and
 // then the page, and keeps the drag under the pointer, so a roof larger than the screen is cut in one stroke.
 function edgeScroll(){
  if(edgeFrame.current)return
  const tick=()=>{edgeFrame.current=0;const s=stage.current,at=pointer.current;if(!s||!at||!drag.current||drag.current.kind==='pan')return
   const r=s.getBoundingClientRect(),top=Math.max(r.top,0),bottom=Math.min(r.bottom,innerHeight),left=Math.max(r.left,0),right=Math.min(r.right,innerWidth)
   const push=(d:number)=>d>=EDGE_PX?0:Math.round(Math.min(1,(EDGE_PX-d)/EDGE_PX)*EDGE_SPEED)
   const dx=push(right-at.clientX)-push(at.clientX-left),dy=push(bottom-at.clientY)-push(at.clientY-top)
   if(!dx&&!dy)return
   const x0=s.scrollLeft,y0=s.scrollTop;s.scrollLeft+=dx;s.scrollTop+=dy
   let moved=s.scrollLeft!==x0||s.scrollTop!==y0
   if(s.scrollTop===y0&&dy&&(dy>0?r.bottom>innerHeight:r.top<0)){const page=scrollY;scrollBy(0,dy);moved=moved||scrollY!==page}
   if(!moved)return
   dragTo(at);edgeFrame.current=requestAnimationFrame(tick)}
  edgeFrame.current=requestAnimationFrame(tick)
 }
 function endDrag(){
  if(drag.current?.kind==='brush'){commitStroke();stroke.current=null;setLive(null)}
  if(drag.current?.kind==='pan')setPanning(false)
  drag.current=null;pointer.current=null;cancelAnimationFrame(edgeFrame.current);edgeFrame.current=0
 }

 // ---- tool actions -------------------------------------------------------------------------------
 function pick(id:Tool){
  if((id==='edit'||id==='opening')&&result){saveEdit();setOutline(result.polygon_image_pct);setOpenings(result.openings_image_pct||[]);setClosed(true);setResult(null)}
  if(id==='polygon'&&!outline.length)setClosed(false)
  setSelected(null);setTool(id)
 }
 function closeOutline(){if(outline.length>=3&&!closed){saveEdit();setClosed(true);setResult(null)}}
 function commitHole(){if(holeDraft.length<3)return;saveEdit();setOpenings(a=>[...a,holeDraft]);setHoleDraft([]);setResult(null)}
 function deleteSelected(){
  const s=selected;if(!s)return
  if(s.opening===undefined){if(outline.length<=3)return;saveEdit();setOutline(a=>a.filter((_,i)=>i!==s.index))}
  else{const r=openings[s.opening];saveEdit();setOpenings(a=>r&&r.length>3?a.map((ring,j)=>j===s.opening?ring.filter((_,i)=>i!==s.index):ring):a.filter((_,j)=>j!==s.opening))}
  setSelected(null);setResult(null)
 }
 function removeLastPoint(){
  if(tool==='opening'&&holeDraft.length){setHoleDraft(a=>a.slice(0,-1));return}
  if(tool==='polygon'&&outline.length){saveEdit();if(closed)setClosed(false);else setOutline(a=>a.slice(0,-1));setResult(null)}
 }
 function setZoomAt(next:number,at?:{clientX:number;clientY:number}){
  const s=stage.current,z=Math.max(ZOOMS[0],Math.min(ZOOMS[ZOOMS.length-1],next));if(!s||z===zoom)return
  const r=s.getBoundingClientRect(),cx=at?at.clientX-r.left:s.clientWidth/2,cy=at?at.clientY-r.top:s.clientHeight/2
  zoomAnchor.current={fx:(s.scrollLeft+cx)/Math.max(1,s.scrollWidth),fy:(s.scrollTop+cy)/Math.max(1,s.scrollHeight),cx,cy};setZoom(z)
 }
 const stepZoom=(dir:1|-1,at?:{clientX:number;clientY:number})=>setZoomAt(dir>0?ZOOMS.find(z=>z>zoom)??zoom:[...ZOOMS].reverse().find(z=>z<zoom)??zoom,at)
 // Keep the point under the cursor (or the centre) in place when the zoom changes.
 useLayoutEffect(()=>{const s=stage.current,a=zoomAnchor.current;if(!s||!a)return;zoomAnchor.current=null;s.scrollLeft=a.fx*s.scrollWidth-a.cx;s.scrollTop=a.fy*s.scrollHeight-a.cy},[zoom])

 function down(e:React.PointerEvent<SVGSVGElement>){
  if(busy)return
  const el=e.target as Element
  if(e.button===1||space.current){e.preventDefault();const s=stage.current!;drag.current={kind:'pan',x:e.clientX,y:e.clientY,left:s.scrollLeft,top:s.scrollTop};setPanning(true);capture(e);return}
  if(e.button!==0)return
  const p=point(e)
  if(tool==='box'){
   const handle=el.closest('[data-box]')?.getAttribute('data-box')
   saveEdit();setResult(null)
   drag.current=handle==='move'?{kind:'box-move',from:p,rect}:handle?{kind:'box-resize',handle,rect}:{kind:'box-new',from:p}
   capture(e);return
  }
  if(tool==='keep'||tool==='remove'){
   if(keep.length+drop.length>=MAX_STROKES){setError(`Đã đủ ${MAX_STROKES} nét cọ. Bấm "Tách biên từ vùng chọn" rồi xóa bớt nét để vẽ tiếp.`);return}
   saveEdit();setResult(null);setError('')
   stroke.current={target:tool,stroke:{points:[p],radius:Math.max(.001,Math.min(.15,brushPx/Math.max(1,drawnWidth())))}};setLive(stroke.current.stroke)
   drag.current={kind:'brush'};capture(e);return
  }
  if(tool==='polygon'){
   if(closed||(outline.length&&screenDist(last(outline),p)<3))return   // a double-click must not add a duplicate vertex
   if(outline.length>=3&&screenDist(outline[0],p)<=CLOSE_PX){closeOutline();return}
   saveEdit();setResult(null);setOutline(a=>[...a,constrain(p,a[a.length-1],e.shiftKey)]);return
  }
  if(tool==='edit'){
   const v=el.closest('[data-vertex]'),m=el.closest('[data-mid]')
   const ringOf=(node:Element)=>node.hasAttribute('data-ring')?Number(node.getAttribute('data-ring')):undefined
   if(v){const ref={index:Number(v.getAttribute('data-vertex')),opening:ringOf(v)};saveEdit();setSelected(ref);drag.current={kind:'vertex',...ref};setResult(null);capture(e);return}
   if(m){
    const i=Number(m.getAttribute('data-mid')),opening=ringOf(m);saveEdit();setResult(null)
    if(opening===undefined)setOutline(a=>[...a.slice(0,i+1),p,...a.slice(i+1)])
    else setOpenings(a=>a.map((r,j)=>j===opening?[...r.slice(0,i+1),p,...r.slice(i+1)]:r))
    const ref={index:i+1,opening};setSelected(ref);drag.current={kind:'vertex',...ref};capture(e);return
   }
   setSelected(null);return
  }
  if(tool==='opening'){
   if(holeDraft.length&&screenDist(last(holeDraft),p)<3)return
   if(holeDraft.length>=3&&screenDist(holeDraft[0],p)<=CLOSE_PX){commitHole();return}
   setHoleDraft(a=>[...a,constrain(p,a[a.length-1],e.shiftKey)]);return
  }
  if(tool==='measure'){setMeasure(a=>a.length>=2?[p]:[...a,p]);return}
  if(tool==='check'){setCheck(a=>a.length>=2?[p]:[...a,p]);return}
  setQuad(a=>a.length>=4?[p]:[...a,p])
 }
 function move(e:React.PointerEvent<SVGSVGElement>){
  pointer.current={clientX:e.clientX,clientY:e.clientY}
  if(tool!=='box'&&tool!=='edit')setHover(point(e))
  if(dragTo(e))edgeScroll()
 }

 // ---- keyboard and wheel (latest handler through a ref, listeners attached once) -------------------
 const keyHandler=useRef<(e:KeyboardEvent)=>void>(()=>{}),wheelHandler=useRef<(e:WheelEvent)=>void>(()=>{})
 keyHandler.current=e=>{
  const root=section.current
  if(!root||busy||(e.target as HTMLElement).closest?.('input,select,textarea,[contenteditable="true"]'))return
  if(!engaged.current&&!root.matches(':hover')&&!root.contains(document.activeElement))return
  const ctrl=e.ctrlKey||e.metaKey,key=e.key.toLowerCase()
  if(e.type==='keyup'){if(e.key===' ')space.current=false;return}
  if(e.key===' '){space.current=true;e.preventDefault();return}
  if(ctrl&&key==='z'){e.preventDefault();undoEdit(e.shiftKey);return}
  if(ctrl&&key==='y'){e.preventDefault();undoEdit(true);return}
  if(ctrl)return
  const shortcut=ALL_TOOLS.find(t=>t.key.toLowerCase()===key)
  if(shortcut){e.preventDefault();pick(shortcut.id);return}
  if(e.key==='['||e.key===']'){e.preventDefault();setBrushPx(b=>Math.max(4,Math.min(60,b+(e.key===']'?2:-2))));return}
  if(e.key==='+'||e.key==='='){e.preventDefault();stepZoom(1);return}
  if(e.key==='-'){e.preventDefault();stepZoom(-1);return}
  if(e.key==='0'){e.preventDefault();setZoomAt(1);return}
  if(e.key==='Enter'){if(tool==='polygon'){e.preventDefault();closeOutline()}else if(tool==='opening'){e.preventDefault();commitHole()}return}
  if(e.key==='Escape'){setHoleDraft([]);setSelected(null);return}
  if(e.key==='Backspace'||e.key==='Delete'){e.preventDefault();if(tool==='edit')deleteSelected();else removeLastPoint()}
 }
 wheelHandler.current=e=>{if(!(e.ctrlKey||e.metaKey))return;e.preventDefault();stepZoom(e.deltaY<0?1:-1,e)}
 useEffect(()=>{
  const onKey=(e:KeyboardEvent)=>keyHandler.current(e),onWheel=(e:WheelEvent)=>wheelHandler.current(e),s=stage.current
  const onPress=(e:PointerEvent)=>{engaged.current=!!section.current?.contains(e.target as Node)}
  window.addEventListener('keydown',onKey);window.addEventListener('keyup',onKey);window.addEventListener('pointerdown',onPress,true);s?.addEventListener('wheel',onWheel,{passive:false})
  return()=>{window.removeEventListener('keydown',onKey);window.removeEventListener('keyup',onKey);window.removeEventListener('pointerdown',onPress,true);s?.removeEventListener('wheel',onWheel)}
 },[])

 async function trace(method:string){const id=++requestId.current;setBusy(true);setError('');try{const r=await studioApi.trace({image_data_url:url,input_kind:kind,method,rect,keep_strokes:keep,drop_strokes:drop,regularize:shape,polygon:outline,openings:method==='manual'?openings:[],quad:method==='rectify'?quad:[],quad_aspect_ratio:method==='rectify'?quadWidth/quadDepth:null,detail});
  if(id!==requestId.current)return;
  if(r.rectified&&r.image_data_url){setUrl(r.image_data_url);setRect([2,2,96,96]);setKeep([]);setDrop([]);setOutline([]);setClosed(false);setOpenings([]);setHoleDraft([]);setCheck([]);setMeasure([]);edits.current={past:[],future:[]};setQuad([]);setResult(null);setTool('box')}
  else setResult(r)
 }catch(e){setError(e instanceof Error?e.message:'Chưa trích được biên.')}finally{setBusy(false)}}

 // ---- drawing helpers (image pixel space; UI strokes keep their screen width) ----------------------
 const ui={vectorEffect:'non-scaling-stroke' as const}
 const square=(p:Point,px:number,props:SVGProps<SVGRectElement>)=><rect x={X(p)-u(px)/2} y={Y(p)-u(px)/2} width={u(px)} height={u(px)} {...ui} {...props}/>
 const dot=(p:Point,px:number,props:SVGProps<SVGCircleElement>)=><circle cx={X(p)} cy={Y(p)} r={u(px)} {...ui} {...props}/>
 const strokePath=(s:Stroke)=>'M'+s.points.map(p=>`${X(p)} ${Y(p)}`).join('L')+(s.points.length===1?'l.01 0':'')
 const brushLayer=(list:Stroke[],color:string)=>list.map((s,i)=><path key={i} d={strokePath(s)} fill="none" stroke={color} strokeOpacity=".5" strokeWidth={2*s.radius*W} strokeLinecap="round" strokeLinejoin="round" pointerEvents="none"/>)
 const shownOutline=result?.polygon_image_pct||outline,shownOpenings=result?.openings_image_pct||openings
 const nearFirst=(list:Point[])=>!!hover&&list.length>=3&&screenDist(list[0],hover)<=CLOSE_PX
 const rubber=(from:Point|undefined,color:string)=>from&&hover?<line x1={X(from)} y1={Y(from)} x2={X(hover)} y2={Y(hover)} stroke={color} strokeWidth="1.5" strokeDasharray="5 4" {...ui} pointerEvents="none"/>:null
 const toolLabel=ALL_TOOLS.find(t=>t.id===tool)!.label
 const cursorClass=panning?'panning':space.current?'pan-ready':`tool-${tool}`

 return <section ref={section} className="image-tracer">
  <div className="tracer-heading"><div><h3>Trích biên đúng theo ảnh</h3><p>Khoanh sát mái → tách vùng → so lớp phủ → hiệu chuẩn số đo.</p></div><span>OpenCV · CPU</span></div>
  <div className="tracer-toolbar" role="toolbar" aria-label="Công cụ trích biên">
   {TOOLS.map(g=><div className="tool-group" key={g.group}><span>{g.group}</span><div>{g.items.map(t=><button key={t.id} type="button" className={tool===t.id?'active':''} aria-pressed={tool===t.id} title={`${t.label} (phím ${t.key})`} disabled={busy} onClick={()=>pick(t.id)}>{t.icon}<span>{t.label}</span><kbd>{t.key}</kbd></button>)}</div></div>)}
   <div className="tool-group"><span>Lịch sử</span><div>
    <button type="button" title="Hoàn tác (Ctrl+Z)" disabled={busy||!edits.current.past.length} onClick={()=>undoEdit()}>{icon(<path d="M5.5 4L2.5 7l3 3M2.8 7H10a3.5 3.5 0 010 7H7"/>)}<span>Hoàn tác</span></button>
    <button type="button" title="Làm lại (Ctrl+Y)" disabled={busy||!edits.current.future.length} onClick={()=>undoEdit(true)}>{icon(<path d="M10.5 4l3 3-3 3M13.2 7H6a3.5 3.5 0 000 7h3"/>)}<span>Làm lại</span></button>
   </div></div>
  </div>
  <div className="tracer-options">
   {(tool==='keep'||tool==='remove')&&<><label className="brush-size">Cỡ cọ<input aria-label="Cỡ cọ" type="range" min="4" max="60" step="1" value={brushPx} onChange={e=>setBrushPx(Number(e.target.value))}/><output>{brushPx} px</output></label>
    <span className="brush-swatch keep"/>Nét giữ: {keep.length}<button type="button" className="text-button" disabled={busy||!keep.length} onClick={()=>{saveEdit();setKeep([]);setResult(null)}}>Xóa</button>
    <span className="brush-swatch remove"/>Nét loại: {drop.length}<button type="button" className="text-button" disabled={busy||!drop.length} onClick={()=>{saveEdit();setDrop([]);setResult(null)}}>Xóa</button></>}
   {tool==='polygon'&&<><span>{outline.length} đỉnh{closed?' · đã khép':''}</span><button type="button" className="button secondary small" disabled={busy||closed||outline.length<3} onClick={closeOutline}>Khép biên (Enter)</button><button type="button" className="button secondary small" disabled={busy||!outline.length} onClick={removeLastPoint}>Bỏ đỉnh cuối (Backspace)</button></>}
   {tool==='edit'&&<><span>{selected?`Đang chọn đỉnh ${selected.index+1}${selected.opening!==undefined?` của sân trong ${selected.opening+1}`:''}`:'Chưa chọn đỉnh'}</span><button type="button" className="button secondary small" disabled={busy||!selected} onClick={deleteSelected}>Xóa đỉnh (Delete)</button></>}
   {tool==='opening'&&<><span>{holeDraft.length} đỉnh đang vẽ · {openings.length} sân trong</span><button type="button" className="button secondary small" disabled={busy||holeDraft.length<3} onClick={commitHole}>Khép sân trong (Enter)</button><button type="button" className="button secondary small" disabled={busy||!holeDraft.length} onClick={removeLastPoint}>Bỏ đỉnh cuối</button></>}
   {tool==='box'&&<span>Khung: {rect[2].toFixed(0)}% × {rect[3].toFixed(0)}% ảnh</span>}
   {tool==='check'&&<label className="field inline-field">Chiều dài đoạn kiểm tra (m)<input aria-label="Chiều dài đoạn kiểm tra" type="number" min=".01" max="300" step=".01" value={checkLength||''} onChange={e=>setCheckLength(Number(e.target.value))}/>{result&&check.length===2&&checkLength>0&&<span>Theo ảnh: {predictedCheck.toFixed(2)} m · lệch {(checkMismatch*100).toFixed(1)}%</span>}</label>}
   {tool==='measure'&&<span>{measure.length===2?'Đã có đoạn tham chiếu; nhập chiều dài thật ở phần hiệu chuẩn bên dưới.':'Chọn 2 điểm.'}</span>}
  </div>
  {tool==='quad'&&<div className="tracer-calibration"><label>Cạnh ngang thật của vùng 4 góc (m)<input type="number" min=".1" max="300" value={quadWidth} onChange={e=>setQuadWidth(Math.max(.1,Number(e.target.value)))}/></label><label>Cạnh dọc thật của vùng 4 góc (m)<input type="number" min=".1" max="300" value={quadDepth} onChange={e=>setQuadDepth(Math.max(.1,Number(e.target.value)))}/></label><p>Nhập hai số đo thật để tránh kéo méo ảnh khi hiệu chỉnh. Sau đó đo tham chiếu lại trên ảnh đã chỉnh.</p></div>}
  <div className="trace-view-row"><label className="field">Độ rõ lớp biên<input aria-label="Độ rõ lớp biên" type="range" min="0" max=".6" step=".05" value={overlayOpacity} onChange={e=>setOverlayOpacity(Number(e.target.value))}/></label>
   <div className="trace-zoom" role="group" aria-label="Phóng ảnh">
    <button type="button" title="Thu nhỏ (−)" aria-label="Thu nhỏ" disabled={zoom<=ZOOMS[0]} onClick={()=>stepZoom(-1)}>−</button>
    <output aria-live="polite">{zoom===1?'Vừa khung':`×${String(zoom).replace('.',',')}`}</output>
    <button type="button" title="Phóng to (+, Ctrl+lăn chuột)" aria-label="Phóng to" disabled={zoom>=ZOOMS[ZOOMS.length-1]} onClick={()=>stepZoom(1)}>+</button>
    <button type="button" className={zoom===1?'active':''} aria-pressed={zoom===1} title="Vừa màn hình (0)" onClick={()=>setZoomAt(1)}>Vừa màn hình</button>
   </div></div>
  {/* The whole photo fits the screen by default; zoomed, it scrolls inside this frame instead of the page. */}
  <div ref={stage} className={`trace-stage${zoom>1?' zoomed':''}`} style={{'--ar':size.w/size.h,'--zoom':zoom} as CSSProperties}>
  <svg ref={svg} viewBox={`0 0 ${W} ${H}`} style={{aspectRatio:`${W}/${H}`}} className={`trace-image ${cursorClass}`} aria-label="Ảnh gốc để khoanh vùng, chấm biên và đo tỷ lệ"
   onPointerDown={down} onPointerMove={move} onPointerUp={endDrag} onPointerCancel={endDrag} onPointerLeave={()=>setHover(null)} onAuxClick={e=>e.preventDefault()}
   onDoubleClick={e=>{if(tool==='polygon')closeOutline();else if(tool==='opening')commitHole();else if(tool==='edit'&&(e.target as Element).closest('[data-vertex]'))deleteSelected()}}>
   <image href={url||undefined} width={W} height={H} preserveAspectRatio="none"/>
   {brushLayer(keep,'#21c86d')}{brushLayer(drop,'#ff4d6d')}{live&&brushLayer([live],stroke.current?.target==='remove'?'#ff4d6d':'#21c86d')}
   {shownOutline.length>=3&&(closed||result||tool!=='polygon')&&<path d={[shownOutline,...shownOpenings].map(ring).join('')} fill="#42cf9b" fillOpacity={overlayOpacity} fillRule="evenodd" stroke="#2bd3a0" strokeWidth="2" {...ui} pointerEvents="none"/>}
   {tool==='box'&&<path d={`M0 0H${W}V${H}H0Z`+ring([{x:rect[0],y:rect[1]},{x:rect[0]+rect[2],y:rect[1]},{x:rect[0]+rect[2],y:rect[1]+rect[3]},{x:rect[0],y:rect[1]+rect[3]}])} fill="#0b1a12" fillOpacity=".38" fillRule="evenodd" pointerEvents="none"/>}
   {tool==='box'&&<rect data-box="move" className="box-body" x={X({x:rect[0],y:0})} y={Y({x:0,y:rect[1]})} width={rect[2]*W/100} height={rect[3]*H/100} fill="none" stroke="transparent" strokeWidth="14" {...ui}/>}
   <rect x={X({x:rect[0],y:0})} y={Y({x:0,y:rect[1]})} width={rect[2]*W/100} height={rect[3]*H/100} fill="none" stroke="#f6bb4d" strokeWidth="2" strokeDasharray="7 5" {...ui} pointerEvents="none"/>
   {tool==='box'&&(()=>{const c={x:rect[0]+rect[2]/2,y:rect[1]+rect[3]/2},a=u(9);return <g data-box="move" className="box-body">{dot(c,15,{fill:'#0b1a12',fillOpacity:.45,stroke:'#fff',strokeWidth:1.5})}<path d={`M${X(c)-a} ${Y(c)}H${X(c)+a}M${X(c)} ${Y(c)-a}V${Y(c)+a}`} stroke="#fff" strokeWidth="1.8" {...ui}/></g>})()}
   {tool==='box'&&BOX_HANDLES.map(h=>{const x=rect[0]+(h.includes('w')?0:h.includes('e')?rect[2]:rect[2]/2),y=rect[1]+(h.includes('n')?0:h.includes('s')?rect[3]:rect[3]/2)
    return <g key={h} data-box={h} className={`box-handle box-${h}`}>{square({x,y},HANDLE+8,{fill:'transparent',stroke:'none'})}{square({x,y},HANDLE,{fill:'#fff',stroke:'#b4791a',strokeWidth:1.5})}</g>})}
   {/* pen: open path with live rubber band; closed outlines render as the filled overlay above */}
   {tool==='polygon'&&!closed&&<polyline points={pts(outline)} fill="none" stroke="#2bd3a0" strokeWidth="2" {...ui} pointerEvents="none"/>}
   {tool==='polygon'&&!closed&&<>{rubber(last(outline),'#2bd3a0')}{outline.length>=2&&hover&&<line x1={X(hover)} y1={Y(hover)} x2={X(outline[0])} y2={Y(outline[0])} stroke="#2bd3a0" strokeOpacity=".45" strokeWidth="1" strokeDasharray="2 4" {...ui} pointerEvents="none"/>}</>}
   {tool==='polygon'&&outline.map((p,i)=><g key={i} pointerEvents="none">{square(p,i===0&&nearFirst(outline)&&!closed?HANDLE+6:8,{fill:i===0?'#2bd3a0':'#fff',stroke:'#13795b',strokeWidth:1.5})}</g>)}
   {/* edit: square vertex handles and midpoint dots on the outline and every courtyard */}
   {tool==='edit'&&[outline,...openings].map((list,r)=>{const opening=r===0?undefined:r-1,color=r===0?'#13795b':'#c2416a'
    return <g key={r}>{list.map((p,i)=>{const q=list[(i+1)%list.length],sel=selected?.index===i&&selected.opening===opening
     return <g key={i}><g data-mid={i} data-ring={opening} className="mid-handle">{dot({x:(p.x+q.x)/2,y:(p.y+q.y)/2},7,{fill:'transparent',stroke:'none'})}{dot({x:(p.x+q.x)/2,y:(p.y+q.y)/2},3.5,{fill:'#fff',stroke:color,strokeWidth:1.2})}</g>
      <g data-vertex={i} data-ring={opening} className="vertex-handle">{square(p,HANDLE+8,{fill:'transparent',stroke:'none'})}{square(p,HANDLE,{fill:sel?color:'#fff',stroke:color,strokeWidth:1.5})}</g></g>})}</g>})}
   {tool!=='edit'&&openings.map((r,j)=><path key={j} d={ring(r)} fill="none" stroke="#e05a85" strokeWidth="1.5" {...ui} pointerEvents="none"/>)}
   {tool==='opening'&&<><polyline points={pts(holeDraft)} fill="none" stroke="#e05a85" strokeWidth="2" {...ui} pointerEvents="none"/>{rubber(last(holeDraft),'#e05a85')}
    {holeDraft.map((p,i)=><g key={i} pointerEvents="none">{square(p,i===0&&nearFirst(holeDraft)?HANDLE+6:8,{fill:i===0?'#e05a85':'#fff',stroke:'#a3264f',strokeWidth:1.5})}</g>)}</>}
   {/* measuring and perspective points */}
   {[[measure,'#3d9cf5'],[check,'#b46cf0']].map(([list,color],j)=>{const l=list as Point[];return <g key={j} pointerEvents="none">
    {l.length===2?<line x1={X(l[0])} y1={Y(l[0])} x2={X(l[1])} y2={Y(l[1])} stroke={String(color)} strokeWidth="2.5" {...ui}/>:((tool==='measure'&&j===0)||(tool==='check'&&j===1))?rubber(l[0],String(color)):null}
    {l.map((p,i)=><g key={i}>{dot(p,5,{fill:'#fff',stroke:String(color),strokeWidth:2})}</g>)}</g>})}
   {quad.length>0&&<g pointerEvents="none"><polyline points={pts(quad.length===4?[...quad,quad[0]]:quad)} fill="none" stroke="#b46cf0" strokeWidth="2" {...ui}/>{tool==='quad'&&quad.length<4&&rubber(last(quad),'#b46cf0')}
    {quad.map((p,i)=><g key={i}>{dot(p,6,{fill:'#b46cf0',stroke:'#fff',strokeWidth:1.5})}<text x={X(p)+u(9)} y={Y(p)-u(9)} fontSize={u(13)} fontWeight="700" fill="#fff" stroke="#3a1458" strokeWidth={u(3)} paintOrder="stroke">{i+1}</text></g>)}</g>}
   {(tool==='keep'||tool==='remove')&&hover&&!panning&&<g pointerEvents="none"><circle cx={X(hover)} cy={Y(hover)} r={u(brushPx)} fill="none" stroke="#000" strokeOpacity=".55" strokeWidth="3" {...ui}/><circle cx={X(hover)} cy={Y(hover)} r={u(brushPx)} fill="none" stroke={tool==='keep'?'#7dffb5':'#ff9fb0'} strokeWidth="1.5" {...ui}/></g>}
  </svg>
  </div>
  <p className="tracer-status"><strong>{toolLabel}</strong> · {HINTS[tool]} <span className="tracer-keys">Space + kéo: dời ảnh · Ctrl + lăn chuột: phóng · Ctrl+Z: hoàn tác</span></p>
  {(shownOpenings.length>0)&&<div className="tracer-actions"><button className="text-button" disabled={busy||!openings.length} onClick={()=>{saveEdit();setOpenings([]);setResult(null)}}>Xóa tất cả sân trong ({openings.length})</button>{shownOpenings.map((_,i)=><button className="text-button" key={i} disabled={busy} onClick={()=>{saveEdit();if(result){setOutline(result.polygon_image_pct);setClosed(true)}setOpenings(shownOpenings.filter((_,j)=>j!==i));setResult(null);setTool('edit')}}>Xóa sân trong {i+1}</button>)}</div>}
  <div className="tracer-actions"><button className="button primary" disabled={busy||!url} onClick={()=>trace(kind==='plan'?'plan':'grabcut')}>{busy?'Đang xử lý điểm ảnh…':'Tách biên từ vùng chọn'}</button><button className="button secondary" disabled={busy||outline.length<3} onClick={()=>trace('manual')}>Dùng biên đã vẽ ({outline.length} đỉnh)</button><button className="button secondary" disabled={busy||quad.length!==4} onClick={()=>trace('rectify')}>Hiệu chỉnh 4 góc</button><button className="text-button" disabled={busy} onClick={clearAll}>Xóa hết nét và điểm</button></div>
  <div className="tracer-calibration"><label>{target==="roof"?"Cạnh dài nhất của mái (m)":"Cạnh dài nhất của vật thể (m)"}<input aria-label="Cạnh dài nhất" type="number" min=".1" max={MAX_ROOF_SIDE_M} step=".1" placeholder="Ví dụ 18,5" value={target==="roof"?measuredLong??localLong:localLong} onChange={e=>{setLocalLong(e.target.value);if(target==="roof")onLongChange?.(e.target.value)}}/></label><label>Hình dạng biên<select aria-label="Hình dạng biên" value={shape} onChange={e=>{setShape(e.target.value as Shape);setResult(null)}}><option value="orthogonal">Nắn cạnh vuông góc (nhà phố, nhà xưởng)</option><option value="rectangle">Hình chữ nhật</option><option value="none">Giữ đúng theo màu ảnh</option></select></label><label>Giữ chi tiết đường biên<select value={detail} onChange={e=>{setDetail(Number(e.target.value));setResult(null)}}><option value={.001}>Nhiều đỉnh</option><option value={.003}>Cân bằng</option><option value={.008}>Ít đỉnh</option></select></label><label className="check-line"><input type="checkbox" checked={useReference} onChange={e=>setUseReference(e.target.checked)}/>Dùng đoạn tham chiếu thay cho cạnh dài</label>{useReference&&<label>Đoạn tham chiếu đã đo thật (m)<input type="number" min=".01" max={MAX_ROOF_SIDE_M} step=".1" value={knownLength} onChange={e=>setKnownLength(Math.max(.01,Number(e.target.value)))}/></label>}</div>
  <p className="muted-note">{calibrated?'Tỷ lệ lấy từ đoạn tham chiếu (công cụ "Đo tham chiếu"); cạnh dài/ngắn đã nhập chỉ để đối chiếu.':'Chỉ cần cạnh dài nhất: tỷ lệ ảnh cho ra cạnh còn lại, bản vẽ không bị kéo méo. Không có thước? Trên Google Maps, nhấp chuột phải vào một góc mái → "Đo khoảng cách" → nhấp góc kia của cạnh dài.'} Mái nhiều màu (tôn thay mới, vá, bóng đổ): tô thêm "Cọ giữ mái" lên từng mảng màu rồi tách lại. Ảnh chụp xiên cần "4 góc phối cảnh" trước.</p>
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {result&&<div className="trace-result"><strong>{result.roof_polygon_pct.length} đỉnh · {result.roof_openings_pct?.length||0} khoảng trống · {actualWidth.toFixed(2)} × {actualHeight.toFixed(2)} m · {Math.round(result.elapsed_ms)} ms</strong>{result.notes.map((note,i)=><p key={i}>{note}</p>)}{target==='roof'&&calibration.sound&&<p className={calibration.checked&&!calibration.valid?'tracer-warn':undefined}>Theo ảnh: cạnh dài {calibration.long.toFixed(2)} m, cạnh ngắn {calibration.short.toFixed(2)} m.{calibration.checked?` Lệch so với số bạn nhập ${(calibration.mismatch*100).toFixed(1)}%${calibration.valid?' · khớp':calibration.acceptable?' · thường do mép mái/máng xối':''}.`:' Nhập thêm cạnh ngắn ở phần Thông tin công trình nếu muốn đối chiếu.'}</p>}{warning&&<p className="tracer-warn" role="status">{warning}</p>}<div><select aria-label="Áp dụng đường biên cho" value={target} onChange={e=>setTarget(e.target.value as 'roof'|'obstacle')}><option value="roof" disabled={kind==='partial'}>Toàn mái</option><option value="obstacle">Một vật thể / chi tiết</option></select><button className="button primary" disabled={!!applyBlockedReason} title={applyBlockedReason||undefined} onClick={async()=>{setBusy(true);try{await onApply({result,width:actualWidth,height:actualHeight,target,calibrated,referenceLength:calibrated?knownLength:undefined,sourceImage:url,calibrationRecord:{captured_at:new Date().toISOString(),method:result.algorithm,image_width_px:size.w,image_height_px:size.h,reference_points:calibrated?measure:[],reference_m:calibrated?knownLength:null,check_points:check.length===2&&checkLength>0?check:[],check_m:check.length===2&&checkLength>0?checkLength:null,measured_width_m:long??null,measured_length_m:measuredShort??null,result_width_m:actualWidth,result_height_m:actualHeight,frame_error_pct:calibration.mismatch*100,check_error_pct:check.length===2&&checkLength>0?checkMismatch*100:null}})}finally{setBusy(false)}}}>Áp dụng biên và tỷ lệ</button></div>{applyBlockedReason&&<p className="tracer-error" role="status">{applyBlockedReason}</p>}</div>}
 </section>
}
