import {useState} from 'react'
import {DATA_SECTIONS,EVIDENCE_DOC,SOURCES_CHECKED,sourceCounts,type SourceStatus} from '../dataSources'
import {Icon} from './Icon'

const STATUS:Record<SourceStatus,[string,string]>={verified:['Đã đối chiếu','green'],secondary:['Nguồn thứ cấp','amber'],assumption:['Giả định, chưa có nguồn','red']}

/** "Nguồn lấy số liệu": every fixed number, the step that uses it, and the page it was read from, so anyone can check it. */
export function DataSources({onClose}:{onClose:()=>void}){
 const [open,setOpen]=useState<string|null>(DATA_SECTIONS[0].id),[filter,setFilter]=useState<SourceStatus|'all'>('all')
 const c=sourceCounts()
 return <div className="modal-backdrop" onClick={onClose}><section className="history-modal sources-modal" role="dialog" aria-modal="true" aria-label="Nguồn lấy số liệu" onClick={e=>e.stopPropagation()}>
  <div className="card-heading"><h2>Nguồn lấy số liệu</h2><button className="icon-button" onClick={onClose} aria-label="Đóng nguồn số liệu"><Icon name="close"/></button></div>
  <p className="muted-note">Mọi số liệu cố định SolarOpt dùng, chia theo từng bước của ứng dụng, kèm trang gốc để tự kiểm chứng. Đối chiếu lần gần nhất: {SOURCES_CHECKED}. Bảng giá thô và trích dẫn: <code>{EVIDENCE_DOC}</code>. Kỹ sư luôn được thay bằng báo giá và số đo thật của công trình.</p>
  <div className="source-filter" role="group" aria-label="Lọc theo mức kiểm chứng">
   {([['all',`Tất cả (${c.total})`],['verified',`Đã đối chiếu (${c.verified})`],['secondary',`Nguồn thứ cấp (${c.secondary})`],['assumption',`Giả định (${c.assumption})`]] as [SourceStatus|'all',string][]).map(([id,label])=>
    <button key={id} type="button" className={filter===id?'active':''} aria-pressed={filter===id} onClick={()=>setFilter(id)}>{label}</button>)}
  </div>
  {DATA_SECTIONS.map(s=>{const items=s.items.filter(i=>filter==='all'||i.status===filter);if(!items.length)return null;const expanded=open===s.id||filter!=='all'
   return <section key={s.id} className="source-section">
    <button type="button" className="source-section-head" aria-expanded={expanded} onClick={()=>setOpen(expanded&&filter==='all'?null:s.id)}><strong>{s.title}</strong><small>{s.where} · {items.length} mục</small><Icon name="chevron" size={16}/></button>
    {expanded&&<div className="table-scroll"><table className="admin-table source-table"><thead><tr><th>Số liệu</th><th>Giá trị đang dùng</th><th>Nguồn</th><th>Mức kiểm chứng</th></tr></thead><tbody>
     {items.map(i=><tr key={i.name}><td><strong>{i.name}</strong><small>Dùng ở: {i.used}</small></td><td>{i.value}{i.note&&<small>{i.note}</small>}</td>
      <td>{i.sources.length?<ul>{i.sources.map(src=><li key={src.label}>{src.url?<a href={src.url} target="_blank" rel="noreferrer noopener">{src.label}</a>:src.label}</li>)}</ul>:<span className="muted-note">Chưa có nguồn công khai</span>}<small>Đọc ngày {i.checked}</small></td>
      <td><span className={`badge ${STATUS[i.status][1]}`}>{STATUS[i.status][0]}</span></td></tr>)}
    </tbody></table></div>}
   </section>})}
  <p className="muted-note">Cập nhật số liệu: sửa giá trị trong tệp được ghi ở "Dùng ở", rồi sửa nguồn và ngày đọc trong <code>frontend/src/dataSources.ts</code> trong cùng lần commit.</p>
 </section></div>
}
