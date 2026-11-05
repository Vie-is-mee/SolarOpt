import {calculateScenarios,type Economics,type Site} from '../economics'
import {vnd} from '../format'

const num=(v:number,d=1)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
type Scenarios=ReturnType<typeof calculateScenarios>

/** Range of outcomes for the same layout: pessimistic, base and optimistic assumptions side by side,
 * so a customer or investor sees how far the answer can move instead of one fixed number. */
export function ScenarioTable({scenarios,years,compact=false}:{scenarios:Scenarios;years:number;compact?:boolean}){
 const rows:[string,(s:Scenarios[number])=>string,string?][]=[
  ['Suất đầu tư',s=>s.result.costPerKwp!=null?`${num(s.result.costPerKwp/1e6)} tr đ/kWp`:'—'],
  ['Tổng đầu tư',s=>vnd(s.result.total)],
  ['Sản lượng năm đầu',s=>`${num(s.energy,0)} kWh`,'nắng, bụi bẩn, thời tiết'],
  ['Điện dùng tại chỗ',s=>`${num(s.econ.self_use_pct??0,0)}% · ${num(s.econ.buy_price??0,0)} đ/kWh`],
  ['Giá bán điện dư',s=>`${num(s.econ.sell_price??0,0)} đ/kWh`,'tối đa 50% sản lượng'],
  ['Lợi ích ròng năm 1',s=>vnd(s.result.rows[1]?.net??0)],
  ['Hoàn vốn',s=>s.result.payback!=null?`${num(s.result.payback)} năm`:`> ${years} năm`],
  ['Tỷ suất hoàn vốn nội bộ (IRR)',s=>s.result.irr!=null?`${num(s.result.irr*100)}%`:'—'],
  [`NPV (chiết khấu)`,s=>`${vnd(s.result.npv)} · ${num(s.econ.discount_pct??0)}%`],
  ['Giá thành điện (LCOE)',s=>s.result.lcoe!=null?`${num(s.result.lcoe,0)} đ/kWh`:'—','so với giá mua EVN'],
  [`Lợi ích ròng ${years} năm`,s=>vnd(s.result.netBenefit)],
 ]
 return <div className="table-scroll"><table className={'data-table scenario-table'+(compact?' compact':'')}>
  <caption>Cùng một bố trí, ba bộ giả định: kết quả thật nằm trong khoảng này</caption>
  <thead><tr><th>Chỉ tiêu</th>{scenarios.map(s=><th key={s.id} className={'num scenario-'+s.id} title={s.hint}>{s.name}</th>)}</tr></thead>
  <tbody>{rows.map(([label,value,hint])=><tr key={label}><td>{label}{hint&&!compact&&<small> · {hint}</small>}</td>{scenarios.map(s=><td key={s.id} className={'num scenario-'+s.id+(s.id==='base'?' strong':'')}>{value(s)}</td>)}</tr>)}</tbody>
 </table></div>
}

export function scenarioSummary(a:Economics,panelCost:number,energy:number,kwp:number,site?:Site|null){
 const s=calculateScenarios(a,panelCost,energy,kwp,site),[low,base,high]=s.map(x=>x.result)
 const pb=(v:number|null)=>v==null?`trên ${a.years} năm`:`${num(v)} năm`
 return {scenarios:s,text:`Tổng đầu tư ${vnd(high.total)} – ${vnd(low.total)} (cơ sở ${vnd(base.total)}); hoàn vốn ${pb(high.payback)} đến ${pb(low.payback)} (cơ sở ${pb(base.payback)}); NPV từ ${vnd(low.npv)} đến ${vnd(high.npv)}.`}
}
