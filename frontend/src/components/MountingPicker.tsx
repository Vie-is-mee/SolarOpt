import {useState} from 'react'
import type {Config,Obstacle,Panel} from '../studioTypes'
import {studioApi as api} from '../services/studioApi'

type Mounting='flush'|'tilted_rack'|'tracker'
type Option={label:string;settings:Partial<Config>&{mounting:Mounting};panels:number;kwp:number;annual_kwh:number;kwh_per_panel:number;vs_flush_pct:number|null}
type Comparison={options:Option[];best:string|null;notes:string[]}
const KINDS:{id:Mounting;name:string;hint:string}[]=[
 {id:'flush',name:'Lắp sát mái',hint:'Tấm nằm theo mặt mái, xếp sát nhau'},
 {id:'tilted_rack',name:'Giá nghiêng xếp hàng',hint:'Tấm nghiêng về một hướng, hàng cách nhau để không che nhau'},
 {id:'tracker',name:'Pin xoay theo mặt trời',hint:'Xoay 1 trục Bắc–Nam theo mặt trời Đông sang Tây, tự lùi góc để không che hàng sau'},
]
const num=(v:number,d=0)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})

export function MountingPicker({config,panel,obstacles,onChange}:{config:Config;panel:Panel;obstacles:Obstacle[];onChange:(patch:Partial<Config>)=>void}){
 const mounting=(config.mounting||'flush') as Mounting
 const [result,setResult]=useState<Comparison|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 async function compare(){setBusy(true);setError('');try{setResult(await api.mountingCompare(config,panel,obstacles))}catch(e){setError(e instanceof Error?e.message:'Chưa so sánh được.')}finally{setBusy(false)}}
 return <div className="mounting-picker">
  <div className="field"><span>Cách lắp trên mặt mái bằng</span>
   <div className="shape-grid">{KINDS.map(k=><button key={k.id} type="button" className={mounting===k.id?'selected':''} title={k.hint} onClick={()=>onChange({mounting:k.id})}><strong>{k.name}</strong><small>{k.hint}</small></button>)}</div>
  </div>
  {mounting==='tilted_rack'&&<div className="field-grid">
   <label className="field"><span>Góc nghiêng tấm</span><div className="input-wrap"><input type="number" min={1} max={45} step={1} value={config.rack_tilt_deg??15} onChange={e=>onChange({rack_tilt_deg:Number(e.target.value)})}/><small>°</small></div><em>Ở Việt Nam thường 10–15°; từ 10° mưa tự rửa bụi tốt hơn.</em></label>
   <label className="field"><span>Hướng tấm quay về</span><div className="input-wrap"><input type="number" min={0} max={360} step={5} value={config.rack_azimuth_deg??180} onChange={e=>onChange({rack_azimuth_deg:Number(e.target.value)})}/><small>°</small></div><em>180° là hướng Nam. Khoảng cách hàng tự tính để ngày đông chí 9h–15h không che nhau.</em></label>
  </div>}
  {mounting==='tracker'&&<div className="field-grid">
   <label className="field"><span>Hệ số phủ GCR</span><div className="input-wrap"><input type="number" min={.2} max={.8} step={.05} value={config.tracker_gcr??.4} onChange={e=>onChange({tracker_gcr:Number(e.target.value)})}/><small></small></div><em>Bề rộng tấm chia khoảng cách hàng. Nhỏ hơn: hàng thưa, ít phải lùi góc nhưng ít tấm.</em></label>
   <label className="field"><span>Góc xoay tối đa</span><div className="input-wrap"><input type="number" min={20} max={70} step={5} value={config.tracker_max_angle_deg??55} onChange={e=>onChange({tracker_max_angle_deg:Number(e.target.value)})}/><small>°</small></div></label>
  </div>}
  {mounting!=='flush'&&<p className="muted-note">Chỉ áp dụng cho mặt mái bằng; mặt dốc vẫn lắp sát mái. Chưa tính chi phí giá đỡ/bộ xoay và tải gió.</p>}
  <button type="button" className="button secondary small" disabled={busy} onClick={compare}>{busy?'Đang so sánh 7 cách lắp…':'So sánh các cách lắp trên mái này'}</button>
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {result&&<div className="table-scroll"><table className="mounting-table"><caption>Cùng mái, cùng tấm, cùng ngân sách · mục tiêu sản lượng cao nhất</caption>
   <thead><tr><th>Cách lắp</th><th>Số tấm</th><th>kWh/năm</th><th>kWh mỗi tấm</th><th>So với sát mái</th><th></th></tr></thead>
   <tbody>{result.options.map(o=><tr key={o.label} className={o.label===result.best?'recommended':''}>
    <td>{o.label}{o.label===result.best&&<strong> · Cao nhất</strong>}</td><td>{o.panels}</td><td>{num(o.annual_kwh)}</td><td>{num(o.kwh_per_panel)}</td>
    <td>{o.vs_flush_pct===null?'—':`${o.vs_flush_pct>0?'+':''}${num(o.vs_flush_pct,1)}%`}</td>
    <td><button type="button" className="text-button" onClick={()=>onChange(o.settings)}>Dùng cách này</button></td></tr>)}</tbody></table>
   <ul className="sizing-notes">{result.notes.map(n=><li key={n}>{n}</li>)}</ul></div>}
 </div>
}
