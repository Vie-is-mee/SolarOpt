import {calculateScenarios,type Economics} from '../economics'
import type {Electrical} from '../electricalTypes'
import type {Design,Verification} from '../studioTypes'
import {vnd} from '../format'
import {Icon} from './Icon'

const num=(v:number,d=1)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
const range=(a:number,b:number,f:(v:number)=>string)=>Math.abs(a-b)<1e-9?f(a):`${f(Math.min(a,b))} – ${f(Math.max(a,b))}`

/** The few numbers a customer decision rests on, at the top of the handover step; every other card
 * below is the evidence behind them. Money and output are ranges (thận trọng → thuận lợi), not one figure. */
export function HandoverSummary({design,economics,electrical,verification,stale,latitude}:{design:Design;economics:Economics;electrical:Electrical|null;verification:Verification|null;stale:boolean;latitude:number}){
 const m=design.metrics,s=calculateScenarios(economics,m.estimated_cost_vnd,m.annual_energy_kwh,m.peak_power_kwp,{profile:design.month_hour_kwh,latitude})
 const [low,base,high]=s,ready=!base.result.missing.length
 const payback=(v:number|null)=>v==null?`> ${economics.years}`:num(v)
 const failed=verification?.checks.filter(c=>c.status==='FAIL').length??0
 const items:[string,string,string,string][]=[
  ['grid','Hệ thống',`${num(m.peak_power_kwp,2)} kWp`,`${m.panel_count} tấm`],
  ['bolt','Inverter',electrical?`${electrical.inverter_count} × ${num(electrical.inverter.ac_rated_w/1000)} kW`:'Chưa thiết kế điện',electrical?`${electrical.inverter.manufacturer} ${electrical.inverter.model} · DC/AC ${num(electrical.dc_ac_ratio,2)}`:'xem phần Thiết kế điện'],
  ['sun','Điện năm đầu',`${range(low.energy,high.energy,v=>num(v/1000,1))} MWh`,`cơ sở ${num(base.energy,0)} kWh`+(base.result.hourly?` · tự dùng ${num(base.result.hourly.selfPct,0)}%`:'')],
  ['chart','Tổng đầu tư',ready?range(high.result.total,low.result.total,v=>vnd(v)):'Thiếu giá',ready?`cơ sở ${vnd(base.result.total)}`:base.result.missing.slice(0,2).join(', ')],
  ['history','Hoàn vốn',ready?`${payback(high.result.payback)} – ${payback(low.result.payback)} năm`:'—',ready?`cơ sở ${payback(base.result.payback)} năm · IRR ${base.result.irr!=null?num(base.result.irr*100)+'%':'—'}`:''],
  ['shield','Kiểm tra',verification?(failed?`${failed} điều kiện chưa đạt`:'Đạt'):'Chưa chạy',verification?`${verification.checks.filter(c=>c.status==='PASS').length}/${verification.checks.length} đạt`:'bấm Chạy kiểm tra bên dưới'],
 ]
 return <section className="card handover-summary" aria-label="Số liệu chốt">
  <div className="card-heading"><div className="card-title"><span className="card-icon"><Icon name="file" size={18}/></span><div><h3>Số liệu chốt cho khách hàng</h3><p>Khoảng giá trị từ kịch bản thận trọng đến thuận lợi; chi tiết và giả định nằm ở các phần bên dưới.</p></div></div></div>
  {stale&&<p className="tracer-error">Đầu vào đã thay đổi; các số này thuộc phương án cũ.</p>}
  <div className="summary-grid">{items.map(([icon,label,value,note])=><div key={label}><span><Icon name={icon} size={15}/>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
 </section>
}
