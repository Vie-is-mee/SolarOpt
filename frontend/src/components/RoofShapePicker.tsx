import {useEffect,useState} from 'react'
import type {Config,Panel,RoofFace,Vision} from '../studioTypes'
import {studioApi as api} from '../services/studioApi'

type Shape='flat'|'shed'|'gable'|'hip'|'barrel'|'parabolic'
const SHAPES:{id:Shape;name:string;hint:string}[]=[
 {id:'flat',name:'Mái bằng',hint:'Một mặt phẳng ngang'},
 {id:'shed',name:'Mái một dốc',hint:'Một mặt nghiêng từ phía thấp lên phía cao'},
 {id:'gable',name:'Mái chữ A (2 dốc)',hint:'Hai mặt gặp nhau ở đường nóc'},
 {id:'hip',name:'Mái 4 dốc',hint:'Hai mặt dốc chính và hai mặt đầu hồi tam giác'},
 {id:'barrel',name:'Mái vòm cung',hint:'Chia thành các dải phẳng bám theo cung tròn'},
 {id:'parabolic',name:'Mái vòm parabol',hint:'Chia thành các dải phẳng bám theo parabol'},
]
const NAMES:Record<string,string>={flat:'mái bằng',shed:'mái một dốc',gable:'mái chữ A',hip:'mái 4 dốc',barrel:'mái vòm cung',parabolic:'mái vòm parabol',other:'dạng khác',unknown:'chưa rõ'}

export function RoofShapePicker({config,panel,vision,onFaces}:{config:Config;panel:Panel;vision:Vision|null;onFaces:(faces:RoofFace[],notes:string[])=>void}){
 const [shape,setShape]=useState<Shape>('gable'),[axis,setAxis]=useState<'x'|'y'>('x'),[rise,setRise]=useState('2'),[low,setLow]=useState<'start'|'end'>('start')
 const [busy,setBusy]=useState(false),[notes,setNotes]=useState<string[]>([]),[error,setError]=useState('')
 // Curved roofs: strips follow the panel rows unless the engineer gives a count (a segmented vault).
 const [strips,setStrips]=useState('')
 // Scope: the whole roof, or a smaller roof stacked on a region of the existing one (raised gable, second tier).
 const [part,setPart]=useState(false),[region,setRegion]=useState({x:'',y:'',w:'',d:''}),[eave,setEave]=useState('')
 const suggested=vision?.roof_shape&&vision.roof_shape!=='unknown'?vision.roof_shape:null
 // Prefill from the AI reading once; the engineer can still change every field before generating.
 useEffect(()=>{if(!vision)return;if(suggested&&SHAPES.some(s=>s.id===suggested))setShape(suggested as Shape);if(vision.ridge_axis==='horizontal')setAxis('x');if(vision.ridge_axis==='vertical')setAxis('y');if(vision.rise_m)setRise(String(vision.rise_m))},[vision])
 const W=config.roof_width_m,D=config.roof_height_m
 // Default stacked region: the middle third of the frame.
 const box=[Number(region.x||W/3),Number(region.y||D/3),Number(region.w||W/3),Number(region.d||D/3)]
 const regionValid=box.every(Number.isFinite)&&box[2]>=.5&&box[3]>=.5&&box[0]>=0&&box[1]>=0&&box[0]+box[2]<=W+1e-6&&box[1]+box[3]<=D+1e-6
 const curved=shape==='barrel'||shape==='parabolic',stripCount=strips?Number(strips):null
 async function generate(){setBusy(true);setError('');try{const r=await api.roofTemplate({config:part?config:{...config,roof_faces:[]},shape,ridge_axis:axis,rise_m:shape==='flat'?0.01:Number(rise),low_side:low,panel_pitch_m:Math.min(panel.width_m,panel.height_m)+config.panel_gap_m,strips:curved?stripCount:null,...(part?{region:box.map(v=>Math.round(v*1000)/1000),eave_m:eave.trim()?Number(eave):null}:{})});setNotes(r.notes);onFaces(r.roof_faces,r.notes)}catch(e){setError(e instanceof Error?e.message:'Không tạo được mặt mái.')}finally{setBusy(false)}}
 const riseValid=(shape==='flat'||(Number(rise)>0&&Number(rise)<=50))&&(!curved||!strips||(Number.isInteger(stripCount)&&stripCount!>=2&&stripCount!<=20))&&(!part||(regionValid&&(!eave.trim()||(Number(eave)>=0&&Number(eave)<=300))))
 const num=(label:string,value:string,set:(v:string)=>void,placeholder:string,unit='m')=><label className="field"><span>{label}</span><div className="input-wrap"><input aria-label={label} type="number" min={0} step={.1} value={value} placeholder={placeholder} onChange={e=>set(e.target.value)}/><small>{unit}</small></div></label>
 return <div className="card roof-shape-picker">
  <div className="card-heading"><div className="card-title"><div><h3>Dạng mái</h3><p>Mọi dạng mái được đưa về các mặt phẳng nhỏ; bóng, bức xạ và xếp tấm tính theo từng mặt.</p></div></div></div>
  {suggested&&<p className="muted-note">AI gợi ý: <strong>{NAMES[suggested]||suggested}</strong>{vision?.ridge_axis&&vision.ridge_axis!=='unknown'?`, nóc theo chiều ${vision.ridge_axis==='horizontal'?'ngang':'dọc'} ảnh`:''}{vision?.rise_m?`, cao đỉnh ${vision.rise_m} m`:''}. Kiểm tra lại trước khi tạo.</p>}
  <div className="segmented roof-scope" role="group" aria-label="Phạm vi dựng mái"><button type="button" className={!part?'active':''} onClick={()=>setPart(false)}>Toàn bộ mái</button><button type="button" className={part?'active':''} onClick={()=>setPart(true)}>Mái phụ chồng lên một vùng</button></div>
  {part&&<><p className="muted-note">Mái phụ thay phần mái bên dưới nó trên mặt bằng; phần còn lại giữ nguyên độ dốc, hướng. Lặp lại để chồng nhiều cấp (mái chữ A nhỏ trên mái chữ A lớn, mái tum, mái chéo). Tọa độ tính từ góc trái dưới bản vẽ ({W.toLocaleString('vi-VN',{maximumFractionDigits:2})} × {D.toLocaleString('vi-VN',{maximumFractionDigits:2})} m).</p>
  <div className="field-grid four">{num('Mái phụ: cách mép trái',region.x,v=>setRegion(r=>({...r,x:v})),(W/3).toFixed(2))}{num('cách mép dưới',region.y,v=>setRegion(r=>({...r,y:v})),(D/3).toFixed(2))}{num('rộng',region.w,v=>setRegion(r=>({...r,w:v})),(W/3).toFixed(2))}{num('sâu',region.d,v=>setRegion(r=>({...r,d:v})),(D/3).toFixed(2))}</div>
  {num('Cao độ diềm mái phụ',eave,setEave,'Tự động: đặt lên đỉnh mái bên dưới')}
  {!regionValid&&<p className="tracer-error">Vùng mái phụ phải nằm trong khung mái và rộng, sâu ít nhất 0,5 m.</p>}</>}
  <div className="shape-grid">{SHAPES.map(s=><button key={s.id} type="button" className={shape===s.id?'selected':''} onClick={()=>setShape(s.id)} title={s.hint}><strong>{s.name}</strong><small>{s.hint}</small></button>)}</div>
  {shape!=='flat'&&<div className="field-grid">
   <label className="field"><span>{shape==='shed'?'Chiều dốc':'Đường nóc chạy theo'}</span><select value={axis} onChange={e=>setAxis(e.target.value as 'x'|'y')}><option value="x">{shape==='shed'?'Dốc theo chiều dọc bản vẽ':'Chiều ngang bản vẽ'}</option><option value="y">{shape==='shed'?'Dốc theo chiều ngang bản vẽ':'Chiều dọc bản vẽ'}</option></select></label>
   <label className="field"><span>{shape==='shed'?'Chênh cao giữa hai mép':'Chiều cao đỉnh so với diềm'}</span><div className="input-wrap"><input type="number" min={.1} max={50} step={.1} value={rise} onChange={e=>setRise(e.target.value)}/><small>m</small></div></label>
   {curved&&<label className="field"><span>Số dải phẳng</span><div className="input-wrap"><input aria-label="Số dải phẳng của vòm" type="number" min={2} max={20} step={1} value={strips} placeholder="Tự động theo hàng tấm" onChange={e=>setStrips(e.target.value)}/><small>dải</small></div><em>Để trống: mỗi dải một hàng tấm, lệch ≤ 5 cm so với cung. Nhập số khi vòm ghép từ các tấm phẳng có số đoạn cụ thể.</em></label>}
   {shape==='shed'&&<label className="field"><span>Phía thấp</span><select value={low} onChange={e=>setLow(e.target.value as 'start'|'end')}><option value="start">{axis==='x'?'Mép dưới bản vẽ':'Mép trái bản vẽ'}</option><option value="end">{axis==='x'?'Mép trên bản vẽ':'Mép phải bản vẽ'}</option></select></label>}
  </div>}
  {!part&&<p className="muted-note">Cao độ diềm lấy theo "Cao độ mái tại gốc bản vẽ" ({config.roof_elevation_m} m). Mặt mái tạo ra thay cho các phần mái đã vẽ trước đó.</p>}
  <div className="inline-actions"><button type="button" className="button primary small" disabled={busy||!riseValid} onClick={generate}>{busy?'Đang tạo…':part?'Thêm mái phụ':'Tạo các mặt mái'}</button>{(config.roof_faces||[]).length>0&&<button type="button" className="text-button danger" onClick={()=>{setNotes([]);onFaces([],[])}}>Xóa các mặt mái</button>}</div>
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {notes.length>0&&<ul className="sizing-notes">{notes.map((n,i)=><li key={i}>{n}</li>)}</ul>}
 </div>
}
