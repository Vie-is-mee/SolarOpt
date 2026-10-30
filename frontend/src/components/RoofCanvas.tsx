import {useEffect,useRef,useState} from 'react'
import {panelBadges} from '../panelLabels'
import {panelLabel,panelCorners} from '../layoutMeasurements'
import type {Config,Obstacle,Scene,Design,Point} from '../studioTypes'
import {Icon} from './Icon'
import {footprint,outerRoof,pathOf,polygonObstacle} from '../editorGeometry'
export type ViewMode='plan'|'shadow'|'heat'
type Props={comparisonRoof?:Point[];datumIndex?:number;highlightPanels?:string[];idPrefix?:string;config:Config;obstacles:Obstacle[];scene:Scene|null;design:Design|null;selected:string|null;onSelect:(id:string|null)=>void;onMove:(id:string,x:number,y:number)=>void;onRoof:(points:Point[])=>void;mode:ViewMode;setMode:(v:ViewMode)=>void;editable:boolean;loading:boolean;sample:boolean;onPatch?:(id:string,p:Partial<Obstacle>)=>void;onGeometry?:(p:Partial<Config>)=>void;onAddPolygon?:(p:Point[])=>void;onEditStart?:()=>void;onEditEnd?:()=>void;referenceImage?:string|null}
type Drag={kind:'move'|'resize'|'rotate'|'object-vertex'|'roof-vertex'|'face-vertex'|'opening-vertex';start:Point;object?:Obstacle;index?:number;id?:string;points?:Point[];corner?:number;opening?:number}
type Tool='move'|'roof'|'face'|'opening'|'object'
const rounded=(v:number)=>Math.round(v*100)/100
export function RoofCanvas({comparisonRoof=[],datumIndex=0,config,obstacles,scene,design,selected,onSelect,onMove,onRoof,mode,setMode,editable,loading,sample,idPrefix='roof',highlightPanels=[],onPatch,onGeometry,onAddPolygon,onEditStart,onEditEnd,referenceImage}:Props){
 const svg=useRef<SVGSVGElement>(null),drag=useRef<Drag|null>(null),pending=useRef<Partial<Config>|null>(null)
 const pointers=useRef(new Map<number,Point>()),gesture=useRef<{kind:'pan'|'pinch';start:Point;pan:Point;zoom:number;dist:number}|null>(null)
 const [dragging,setDragging]=useState(false)
 const [measurePanel,setMeasurePanel]=useState(''),[showMeasurements,setShowMeasurements]=useState(true)
 const [viewportRatio,setViewportRatio]=useState(1)
 useEffect(()=>{const el=svg.current;if(!el)return;const observer=new ResizeObserver(()=>{const width=el.getBoundingClientRect().width;if(width>0)setViewportRatio(width/900)});observer.observe(el);return()=>observer.disconnect()},[])
 const [tool,setTool]=useState<Tool>('move'),[points,setPoints]=useState<Point[]>([]),[draft,setDraft]=useState<Partial<Config>|null>(null),[zoom,setZoom]=useState(1),[pan,setPan]=useState<Point>({x:0,y:0}),[opacity,setOpacity]=useState(.4),[selectedFace,setSelectedFace]=useState<string|null>(null)
 const c={...config,...draft},roof=outerRoof(c),faces=c.roof_faces||[],holes=c.roof_openings||[]
 const minX=Math.min(-2,...obstacles.map(o=>Math.max(-c.roof_width_m-12,o.x-1))),minY=Math.min(-2,...obstacles.map(o=>Math.max(-c.roof_height_m-12,o.y-1)))
 const maxX=Math.max(c.roof_width_m+2,...comparisonRoof.map(p=>p.x+2),...obstacles.map(o=>Math.min(c.roof_width_m*2+12,o.x+o.width_m+1))),maxY=Math.max(c.roof_height_m+2,...comparisonRoof.map(p=>p.y+2),...obstacles.map(o=>Math.min(c.roof_height_m*2+12,o.y+o.depth_m+1)))
 const focusPanel=design?.panels.find(p=>p.id===measurePanel)||design?.panels[0]
 // Base view for a zoom level; pan (viewBox px) shifts it so wheel/pinch zoom keeps the point under the pointer fixed.
 const baseView=(z:number)=>{const s=Math.min(740/(maxX-minX),460/(maxY-minY))*z,focus=z>1&&!editable&&focusPanel;return{scale:s,tx:450-(focus?focusPanel.x+focusPanel.width_m/2:(minX+maxX)/2)*s,ty:315+(focus?focusPanel.y+focusPanel.height_m/2:(minY+maxY)/2)*s}}
 const base=baseView(zoom),fitScale=base.scale,fitTx=base.tx+pan.x,fitTy=base.ty+pan.y
 function zoomFrom(fromZoom:number,fromPan:Point,toZoom:number,at:Point){const z=Math.min(6,Math.max(.7,toZoom)),a=baseView(fromZoom),b=baseView(z),k=b.scale/a.scale
  setZoom(z);setPan({x:at.x-(at.x-a.tx-fromPan.x)*k-b.tx,y:at.y-(at.y-a.ty-fromPan.y)*k-b.ty})}
 const zoomAt=useRef<(z:number,at:Point)=>void>(()=>{});zoomAt.current=(z:number,at:Point)=>zoomFrom(zoom,pan,z,at)
 useEffect(()=>{const el=svg.current;if(!el)return
  const wheel=(e:WheelEvent)=>{if(!e.ctrlKey&&!e.metaKey)return;e.preventDefault();const p=el.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const v=p.matrixTransform(el.getScreenCTM()!.inverse())
   zoomAt.current(zoomRef.current*Math.exp(-Math.max(-60,Math.min(60,e.deltaY))/300),{x:v.x,y:v.y})}
  el.addEventListener('wheel',wheel,{passive:false});return()=>el.removeEventListener('wheel',wheel)},[])
 const zoomRef=useRef(zoom);zoomRef.current=zoom
 const transform=useRef({scale:fitScale,tx:fitTx,ty:fitTy});if(!dragging&&!drag.current)transform.current={scale:fitScale,tx:fitTx,ty:fitTy}
 const {scale,tx,ty}=transform.current
 const sx=(x:number)=>tx+x*scale,sy=(y:number)=>ty-y*scale
 const roofPath=pathOf(roof)+holes.map(pathOf).join('')
 const datumA=roof[Math.min(datumIndex,roof.length-1)],activePanel=design?.panels.find(p=>p.id===measurePanel)||design?.panels[0],corner=activePanel?panelCorners(activePanel)[0]:null
 const measurementLabel=c.dimensions_source==='measured'?'Theo số đo thực tế':c.dimensions_verified?'Đã đối chiếu số đo':c.dimensions_source==='reference'?'Đã hiệu chuẩn':'Kích thước giả định'
 const approximate=c.dimensions_verified||c.dimensions_source==='measured'?'':'≈ '
 const handleRadius=5/scale
 function cursor(e:React.PointerEvent<SVGSVGElement>){const p=svg.current!.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const v=p.matrixTransform(svg.current!.getScreenCTM()!.inverse()),t=transform.current;return{x:(v.x-t.tx)/t.scale,y:(t.ty-v.y)/t.scale}}
 function viewPoint(e:React.PointerEvent<SVGSVGElement>){const p=svg.current!.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const v=p.matrixTransform(svg.current!.getScreenCTM()!.inverse());return{x:v.x,y:v.y}}
 function pinchState(){const [a,b]=[...pointers.current.values()];return{mid:{x:(a.x+b.x)/2,y:(a.y+b.y)/2},dist:Math.max(1,Math.hypot(a.x-b.x,a.y-b.y))}}
 function preview(p:Partial<Config>){pending.current=p;setDraft(p)}
 function down(e:React.PointerEvent<SVGSVGElement>){const point=cursor(e),target=e.target as Element
  pointers.current.set(e.pointerId,viewPoint(e))
  if(pointers.current.size===2){if(drag.current){drag.current=null;pending.current=null;setDraft(null);setDragging(false)}const {mid,dist}=pinchState();gesture.current={kind:'pinch',start:mid,pan,zoom,dist};e.currentTarget.setPointerCapture(e.pointerId);return}
  const hit=target.closest('[data-panel]');if(!editable&&hit){setMeasurePanel(hit.getAttribute('data-panel')!);return}
  if(editable&&tool!=='move'){setPoints(a=>[...a,{x:rounded(Math.max(0,Math.min(tool==='object'?100:config.roof_width_m,point.x))),y:rounded(Math.max(0,Math.min(tool==='object'?100:config.roof_height_m,point.y)))}]);return}
  const vertex=target.closest('[data-roof-vertex]'),edge=target.closest('[data-roof-edge]'),faceVertex=target.closest('[data-face-vertex]'),opening=target.closest('[data-opening-vertex]'),object=target.closest('[data-obstacle]')
  if(editable&&(vertex||edge)){
   onEditStart?.();let list=outerRoof(config).map(p=>({...p})),index=Number((vertex||edge)!.getAttribute(vertex?'data-roof-vertex':'data-roof-edge'))
   if(edge){list.splice(index+1,0,{x:rounded(point.x),y:rounded(point.y)});index++;preview({roof_polygon:list})}
   drag.current={kind:'roof-vertex',start:point,index,points:list}
  }else if(editable&&faceVertex){const id=faceVertex.getAttribute('data-face-id')!,index=Number(faceVertex.getAttribute('data-face-vertex'));onEditStart?.();drag.current={kind:'face-vertex',start:point,id,index,points:faces.find(f=>f.id===id)!.polygon};setSelectedFace(id)
  }else if(editable&&opening){onEditStart?.();const hole=Number(opening.getAttribute('data-opening'));drag.current={kind:'opening-vertex',start:point,index:Number(opening.getAttribute('data-opening-vertex')),opening:hole,points:holes[hole]}
  }else if(object){const id=object.getAttribute('data-obstacle')!,o=obstacles.find(v=>v.id===id)!;onSelect(id);setSelectedFace(null)
   if(editable){onEditStart?.();drag.current={kind:target.hasAttribute('data-rotate')?'rotate':target.hasAttribute('data-resize')?'resize':target.hasAttribute('data-object-vertex')?'object-vertex':'move',start:point,object:structuredClone(o),id,corner:Number(target.getAttribute('data-resize')),index:Number(target.getAttribute('data-object-vertex')),points:footprint(o)}}
  }else{onSelect(null);const f=target.closest('[data-face]');setSelectedFace(f?.getAttribute('data-face')||null);gesture.current={kind:'pan',start:viewPoint(e),pan,zoom,dist:1};e.currentTarget.setPointerCapture(e.pointerId)}
  if(drag.current){e.preventDefault();setDragging(true);e.currentTarget.setPointerCapture(e.pointerId)}
 }
 function move(e:React.PointerEvent<SVGSVGElement>){if(pointers.current.has(e.pointerId))pointers.current.set(e.pointerId,viewPoint(e))
  const g=gesture.current
  if(g?.kind==='pinch'&&pointers.current.size>=2){const {mid,dist}=pinchState();zoomFrom(g.zoom,{x:g.pan.x+mid.x-g.start.x,y:g.pan.y+mid.y-g.start.y},g.zoom*dist/g.dist,mid);return}
  if(g?.kind==='pan'){const v=viewPoint(e);setPan({x:g.pan.x+v.x-g.start.x,y:g.pan.y+v.y-g.start.y});return}
  const d=drag.current;if(!d)return;const p=cursor(e),o=d.object
  if(d.kind==='roof-vertex'||d.kind==='face-vertex'||d.kind==='opening-vertex'){
   const list=d.points!.map((v,i)=>i===d.index?{x:Math.min(config.roof_width_m,rounded(Math.max(0,Math.min(config.roof_width_m,p.x)))),y:Math.min(config.roof_height_m,rounded(Math.max(0,Math.min(config.roof_height_m,p.y))))}:v)
   if(d.kind==='roof-vertex')preview({roof_polygon:list})
   else if(d.kind==='face-vertex')preview({roof_faces:faces.map(f=>f.id===d.id?{...f,polygon:list}:f)})
   else preview({roof_openings:holes.map((h,i)=>i===d.opening?list:h)})
  }else if(o){
   if(d.kind==='move')onMove(o.id,rounded(o.x+p.x-d.start.x),rounded(o.y+p.y-d.start.y))
   else if(d.kind==='rotate')onPatch?.(o.id,{rotation_deg:rounded(Math.atan2(p.y-o.y-o.depth_m/2,p.x-o.x-o.width_m/2)*180/Math.PI-90)})
   else if(d.kind==='object-vertex')onPatch?.(o.id,polygonObstacle(d.points!.map((v,i)=>i===d.index?{x:rounded(p.x),y:rounded(p.y)}:v)))
   else{
    const corners=footprint({...o,shape:'rect'}),opp=corners[((d.corner||0)+2)%4],a=(o.rotation_deg||0)*Math.PI/180,u={x:Math.cos(a),y:Math.sin(a)},v={x:-Math.sin(a),y:Math.cos(a)},dx=p.x-opp.x,dy=p.y-opp.y
    const signX=d.corner===1||d.corner===2?1:-1,signY=d.corner===2||d.corner===3?1:-1,w=Math.max(.1,(dx*u.x+dy*u.y)*signX),h=Math.max(.1,(dx*v.x+dy*v.y)*signY)
    const cx=opp.x+u.x*signX*w/2+v.x*signY*h/2,cy=opp.y+u.y*signX*w/2+v.y*signY*h/2
    onPatch?.(o.id,{x:rounded(cx-w/2),y:rounded(cy-h/2),width_m:rounded(w),depth_m:rounded(h),points:o.points?.map(p=>({x:p.x*w/o.width_m,y:p.y*h/o.depth_m}))})
   }
  }
 }
 function up(e:React.PointerEvent<SVGSVGElement>){pointers.current.delete(e.pointerId);if(gesture.current){if(gesture.current.kind==='pan'||pointers.current.size<2)gesture.current=null;if(!drag.current)return}
 if(pending.current){onGeometry?.(pending.current);pending.current=null;setDraft(null)}drag.current=null;setDragging(false);onEditEnd?.()}
 function finish(){if(points.length<3)return;onEditStart?.();if(tool==='roof')onRoof(points);else if(tool==='face')onGeometry?.({roof_faces:[...faces,{id:crypto.randomUUID(),label:`Phần mái ${faces.length+1}`,polygon:points,elevation_m:config.roof_elevation_m+2,tilt_deg:0,azimuth_deg:180,installable:true}]});else if(tool==='opening')onGeometry?.({roof_openings:[...holes,points]});else onAddPolygon?.(points);onEditEnd?.();setPoints([]);setTool('move')}
 return <section className="canvas-card">
  <div className="canvas-toolbar"><div className="segmented">{([['plan','Bản vẽ','layers'],['shadow','Bóng che','sun'],['heat','Bức xạ','bolt']] as const).map(([id,label,icon])=><button key={id} className={mode===id?'active':''} onClick={()=>setMode(id)}><Icon name={icon} size={15}/>{label}</button>)}</div><span className="canvas-live"><i className={loading?'busy':''}/>{loading?'Đang tính…':scene?'Dữ liệu mô phỏng':'Chờ bộ tính toán'}</span></div>
  {!editable&&design&&<div className="measurement-controls"><label><input type="checkbox" checked={showMeasurements} onChange={e=>setShowMeasurements(e.target.checked)}/> Hiện số đo định vị</label><label>Đo vị trí tấm <select aria-label="Đo vị trí tấm" value={activePanel?.id||''} onChange={e=>setMeasurePanel(e.target.value)}>{design.panels.map((p,i)=><option key={p.id} value={p.id}>{panelLabel(i)}</option>)}</select></label><span>Bấm tấm hoặc chọn mã · phóng to để hiện thêm mã · V1 là chấm trắng.</span></div>}
  {!editable&&activePanel&&<div className="panel-selection-info" role="status"><strong>{panelLabel(design!.panels.indexOf(activePanel))}</strong><span>{activePanel.width_m} × {activePanel.height_m} m · góc {activePanel.rotation_deg||0}°</span><span>V1 từ A: X {(corner!.x-datumA.x).toFixed(3)} m · Y {(corner!.y-datumA.y).toFixed(3)} m</span><small>Viền vàng: đang chọn · viền đỏ: cần kiểm tra</small></div>}
  {editable&&<div className="geometry-tools">{([['move','Kéo / sửa đỉnh'],['roof','Vẽ biên mái'],['face','Vẽ phần mái cao/thấp'],['opening','Vẽ khoảng trống'],['object','Vẽ vật cản đa giác']] as [Tool,string][]).map(([id,label])=><button key={id} className={tool===id?'active':''} onClick={()=>{setTool(id);setPoints([])}}>{label}</button>)}{tool!=='move'&&<button disabled={points.length<3} onClick={finish}>Khép biên ({points.length})</button>}</div>}
  {referenceImage&&<label className="reference-opacity">Ảnh nền để canh biên<input aria-label="Độ rõ ảnh nền" type="range" min="0" max=".85" step=".05" value={opacity} onChange={e=>setOpacity(Number(e.target.value))}/>{Math.round(opacity*100)}%</label>}
  <div className={`canvas-surface ${tool!=='move'?'drawing':''}`}><div className="map-label"><span className="map-dot"/> MẶT BẰNG MÁI <span>{sample?'Dữ liệu mẫu':!config.roof_polygon.length?'Khung số đo · kiểm tra biên mái':'Dữ liệu dự án'}</span><span className={`measurement-badge ${c.dimensions_verified?'verified':'estimated'}`}>{measurementLabel}</span></div>
  <svg ref={svg} viewBox="0 0 900 630" className="roof-svg" role="img" aria-label="Bản vẽ mái tương tác, vật cản, bóng và tấm pin" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
   <defs><pattern id={`${idPrefix}-map-grid`} width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="#bdd1c9" strokeWidth=".5"/></pattern><pattern id={`${idPrefix}-panel-grid`} width=".29" height=".39" patternUnits="userSpaceOnUse"><path d="M.29 0H0V.39" fill="none" stroke="#b0e4ff" strokeWidth=".012" opacity=".5"/></pattern><linearGradient id={`${idPrefix}-roof-fill`}><stop stopColor="#fffef7"/><stop offset="1" stopColor="#e2ebe5"/></linearGradient><linearGradient id={`${idPrefix}-panel-fill`}><stop stopColor="#235b7d"/><stop offset="1" stopColor="#143a59"/></linearGradient><clipPath id={`${idPrefix}-roof-clip`}><path d={roofPath} clipRule="evenodd"/></clipPath></defs>
   <rect width="900" height="630" fill={`url(#${idPrefix}-map-grid)`}/>
   <g transform={`translate(${tx},${ty}) scale(${scale},${-scale})`}>
    <path d={roofPath} fill={`url(#${idPrefix}-roof-fill)`} fillRule="evenodd" stroke={c.geometry_confirmed?'#708d7a':'#bc9561'} strokeWidth=".07"/>
    {referenceImage&&<image href={referenceImage} x="0" y={-c.roof_height_m} width={c.roof_width_m} height={c.roof_height_m} transform="scale(1,-1)" opacity={opacity} preserveAspectRatio="none"/>}
    {faces.map((f,i)=><path key={f.id} data-face={f.id} d={pathOf(f.polygon)} fill={['#b8d4da','#d9c8ad','#c7d6b2','#c8b9da'][i%4]} fillOpacity=".28" stroke={selectedFace===f.id?'#e5a03d':'#77928d'} strokeWidth=".045" strokeDasharray=".15 .08"/>)}
    {holes.map((h,i)=><path key={i} d={pathOf(h)} fill="#f5f7f3" stroke="#bc8473" strokeWidth=".045" strokeDasharray=".12 .08"/>)}
    {scene?.usable_polygons.map((p,i)=><polygon key={i} points={p.map(v=>v.join(',')).join(' ')} fill="none" stroke="#8aab91" strokeDasharray=".12 .12" strokeWidth=".025"/>)}
    <g clipPath={`url(#${idPrefix}-roof-clip)`}>{mode==='heat'&&scene?.cells.map((v,i)=><rect key={i} x={v.x} y={v.y} width={v.width_m+.01} height={v.height_m+.01} fill={`hsl(${15+Math.min(1,v.irradiance_w_m2/1000)*40},87%,${v.shade_fraction>.8?45:68}%)`} opacity=".8"/>)}{mode!=='plan'&&scene?.shadows.flatMap(s=>(s.regions||s.polygons.map(boundary=>({boundary,openings:[]}))).map((region,i)=><path key={s.id+i} data-shadow={s.id} d={[region.boundary,...region.openings].map(r=>'M'+r.map(v=>v.join(',')).join('L')+'Z').join('')} fillRule="evenodd" fill={selected===s.id?'#a96521':'#244a48'} fillOpacity={selected===s.id?.48:mode==='heat'?.22:.3}/>))}{scene&&scene.sun.altitude_deg<=0&&mode!=='plan'&&<path d={roofPath} fillRule="evenodd" fill="#1d3548" opacity=".62"/>}</g>
    {comparisonRoof.length>0&&<path data-original-roof="true" d={pathOf(comparisonRoof)} fill="none" stroke="#45474b" strokeWidth=".06" strokeDasharray=".16 .1"/>}
    {design?.panels.map(p=><g key={p.id} data-panel={p.id} data-panel-warning={highlightPanels.includes(p.id)?'true':undefined} data-active-panel={activePanel?.id===p.id?'true':undefined} role={!editable?'button':undefined} tabIndex={!editable?0:undefined} aria-label={`Chọn ${panelLabel(design.panels.indexOf(p))}`} aria-pressed={!editable?activePanel?.id===p.id:undefined} onKeyDown={e=>{if(!editable&&(e.key==='Enter'||e.key===' ')){e.preventDefault();setMeasurePanel(p.id)}}} transform={`rotate(${p.rotation_deg||0} ${p.x+p.width_m/2} ${p.y+p.height_m/2})`}><title>{panelLabel(design.panels.indexOf(p))} · {p.width_m} × {p.height_m} m · góc {p.rotation_deg||0}°</title><rect x={p.x} y={p.y} width={p.width_m} height={p.height_m} rx=".035" fill={`url(#${idPrefix}-panel-fill)`} stroke={highlightPanels.includes(p.id)?'#e84a32':activePanel?.id===p.id?'#f2bd48':p.preserved?'#51d2ad':'#91b1c3'} strokeWidth={highlightPanels.includes(p.id)?.12:activePanel?.id===p.id?2.5/scale:.035}/><rect x={p.x} y={p.y} width={p.width_m} height={p.height_m} fill={`url(#${idPrefix}-panel-grid)`}/></g>)}
    {obstacles.map(o=><g key={o.id} data-obstacle={o.id} className={editable?'obstacle-draggable':''} tabIndex={0} role="button" aria-label={`Chọn ${o.label}`} onKeyDown={e=>{if(e.key==='Enter')onSelect(o.id);if(editable&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();onEditStart?.();onMove(o.id,rounded(o.x+(e.key==='ArrowRight'?.1:e.key==='ArrowLeft'?-.1:0)),rounded(o.y+(e.key==='ArrowUp'?.1:e.key==='ArrowDown'?-.1:0)));onEditEnd?.()}}}>
     <polygon points={footprint(o).map(p=>`${p.x},${p.y}`).join(' ')} fill={o.scope==='neighbor'?'#99afa6':o.shape==='ellipse'?'#d7e5e8':'#c4bcae'} stroke={selected===o.id?'#f4ad43':o.confirmed?'#718b7d':'#bd8b41'} strokeWidth={selected===o.id?.08:.035} strokeDasharray={o.confirmed?undefined:'.1 .07'}/>
     {editable&&selected===o.id&&<>{footprint({...o,shape:'rect'}).map((p,i)=><rect key={i} data-resize={i} x={p.x-handleRadius} y={p.y-handleRadius} width={handleRadius*2} height={handleRadius*2} fill="white" stroke="#df9830" strokeWidth={1.3/scale}/>)}{o.shape==='polygon'&&footprint(o).map((p,i)=><circle key={i} data-object-vertex={i} cx={p.x} cy={p.y} r={handleRadius*1.1} fill="#6db6be" stroke="white" strokeWidth={1/scale}/>)}<circle data-rotate="true" cx={o.x+o.width_m/2} cy={o.y+o.depth_m+.65} r={handleRadius*1.4} fill="#9b74c9" stroke="white" strokeWidth={1/scale}/></>}
    </g>)}
    {editable&&tool==='move'&&<>{roof.map((p,i)=>{const q=roof[(i+1)%roof.length];return <g key={i}><circle data-roof-edge={i} cx={(p.x+q.x)/2} cy={(p.y+q.y)/2} r={handleRadius*.7} fill="#f6dc9d" stroke="#b28d4d" strokeWidth={1/scale}/><circle data-roof-vertex={i} cx={p.x} cy={p.y} r={handleRadius*1.15} fill="white" stroke="#cb8a37" strokeWidth={1.6/scale} onDoubleClick={()=>{if(roof.length>3)onRoof(roof.filter((_,j)=>j!==i))}}/></g>})}{faces.filter(f=>f.id===selectedFace).flatMap(f=>f.polygon.map((p,i)=><circle key={f.id+i} data-face-id={f.id} data-face-vertex={i} cx={p.x} cy={p.y} r={handleRadius} fill="#a4cee0" stroke="white" strokeWidth={1/scale}/>))}{holes.flatMap((h,j)=>h.map((p,i)=><circle key={`${j}-${i}`} data-opening={j} data-opening-vertex={i} cx={p.x} cy={p.y} r={handleRadius} fill="#c48f82" stroke="white" strokeWidth={1/scale}/>))}</>}
    {points.length>0&&<polyline points={points.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke="#d59038" strokeWidth=".06"/>}
   </g>
   {!editable&&corner&&<g className="panel-v1-marker" pointerEvents="none"><circle data-panel-v1="true" cx={sx(corner.x)} cy={sy(corner.y)} r={4/Math.max(.2,viewportRatio)} fill="#ffffff" stroke="#b38218" strokeWidth={1.5/Math.max(.2,viewportRatio)}/></g>}
   {design&&<g className="panel-survey-labels" pointerEvents="none">{panelBadges(design.panels,activePanel?.id,scale,sx,sy,viewportRatio).map(b=><g key={b.id} data-panel-badge={b.id} data-selected-badge={b.active?'true':undefined}>{b.active&&<path d={`M${b.x} ${b.y+b.height/2}L${sx(activePanel!.x+activePanel!.width_m/2)} ${sy(activePanel!.y+activePanel!.height_m/2)}`} stroke="#b38218" strokeWidth={1.5/viewportRatio}/>}<rect x={b.x-b.width/2} y={b.y-b.height/2} width={b.width} height={b.height} rx={5/viewportRatio} fill={b.active?'#fff6d9':'#163e35'} stroke={b.active?'#b38218':'#ffffff60'} strokeWidth={1/viewportRatio}/><text x={b.x} y={b.y} textAnchor="middle" dominantBaseline="middle" fill={b.active?'#624911':'#fff'} fontSize={11/Math.max(.2,viewportRatio)} fontWeight="700">{panelLabel(b.index)}</text></g>)}{[0,1].map((v)=>{const p=roof[(Math.min(datumIndex,roof.length-1)+v)%roof.length];return <g key={v}><circle cx={sx(p.x)} cy={sy(p.y)} r="7" fill={v?'#745b30':'#b33138'} stroke="white" strokeWidth="2"/><text x={sx(p.x)+11} y={sy(p.y)-10} fill="#713137" fontSize="13" fontWeight="700">{v?'B':'A'}</text></g>})}</g>}
   {!editable&&showMeasurements&&corner&&<g className="panel-offset-dimensions" pointerEvents="none"><path d={`M${sx(datumA.x)} ${sy(datumA.y)}H${sx(corner.x)}V${sy(corner.y)}`} fill="none" stroke="#b33138" strokeWidth="1.5" strokeDasharray="5 3"/><text x={(sx(datumA.x)+sx(corner.x))/2} y={sy(datumA.y)-8} textAnchor="middle" fill="#9b2631" stroke="white" strokeWidth="3" paintOrder="stroke" fontSize="12">X { (corner.x-datumA.x).toFixed(3)} m</text><text x={sx(corner.x)+8} y={(sy(datumA.y)+sy(corner.y))/2} fill="#9b2631" stroke="white" strokeWidth="3" paintOrder="stroke" fontSize="12">Y {(corner.y-datumA.y).toFixed(3)} m</text></g>}
   <g className="roof-dimensions" pointerEvents="none" fill="none" stroke="#7e9288" strokeWidth="1.2">
    <path data-dimension="horizontal" d={`M${sx(0)} ${sy(0)+22}v10H${sx(c.roof_width_m)}v-10`}/>
    <path data-dimension="vertical" d={`M${sx(0)-22} ${sy(0)}h-10V${sy(c.roof_height_m)}h10`}/>
    <text x={sx(c.roof_width_m/2)} y={sy(0)+51} textAnchor="middle" fill="#4e6d5f" stroke="none" fontSize="14">{approximate}{c.roof_width_m.toFixed(2)} m</text>
    <text x={sx(0)-49} y={sy(c.roof_height_m/2)} textAnchor="middle" fill="#4e6d5f" stroke="none" fontSize="14" transform={`rotate(-90 ${sx(0)-49} ${sy(c.roof_height_m/2)})`}>{approximate}{c.roof_height_m.toFixed(2)} m</text>
   </g>
   {obstacles.map(o=><g key={'label'+o.id} pointerEvents="none"><rect x={sx(o.x+o.width_m/2)-46} y={sy(o.y+o.depth_m)+7} width="92" height="21" rx="5" fill="white" opacity=".88"/><text x={sx(o.x+o.width_m/2)} y={sy(o.y+o.depth_m)+21} textAnchor="middle" fill="#446458" fontSize="10">{o.label.slice(0,18)}</text></g>)}
   {faces.map(f=>{const x=f.polygon.reduce((s,p)=>s+p.x,0)/f.polygon.length,y=f.polygon.reduce((s,p)=>s+p.y,0)/f.polygon.length;return <g key={f.id} pointerEvents="none"><rect x={sx(x)-55} y={sy(y)-18} width="110" height="31" rx="5" fill="white" opacity=".9"/><text x={sx(x)} y={sy(y)-5} textAnchor="middle" fill="#446458" fontSize="10">{f.label.slice(0,18)}</text><text x={sx(x)} y={sy(y)+7} textAnchor="middle" fill="#6c7d73" fontSize="9">Cao {f.elevation_m} m · dốc {f.tilt_deg}°</text></g>})}
   <g transform={`translate(835 87) rotate(${-c.north_rotation_deg})`}><circle r="31" fill="white" opacity=".85"/><path d="M0-22-7 9 0 5 7 9Z" fill="#2b6a51"/><text y="-39" textAnchor="middle" fill="#254f3c" fontSize="12" fontWeight="700">BẮC</text></g>
   {scene&&scene.sun.altitude_deg>0&&<g transform={`translate(${450+Math.sin((scene.sun.azimuth_deg-c.north_rotation_deg)*Math.PI/180)*320},${315-Math.cos((scene.sun.azimuth_deg-c.north_rotation_deg)*Math.PI/180)*240})`}><circle r="24" fill="#f5bd50" opacity=".16"/><circle r="15" fill="#f4b83c"/>{Array.from({length:8},(_,i)=><path key={i} transform={`rotate(${i*45})`} d="M0-21V-26" stroke="#e7a52c" strokeWidth="1.5"/>)}</g>}
  </svg><div className="canvas-legend"><span><i style={{background:'#244a48'}}/>Bóng che</span><span><i style={{background:'#2d6080'}}/>Tấm pin</span><span><i style={{background:'#bca06d'}}/>Chưa xác nhận</span></div><div className="canvas-zoom" title="Ctrl + cuộn chuột hoặc chụm hai ngón để phóng; kéo vùng trống để dịch bản vẽ"><button aria-label="Thu nhỏ" onClick={()=>zoomAt.current(zoom-.15,{x:450,y:315})}>−</button><span>{Math.round(zoom*100)}%</span><button aria-label="Phóng to" onClick={()=>zoomAt.current(zoom+.25,{x:450,y:315})}>+</button><button aria-label="Đặt lại góc nhìn" onClick={()=>{setZoom(1);setPan({x:0,y:0})}}><Icon name="grid" size={15}/></button></div></div>
  {editable&&mode==='plan'&&<div className="canvas-measurement-note">Chế độ bản vẽ đang ẩn bóng che. <button className="text-button" onClick={()=>setMode('shadow')}>Hiện bóng che</button></div>}
  <div className="canvas-measurement-note">{c.dimensions_source==='measured'?'Mái đã quy đổi theo hai số đo người dùng nhập; cần kiểm tra phối cảnh và vị trí vật cản.':c.dimensions_verified?'Kích thước đã được kỹ sư đối chiếu số đo.':c.dimensions_source==='reference'?'Hiệu chuẩn theo đoạn tham chiếu; cần kiểm tra phối cảnh và đối chiếu số đo khác.':'Số đo ước lượng theo dữ liệu nhập/tỷ lệ ảnh; chưa dùng làm kích thước thi công.'}</div><div className="canvas-bottom"><span><Icon name={editable?'move':'compass'} size={14}/>{editable?'Kéo đỉnh để sửa mái · nút giữa cạnh thêm đỉnh · bấm đúp đỉnh để xóa · nút tím xoay vật thể':'Mặt bằng theo mét · các cao độ phải được kỹ sư kiểm tra'}</span></div>
 </section>
}
