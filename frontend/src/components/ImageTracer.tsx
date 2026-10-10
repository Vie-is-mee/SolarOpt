import {useEffect,useRef,useState} from 'react'
import {studioApi} from '../services/studioApi'
import type {Point,TraceResult} from '../studioTypes'

type Tool='box'|'keep'|'remove'|'polygon'|'measure'|'quad'
export type TraceApplication={result:TraceResult;width:number;height:number;target:'roof'|'obstacle';calibrated:boolean;referenceLength?:number}
export function ImageTracer({image,kind,roofWidth,measuredWidth,measuredLength,onApply}:{image:string;kind:string;roofWidth:number;measuredWidth?:number;measuredLength?:number;onApply:(v:TraceApplication)=>void}){
 const [url,setUrl]=useState(''),[size,setSize]=useState({w:100,h:100}),[tool,setTool]=useState<Tool>('box')
 const [rect,setRect]=useState([5,5,90,90]),[foreground,setForeground]=useState<Point[]>([]),[background,setBackground]=useState<Point[]>([]),[outline,setOutline]=useState<Point[]>([]),[measure,setMeasure]=useState<Point[]>([]),[quad,setQuad]=useState<Point[]>([])
 const [result,setResult]=useState<TraceResult|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const [knownLength,setKnownLength]=useState(5),[width,setWidth]=useState(roofWidth),[detail,setDetail]=useState(.003),[target,setTarget]=useState<'roof'|'obstacle'>(kind==='partial'?'obstacle':'roof')
 const svg=useRef<SVGSVGElement>(null),start=useRef<Point|null>(null)
 const [quadWidth,setQuadWidth]=useState(10),[quadDepth,setQuadDepth]=useState(8)
 useEffect(()=>{setTarget(kind==='partial'?'obstacle':'roof');setResult(null)},[kind])
 useEffect(()=>{let alive=true;setResult(null);setOutline([]);setForeground([]);setBackground([]);setMeasure([]);setQuad([]);setRect([5,5,90,90]);setError('');
  if(image.startsWith('data:'))setUrl(image)
  else fetch(image).then(r=>r.blob()).then(b=>{const reader=new FileReader();reader.onload=()=>{if(alive)setUrl(String(reader.result))};reader.readAsDataURL(b)}).catch(()=>setError('Không đọc được ảnh nguồn.'))
  return()=>{alive=false}
 },[image])
 useEffect(()=>{if(!url)return;const im=new Image();im.onload=()=>setSize({w:im.naturalWidth,h:im.naturalHeight});im.src=url},[url])
 const distance=measure.length===2?Math.hypot((measure[0].x-measure[1].x)*size.w/100,(measure[0].y-measure[1].y)*size.h/100):0
 const calibrated=distance>1&&knownLength>0
 const actualWidth=target==='roof'&&measuredWidth?measuredWidth:result?(calibrated?result.roof_width_px/(distance*(result.image_width_px/size.w))*knownLength:width):width
 const actualHeight=target==='roof'&&measuredLength?measuredLength:result?actualWidth/result.roof_aspect_ratio:0
 function point(e:React.PointerEvent<SVGSVGElement>){const p=svg.current!.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const v=p.matrixTransform(svg.current!.getScreenCTM()!.inverse());return {x:Math.max(0,Math.min(100,v.x)),y:Math.max(0,Math.min(100,v.y))}}
 function down(e:React.PointerEvent<SVGSVGElement>){if(busy)return;const p=point(e);setResult(null);if(tool==='box'){start.current=p;e.currentTarget.setPointerCapture(e.pointerId)}else if(tool==='keep')setForeground(a=>[...a,p]);else if(tool==='remove')setBackground(a=>[...a,p]);else if(tool==='polygon')setOutline(a=>[...a,p]);else if(tool==='measure')setMeasure(a=>a.length>=2?[p]:[...a,p]);else setQuad(a=>a.length>=4?[p]:[...a,p])}
 function move(e:React.PointerEvent<SVGSVGElement>){if(!start.current)return;const p=point(e),s=start.current;setRect([Math.min(s.x,p.x),Math.min(s.y,p.y),Math.max(1,Math.abs(p.x-s.x)),Math.max(1,Math.abs(p.y-s.y))])}
 async function trace(method:string){setBusy(true);setError('');try{const r=await studioApi.trace({image_data_url:url,input_kind:kind,method,rect,foreground,background,polygon:outline,quad:method==='rectify'?quad:[],quad_aspect_ratio:method==='rectify'?quadWidth/quadDepth:null,detail});
  if(r.rectified&&r.image_data_url){setUrl(r.image_data_url);setRect([2,2,96,96]);setForeground([]);setBackground([]);setOutline([]);setQuad([]);setMeasure([]);setResult(null);setTool('box')}
  else setResult(r)
 }catch(e){setError(e instanceof Error?e.message:'Chưa trích được biên.')}finally{setBusy(false)}}
 return <section className="image-tracer">
  <div className="tracer-heading"><div><h3>Trích biên đúng theo ảnh</h3><p>Khoanh sát mái → tách vùng → so lớp phủ → hiệu chuẩn số đo.</p></div><span>OpenCV · CPU</span></div>
  <div className="tracer-tools">{([['box','Khoanh vùng'],['keep','Giữ mái +'],['remove','Loại nền −'],['polygon','Chấm biên'],['measure','Đo tham chiếu'],['quad','Bốn góc phối cảnh']] as [Tool,string][]).map(([id,label])=><button key={id} className={tool===id?'active':''} disabled={busy} onClick={()=>setTool(id)}>{label}</button>)}</div>
  <p className="tracer-help">{({box:'Kéo khung bao toàn mái, tránh cây và công trình khác.',keep:'Bấm các điểm chắc chắn thuộc mái, kể cả các phần khác màu.',remove:'Bấm các điểm cây/nền/công trình khác cần loại.',polygon:'Bấm lần lượt tất cả góc lồi, lõm. Đừng nối qua khoảng thụt vào.',measure:'Bấm hai đầu một đoạn đã đo thật trên cùng mặt phẳng ảnh.',quad:'Bấm 4 góc theo vòng: trên trái → trên phải → dưới phải → dưới trái, chỉ cho một mặt phẳng hình chữ nhật.'} as Record<Tool,string>)[tool]}</p>
  {tool==='quad'&&<div className="tracer-calibration"><label>Cạnh ngang thật của vùng 4 góc (m)<input type="number" min=".1" max="100" value={quadWidth} onChange={e=>setQuadWidth(Math.max(.1,Number(e.target.value)))}/></label><label>Cạnh dọc thật của vùng 4 góc (m)<input type="number" min=".1" max="100" value={quadDepth} onChange={e=>setQuadDepth(Math.max(.1,Number(e.target.value)))}/></label><p>Nhập hai số đo thật để tránh kéo méo ảnh khi hiệu chỉnh. Sau đó đo tham chiếu lại trên ảnh đã chỉnh.</p></div>}
  <svg ref={svg} viewBox="0 0 100 100" preserveAspectRatio="none" style={{aspectRatio:`${size.w}/${size.h}`}} className="trace-image" aria-label="Ảnh gốc để khoanh vùng, chấm biên và đo tỷ lệ" onPointerDown={down} onPointerMove={move} onPointerUp={()=>{start.current=null}} onPointerCancel={()=>{start.current=null}}>
   <image href={result?.overlay_data_url||url} width="100" height="100" preserveAspectRatio="none"/>
   <rect x={rect[0]} y={rect[1]} width={rect[2]} height={rect[3]} fill="none" stroke="#f6bb4d" strokeWidth=".6" strokeDasharray="2 1"/>
   <polyline points={outline.map(p=>`${p.x},${p.y}`).join(' ')} stroke="#56dbce" strokeWidth=".6" fill="none"/>
   <polyline points={quad.map(p=>`${p.x},${p.y}`).join(' ')} stroke="#d9a1ff" strokeWidth=".6" fill="none"/>
   {measure.length===2&&<line x1={measure[0].x} y1={measure[0].y} x2={measure[1].x} y2={measure[1].y} stroke="#64b8ff" strokeWidth=".7"/>}
   {[[foreground,'#28d97c'],[background,'#ff6079'],[outline,'#56dbce'],[measure,'#64b8ff'],[quad,'#d9a1ff']].map(([list,color],j)=>(list as Point[]).map((p,i)=><circle key={`${j}-${i}`} cx={p.x} cy={p.y} r="1" fill={String(color)} stroke="white" strokeWidth=".25"/>))}
  </svg>
  <div className="tracer-actions"><button className="button primary" disabled={busy||!url} onClick={()=>trace(kind==='plan'?'plan':'grabcut')}>{busy?'Đang xử lý điểm ảnh…':'Tách biên từ vùng chọn'}</button><button className="button secondary" disabled={busy||outline.length<3} onClick={()=>trace('manual')}>Dùng biên đã chấm ({outline.length})</button><button className="button secondary" disabled={busy||quad.length!==4} onClick={()=>trace('rectify')}>Hiệu chỉnh 4 góc</button><button className="text-button" disabled={busy} onClick={()=>{setForeground([]);setBackground([]);setOutline([]);setMeasure([]);setQuad([]);setResult(null)}}>Xóa điểm chọn</button></div>
  <div className="tracer-calibration"><label>Đoạn tham chiếu đã đo thật (m)<input type="number" min=".01" max="100" step=".1" value={knownLength} onChange={e=>setKnownLength(Math.max(.01,Number(e.target.value)))}/></label><label>Hoặc chiều rộng khung mái (m)<input type="number" min=".1" max="100" step=".1" value={target==='roof'&&measuredWidth?measuredWidth:width} disabled={calibrated||(target==='roof'&&!!measuredWidth)} onChange={e=>setWidth(Math.max(.1,Number(e.target.value)))}/></label><label>Giữ chi tiết đường biên<select value={detail} onChange={e=>{setDetail(Number(e.target.value));setResult(null)}}><option value={.001}>Nhiều đỉnh</option><option value={.003}>Cân bằng</option><option value={.008}>Ít đỉnh</option></select></label></div>
  <p className="muted-note">{target==='roof'&&measuredWidth&&measuredLength?'Kích thước toàn mái lấy từ hai số đo thực tế ở bước 1.':calibrated?'Đang dùng đoạn tham chiếu để suy ra cùng một tỷ lệ cho hai chiều.':'Chưa có đoạn tham chiếu: chiều rộng vẫn là số bạn nhập; chiều sâu giữ tỷ lệ ảnh, chưa phải đo đạc.'} Ảnh xiên cần hiệu chỉnh và đối chiếu cả hai cạnh; ảnh một phần không xác định toàn mái.</p>
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {result&&<div className="trace-result"><strong>{result.roof_polygon_pct.length} đỉnh · {actualWidth.toFixed(2)} × {actualHeight.toFixed(2)} m · {Math.round(result.elapsed_ms)} ms</strong><p>{result.notes[0]}</p><div><select aria-label="Áp dụng đường biên cho" value={target} onChange={e=>setTarget(e.target.value as 'roof'|'obstacle')}><option value="roof" disabled={kind==='partial'}>Toàn mái</option><option value="obstacle">Một vật thể / chi tiết</option></select><button className="button primary" disabled={actualWidth>100||actualHeight>100||actualHeight<.1||(target==='roof'&&(!measuredWidth||!measuredLength))} onClick={()=>onApply({result,width:actualWidth,height:actualHeight,target,calibrated,referenceLength:calibrated?knownLength:undefined})}>Áp dụng biên và tỷ lệ</button></div></div>}
 </section>
}
