import {useEffect, useState} from 'react'
import {describeFact, type ApplyPlan, type Customer, type Need, type Proposal, type ProposalRound, type Scenario} from '../advisorTypes'
import type {Config, Obstacle, Panel} from '../studioTypes'
import {studioApi as api} from '../services/studioApi'
import {CardHead} from './CardHead'
import {Icon} from './Icon'
import {MoneyInput} from './MoneyInput'
import {OBJECTIVES} from './DesignOptions'

export type AdvisorState={need:Need;customer:Customer;rounds:ProposalRound[]}
const money=(v:number)=>Math.abs(v)>=1e9?(v/1e9).toLocaleString('vi-VN',{maximumFractionDigits:2})+' tỷ đ':Math.round(v/1e6).toLocaleString('vi-VN')+' triệu đ'
const n=(v:number|null|undefined,d=1)=>v===null||v===undefined?'—':v.toLocaleString('vi-VN',{maximumFractionDigits:d})
const NEEDS=OBJECTIVES.filter(o=>o.id==='max_energy'||o.id==='min_cost'||o.id==='robust') as {id:Need;name:string;desc:string;icon:string}[]
const NOTE_IDEAS=['Khách chốt ngân sách tối đa 80 triệu','Chừa lối đi bảo trì quanh mép mái','Khách chủ yếu dùng điện buổi tối','Ưu tiên hoàn vốn dưới 6 năm']

/** Customer need in, reasoned proposal out: scenarios computed by SolarOpt, reasons that cite those numbers,
 * a feedback box that re-plans with the engineer's notes, and "Áp dụng" that runs the chosen scenario. */
export function AdvisorPanel({value,onChange,config,panel,obstacles,confirmed,disabled,onApply,demo=false,demoNote}:{value:AdvisorState;onChange:(v:AdvisorState)=>void;config:Config;panel:Panel;obstacles:Obstacle[];confirmed:boolean;disabled:boolean;demo?:boolean;demoNote?:string;onApply:(plan:ApplyPlan,scenario:Scenario,proposal:Proposal)=>void}){
 const [status,setStatus]=useState<{llm:boolean;model:string}|null>(null)
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[note,setNote]=useState('')
 const [viewing,setViewing]=useState(value.rounds.length-1),[picked,setPicked]=useState<string|null>(null)
 useEffect(()=>{api.advisorStatus().then(setStatus).catch(()=>setStatus(null))},[])
 useEffect(()=>{setViewing(value.rounds.length-1);setPicked(null)},[value.rounds.length])
 const round=value.rounds[viewing],p=round?.proposal
 const c=value.customer,setC=(patch:Partial<Customer>)=>onChange({...value,customer:{...c,...patch}})
 const chosenId=picked||p?.recommended_id,chosen=p?.scenarios.find(s=>s.id===chosenId)

 async function ask(feedback:string|null){
  if(!confirmed){setError('Xác nhận biên mái, hướng và vật cản ở bước Xác nhận bản vẽ trước khi nhờ trợ lý đề xuất.');return}
  setBusy(true);setError('')
  try{
   const notes=[...value.rounds.map(r=>r.feedback).filter((f):f is string=>!!f),...(feedback?[feedback]:[])]
   const proposal=await api.propose({config,panel,obstacles,need:value.need,customer:c,feedback:notes,previous:feedback?p??null:null,demo})
   onChange({...value,rounds:feedback?[...value.rounds,{proposal,feedback}]:[{proposal,feedback:null}]});setNote('')
  }catch(e){setError(e instanceof Error?e.message:'Chưa lập được đề xuất.')}
  finally{setBusy(false)}
 }

 const badge=status?.llm?<span className="advisor-badge ai" title={`Mô hình ${status.model}`}><Icon name="sparkles" size={13}/>AI · {status.model}</span>:<span className="advisor-badge rules" title="Máy chủ chưa có khóa AI; bộ quy tắc của SolarOpt lập đề xuất bằng cùng công cụ tính toán">Bộ quy tắc</span>
 return <section className="card advisor-panel" aria-busy={busy}>
  <CardHead icon="sparkles" title="Trợ lý đề xuất phương án" sub="Trợ lý suy luận theo nhu cầu khách; mọi con số do bộ tối ưu và dòng tiền của SolarOpt tính" action={badge}/>
  <details className="advisor-inputs" open={!p}>
   <summary>Nhu cầu và thông tin khách{p?` · ${NEEDS.find(x=>x.id===value.need)?.name}`:''}</summary>
   <div className="advisor-needs" role="radiogroup" aria-label="Nhu cầu của khách">{NEEDS.map(o=><button key={o.id} type="button" role="radio" aria-checked={value.need===o.id} className={value.need===o.id?'on':''} onClick={()=>onChange({...value,need:o.id})}><Icon name={o.icon} size={16}/><strong>{o.name}</strong><small>{o.desc}</small></button>)}</div>
   <div className="field-grid three">
    <MoneyInput label="Tiền điện mỗi tháng" value={c.monthly_bill_vnd} onChange={v=>setC({monthly_bill_vnd:v})} help="Hoặc nhập số kWh bên cạnh"/>
    <label className="field"><span>Điện tiêu thụ mỗi tháng</span><div className="input-wrap"><input aria-label="Điện tiêu thụ mỗi tháng" type="number" min="0" value={c.monthly_kwh??''} placeholder="Theo hóa đơn" onChange={e=>setC({monthly_kwh:e.target.value===''?null:Number(e.target.value)})}/><small>kWh</small></div></label>
    <label className="field"><span>Biểu giá</span><select aria-label="Biểu giá" value={c.tariff} onChange={e=>setC({tariff:e.target.value as Customer['tariff']})}><option value="residential">Sinh hoạt (bậc thang EVN)</option><option value="business">Kinh doanh</option></select></label>
    {c.tariff==='business'&&<label className="field"><span>Giá điện bình quân (chưa VAT)</span><div className="input-wrap"><input aria-label="Giá điện bình quân" type="number" min="0" value={c.business_price_vnd_kwh??''} placeholder="Theo hóa đơn" onChange={e=>setC({business_price_vnd_kwh:e.target.value===''?null:Number(e.target.value)})}/><small>đ/kWh</small></div></label>}
    <label className="field"><span>Điện dùng ban ngày (7h–17h)</span><div className="input-wrap"><input aria-label="Điện dùng ban ngày" type="number" min="0" max="100" value={c.daytime_share_pct??''} placeholder={c.tariff==='business'?'Mặc định 60':'Mặc định 35'} onChange={e=>setC({daytime_share_pct:e.target.value===''?null:Number(e.target.value)})}/><small>%</small></div></label>
    <MoneyInput label="Ngân sách tối đa của khách" value={c.budget_vnd} onChange={v=>setC({budget_vnd:v})} help="Trọn gói; bỏ trống nếu chưa biết"/>
    <label className="field"><span>Suất đầu tư trọn gói</span><div className="input-wrap"><input aria-label="Suất đầu tư trọn gói của trợ lý" type="number" min="0" step="0.1" value={c.capex_million_per_kwp??''} placeholder="Đơn giá tham khảo" onChange={e=>setC({capex_million_per_kwp:e.target.value===''?null:Number(e.target.value)})}/><small>triệu đ/kWp</small></div></label>
   </div>
   <label className="field"><span>Ghi chú của khách</span><textarea aria-label="Ghi chú của khách" value={c.notes} placeholder="Ví dụ: sắp lắp thêm 2 máy lạnh, muốn giữ sân phơi phía Bắc" onChange={e=>setC({notes:e.target.value})}/></label>
   <button type="button" className="button primary" disabled={busy||disabled} onClick={()=>ask(null)}><Icon name="sparkles" size={16}/>{busy&&!value.rounds.length?'Đang suy luận và tính các kịch bản…':p?'Lập lại đề xuất từ đầu':'Đề xuất phương án'}</button>
  </details>
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {busy&&<p className="advisor-progress" role="status"><i/>Trợ lý đang thử các kịch bản trên mái thật; mỗi kịch bản chạy bộ tối ưu vài giây…</p>}
  {p&&<div className="advisor-result">
   {value.rounds.length>1&&<div className="advisor-rounds" role="tablist" aria-label="Các phiên bản đề xuất">{value.rounds.map((r,i)=><button key={i} type="button" role="tab" aria-selected={i===viewing} className={i===viewing?'on':''} onClick={()=>{setViewing(i);setPicked(null)}} title={r.feedback||'Đề xuất đầu tiên'}>v{i+1}{r.feedback?' · sau góp ý':''}</button>)}</div>}
   {p.replay&&<p className="replay-note"><Icon name="history" size={14}/>{p.replay}</p>}
   {p.notice&&<p className="advisor-notice"><Icon name="info" size={14}/>{p.notice}</p>}
   {round.feedback&&<p className="advisor-feedback-echo"><Icon name="history" size={14}/>Soạn lại theo góp ý: “{round.feedback}”</p>}
   <p className="advisor-summary">{p.summary}</p>
   {chosen&&<div className="advisor-kpis">
    <div><span>Quy mô</span><strong>{chosen.panel_count} tấm</strong><small>{n(chosen.peak_power_kwp,2)} kWp</small></div>
    <div><span>Sản lượng</span><strong>{n(chosen.annual_energy_kwh,0)}</strong><small>kWh/năm{chosen.coverage_pct!==null?` · đáp ứng ${n(chosen.coverage_pct)}%`:''}</small></div>
    <div><span>Vốn đầu tư</span><strong>{money(chosen.investment_vnd)}</strong><small>{n(chosen.peak_power_kwp>0?chosen.investment_vnd/chosen.peak_power_kwp/1e6:p.capex_million_per_kwp,2)} triệu đ/kWp</small></div>
    <div className="accent"><span>Ngân sách đề xuất</span><strong>{money(p.recommended_budget_vnd)}</strong><small>gồm 10% dự phòng</small></div>
    <div><span>Hoàn vốn</span><strong>{chosen.payback_years!==null?n(chosen.payback_years)+' năm':'Chưa hoàn vốn'}</strong><small>NPV {money(chosen.npv_vnd)}</small></div>
    <div><span>Điện tiêu thụ</span><strong>{p.consumption.annual_kwh!==null?n(p.consumption.annual_kwh,0):'Chưa rõ'}</strong><small>kWh/năm · ban ngày {n(p.consumption.daytime_share_pct)}%</small></div>
   </div>}
   <div className="table-scroll"><table className="data-table advisor-table"><caption>Các kịch bản trợ lý đã thử · bấm một dòng để xem hoặc áp dụng</caption>
    <thead><tr><th>Kịch bản</th><th className="num">Tấm</th><th className="num">kWh/năm</th><th className="num">Đáp ứng</th><th className="num">Tự dùng</th><th className="num">Vốn</th><th className="num">Hoàn vốn</th><th className="num">NPV</th></tr></thead>
    <tbody>{p.scenarios.map(s=><tr key={s.id} className={(s.id===chosenId?'picked ':'')+(s.id===p.recommended_id?'recommended':'')} onClick={()=>setPicked(s.id)} tabIndex={0} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setPicked(s.id)}}} aria-selected={s.id===chosenId}>
     <td><strong>{s.id} · {s.label}</strong>{s.id===p.recommended_id&&<em>Khuyến nghị</em>}{s.intent&&<small>{s.intent}</small>}{(s.params.extra_daytime_kwh_year||s.params.edge_reserve_m)?<small className="advisor-tags">{s.params.extra_daytime_kwh_year?<span>+{n(s.params.extra_daytime_kwh_year,0)} kWh/năm dùng ban ngày</span>:null}{s.params.edge_reserve_m?<span>lùi mép {n(s.params.edge_reserve_m*100,0)} cm</span>:null}</small>:null}</td>
     <td className="num">{s.panel_count}</td><td className="num">{n(s.annual_energy_kwh,0)}</td><td className="num">{s.coverage_pct!==null?n(s.coverage_pct)+'%':'—'}</td><td className="num">{n(s.self_use_pct)}%</td>
     <td className="num">{money(s.investment_vnd)}</td><td className="num">{s.payback_years!==null?n(s.payback_years)+' năm':'—'}</td><td className={'num '+(s.npv_vnd<0?'neg':'')}>{money(s.npv_vnd)}</td></tr>)}</tbody></table></div>
   <h4 className="form-group-title">Vì sao đề xuất như vậy</h4>
   <ul className="advisor-reasons">{p.reasons.map((r,i)=><li key={i}><span>{r.text}</span>{r.refs.length>0&&<span className="advisor-refs">{r.refs.map(k=>{const f=describeFact(k,p.facts[k]);return <i key={k} title={`Dữ kiện ${k}, do SolarOpt tính`}>{f.label}: <b>{f.value}</b></i>})}</span>}</li>)}</ul>
   {p.risks.length>0&&<><h4 className="form-group-title">Rủi ro cần lưu ý</h4><ul className="advisor-risks">{p.risks.map((r,i)=><li key={i}>{r}</li>)}</ul></>}
   {p.questions.length>0&&<><h4 className="form-group-title">Nên hỏi thêm khách</h4><ul className="advisor-questions">{p.questions.map((q,i)=><li key={i}>{q}</li>)}</ul></>}
   <details className="advisor-more"><summary>Giả định, nguồn số liệu và các bước suy luận</summary><ul>{p.assumptions.map((a,i)=><li key={i}>{a}</li>)}</ul><ol>{p.trace.map((t,i)=><li key={i}><b>{t.step}</b> {t.detail}</li>)}</ol><p>{p.mode==='llm'?`Mô hình ${p.model}`:'Bộ quy tắc SolarOpt'} · {n(p.elapsed_ms/1000)} giây</p></details>
   <div className="advisor-feedback">
    <label className="field"><span>Góp ý để trợ lý soạn lại (kèm lý do)</span><textarea aria-label="Góp ý cho trợ lý" value={note} placeholder="Ví dụ: Khách chốt ngân sách tối đa 90 triệu vì vay ngân hàng; chừa lối đi phía Bắc để phơi đồ." onChange={e=>setNote(e.target.value)}/></label>
    <div className="advisor-ideas">{(demoNote?[demoNote,...NOTE_IDEAS]:NOTE_IDEAS).map(t=><button key={t} type="button" onClick={()=>setNote(v=>v?v+'; '+t.toLowerCase():t)}>{t}</button>)}</div>
    <div className="advisor-actions">
     <button type="button" className="button secondary" disabled={busy||disabled||!note.trim()} onClick={()=>ask(note.trim())}><Icon name="history" size={16}/>Soạn lại đề xuất</button>
     {chosen&&<button type="button" className="button primary" disabled={busy||disabled||!chosen.panel_count} onClick={()=>onApply(p.plans[chosen.id]??p.apply,chosen,p)}><Icon name="check" size={16}/>Áp dụng {chosen.id} và tính phương án</button>}
    </div>
   </div>
  </div>}
 </section>
}
