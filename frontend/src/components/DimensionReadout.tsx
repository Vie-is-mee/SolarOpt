import type {DimensionCheck} from '../studioTypes'

const metres=(v:number)=>v.toLocaleString('vi-VN',{maximumFractionDigits:2})+' m'
const AXIS={horizontal:'ngang',vertical:'dọc',other:'xiên'} as const

export function DimensionReadout({check,onFill}:{check:DimensionCheck;onFill:(width:number|null,height:number|null)=>void}){
 const {suggested_width_m:w,suggested_height_m:h}=check
 return <div className="dimension-readout">
  <div className="dimension-heading"><strong>Số đo đọc từ bản vẽ</strong>{check.consistent===true?<span className="badge">Tỉ lệ khớp nhau{check.scale_spread_pct!=null?` (lệch ≤ ${check.scale_spread_pct.toLocaleString('vi-VN')}%)`:''}</span>:check.consistent===false?<span className="badge red">Tỉ lệ lệch {check.scale_spread_pct?.toLocaleString('vi-VN')}%</span>:<span className="badge amber">Chưa kiểm tra chéo</span>}</div>
  <ul>{check.labels.map((l,i)=><li key={i} className={l.outlier?'outlier':''}><code>{l.text||'—'}</code><span>{l.value_m?`${metres(l.value_m)} · ${AXIS[l.axis]}`:'không dùng'}</span><small>{l.outlier?'Lệch tỉ lệ so với các số còn lại':l.interpretation}</small></li>)}</ul>
  {check.notes.map((n,i)=><p key={i} className="muted-note">{n}</p>)}
  {(w||h)?<div className="dimension-fill"><p>Gợi ý: rộng <strong>{w?metres(w):'—'}</strong>{w&&<small> ({check.width_basis})</small>}, dài <strong>{h?metres(h):'—'}</strong>{h&&<small> ({check.height_basis})</small>}.</p><button type="button" className="button secondary small" onClick={()=>onFill(w,h)}>Điền vào ô số đo thực tế</button></div>:<p className="muted-note">Chưa đủ căn cứ để gợi ý kích thước mái; nhập số đo thủ công.</p>}
  <p className="muted-note">Số đọc bằng AI và tỉ lệ ước tính từ vị trí đường kích thước trên ảnh. Kỹ sư phải đối chiếu bản vẽ gốc trước khi dùng.</p>
 </div>
}
