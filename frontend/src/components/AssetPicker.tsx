import {useState} from 'react'
import {PRESETS,type Preset} from '../assets'

const ICON:Record<string,string>={tank:'◍',chimney:'▮',ac:'▣',stair:'▤',skylight:'◇',tree_round:'●',tree_cone:'▲',tree_palm:'✳',house:'▦'}

/** Library of typical rooftop objects and surroundings; each adds an editable obstacle. */
export function AssetPicker({onAdd}:{onAdd:(p:Preset)=>void}){
 const [open,setOpen]=useState(false)
 return <div className="asset-picker">
  <button type="button" className="button secondary small full-width" aria-expanded={open} onClick={()=>setOpen(v=>!v)}>{open?'Đóng thư viện vật thể':'＋ Thêm từ thư viện vật thể'}</button>
  {open&&(['roof','around'] as const).map(group=><div key={group} className="asset-group">
   <h5>{group==='roof'?'Trên mái':'Xung quanh công trình'}</h5>
   <div className="asset-grid">{PRESETS.filter(p=>p.group===group).map(p=><button key={p.label} type="button" title={p.hint} onClick={()=>onAdd(p)}>
    <span className={`asset-icon ${p.kind}`} aria-hidden="true">{ICON[p.kind]}</span><strong>{p.label}</strong><small>{p.hint}</small></button>)}</div>
  </div>)}
  {open&&<p className="muted-note">Kích thước là giá trị khởi đầu; kéo trên bản vẽ và nhập chiều cao thực tế. Bóng cây tính như khối đặc (thận trọng).</p>}
 </div>
}
