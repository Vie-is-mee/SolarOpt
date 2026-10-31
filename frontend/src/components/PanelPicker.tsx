import {useState} from 'react'
import type {Panel} from '../studioTypes'
import {MoneyInput} from './MoneyInput'
import {BUILTIN_PANELS,panelErrors,panelKey,readCustomPanels,writeCustomPanels} from '../panelLibrary'

const FIELDS:[keyof Panel,string,string,number][]=[['power_w','Công suất','W',1],['price_vnd','Giá một tấm','đ',100000],['width_m','Rộng','m',.001],['height_m','Dài','m',.001],['voc_v','Voc','V',.01],['vmp_v','Vmp','V',.01],['imp_a','Imp','A',.01]]
const blank=():Panel=>({manufacturer:'',model:'',width_m:1.134,height_m:2.278,power_w:0,price_vnd:0,voc_v:0,vmp_v:0,imp_a:0})

export function PanelPicker({panel,onChange}:{panel:Panel;onChange:(p:Panel)=>void}){
 const [custom,setCustom]=useState(readCustomPanels),[draft,setDraft]=useState<Panel|null>(null),[tried,setTried]=useState(false)
 const all=[...BUILTIN_PANELS,...custom],current=all.find(p=>panelKey(p)===panelKey(panel))
 const edited=current&&FIELDS.some(([k])=>current[k]!==panel[k])
 const isCustom=!!custom.find(p=>panelKey(p)===panelKey(panel))
 const errors=draft?panelErrors(draft):[],duplicate=draft&&all.some(p=>panelKey(p)===panelKey(draft))
 function save(){setTried(true);if(!draft||errors.length||duplicate)return
  const p={...draft,manufacturer:draft.manufacturer.trim(),model:draft.model.trim()},next=[...custom,p]
  setCustom(next);writeCustomPanels(next);onChange(p);setDraft(null);setTried(false)}
 function remove(){const next=custom.filter(p=>panelKey(p)!==panelKey(panel));setCustom(next);writeCustomPanels(next);onChange({...BUILTIN_PANELS[0]})}
 return <div className="panel-picker">
  <div className="field"><span>Tấm pin</span><div className="panel-picker-row">
   <select aria-label="Chọn loại tấm pin" value={current?panelKey(current):''} onChange={e=>{const p=all.find(v=>panelKey(v)===e.target.value);if(p)onChange({...p})}}>
    {!current&&<option value="">{panel.manufacturer} {panel.model} (từ dự án)</option>}
    <optgroup label="Thư viện tham khảo">{BUILTIN_PANELS.map(p=><option key={panelKey(p)} value={panelKey(p)}>{p.manufacturer} {p.model}</option>)}</optgroup>
    {custom.length>0&&<optgroup label="Do bạn thêm">{custom.map(p=><option key={panelKey(p)} value={panelKey(p)}>{p.manufacturer} {p.model}</option>)}</optgroup>}
   </select>
   <button type="button" className="button secondary small" aria-label="Thêm loại tấm pin" title="Thêm loại tấm pin" onClick={()=>{setDraft(draft?null:blank());setTried(false)}}>{draft?'×':'+'}</button>
  </div>
  <em>{edited?'Đã chỉnh thông số so với thư viện. ':''}Thông số thư viện là giá trị tham khảo, giá là giả định — đối chiếu datasheet và báo giá thực tế.{isCustom&&<> <button type="button" className="text-button danger" onClick={remove}>Xóa loại pin này</button></>}</em></div>
  {draft&&<div className="panel-form">
   <div className="field-grid">
    <label className="field"><span>Hãng</span><input value={draft.manufacturer} onChange={e=>setDraft({...draft,manufacturer:e.target.value})}/></label>
    <label className="field"><span>Model</span><input value={draft.model} onChange={e=>setDraft({...draft,model:e.target.value})}/></label>
    {FIELDS.map(([k,label,unit,step])=>k==='price_vnd'?<MoneyInput key={k} label={label} value={draft.price_vnd||null} onChange={v=>setDraft({...draft,price_vnd:v??0})}/>:<label key={k} className="field"><span>{label}</span><div className="input-wrap"><input type="number" min={0} step={step} value={draft[k]||''} onChange={e=>setDraft({...draft,[k]:Number(e.target.value)})}/><small>{unit}</small></div></label>)}
   </div>
   {tried&&(errors.length>0||duplicate)&&<ul className="panel-form-errors">{duplicate&&<li>Đã có loại pin cùng hãng và model</li>}{errors.map(e=><li key={e}>{e}</li>)}</ul>}
   <div className="inline-actions"><button type="button" className="button primary small" onClick={save}>Lưu và dùng loại pin này</button><button type="button" className="text-button" onClick={()=>setDraft(null)}>Hủy</button></div>
   <p className="muted-note">Lưu trong trình duyệt này và trong tệp dự án khi xuất JSON.</p>
  </div>}
 </div>
}
