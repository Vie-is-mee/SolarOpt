import {calculateEconomics,type Economics} from './economics'
import type {Design} from './studioTypes'

// Items that grow with installed kWp; the rest are treated as fixed per project.
export const SCALABLE_COSTS=new Set(['Bộ biến đổi điện (inverter)','Khung, ray và phụ kiện','Dây điện, bảo vệ và tiếp địa','Nhân công và an toàn thi công'])

// Planning assumptions only (VND, residential 3–30 kWp). Not a quote and not market data:
// they let the advisor run before quotes arrive and are labelled as such in the source note.
const REFERENCE_PER_KWP:Record<string,number>={'Bộ biến đổi điện (inverter)':1_800_000,'Khung, ray và phụ kiện':1_000_000,'Dây điện, bảo vệ và tiếp địa':700_000,'Nhân công và an toàn thi công':1_000_000}
const REFERENCE_FIXED:Record<string,number>={'Khảo sát, đo đạc / drone':1_000_000,'Vận chuyển, hồ sơ và đấu nối':2_000_000,'Thiết kế, phần mềm và quản lý dự án':1_000_000,'Chi phí khác':0}
export const REFERENCE_NOTE='Đơn giá tham khảo SolarOpt (giả định lập kế hoạch, chưa phải báo giá): inverter 1,8 tr/kWp; khung 1,0 tr/kWp; dây, bảo vệ 0,7 tr/kWp; nhân công 1,0 tr/kWp; khảo sát 1 tr; vận chuyển, hồ sơ 2 tr; thiết kế 1 tr. Thay bằng báo giá thực tế trước khi chốt.'

/** Fill only empty cost items, so numbers an engineer already entered are never overwritten. */
export function withReferenceCosts(a:Economics,kwp:number):Economics{
 const costs=a.costs.map(c=>c.amount!==null?c:c.name in REFERENCE_PER_KWP?{...c,amount:Math.round(REFERENCE_PER_KWP[c.name]*kwp)}:c.name in REFERENCE_FIXED?{...c,amount:REFERENCE_FIXED[c.name]}:c)
 const changed=costs.some((c,i)=>c.amount!==a.costs[i].amount)
 return {...a,costs,source:changed&&!a.source.includes(REFERENCE_NOTE)?[a.source.trim(),REFERENCE_NOTE].filter(Boolean).join('\n'):a.source}
}

export type SizePoint={panels:number;kwp:number;energy:number;panelCost:number;total:number;npv:number;payback:number|null;selfUsePct:number;missing:string[]}

/** Economics of keeping the n most productive panels of a design. Cost items were entered for a
 * system of baseKwp (the design on screen): scalable items and the loan scale by kWp against it,
 * fixed items are kept. Passing another option's design compares it on the same unit prices. */
export function evaluateSize(a:Economics,design:Design,n:number,baseKwp=design.metrics.peak_power_kwp):SizePoint{
 const N=design.metrics.panel_count,kwp=N?design.metrics.peak_power_kwp*n/N:0,ratio=baseKwp>0?kwp/baseKwp:0
 const energy=[...design.panels].map(p=>p.annual_energy_kwh).sort((x,y)=>y-x).slice(0,n).reduce((s,v)=>s+v,0)
 const daytime=a.daytime_use_kwh_month
 const selfUsePct=daytime!=null&&daytime>0&&energy>0?Math.min(100,daytime*12/energy*100):a.self_use_pct??0
 const scaled:Economics={...a,self_use_pct:daytime!=null&&daytime>0?selfUsePct:a.self_use_pct,loan_amount:a.loan_amount===null?null:a.loan_amount*ratio,
  costs:a.costs.map(c=>SCALABLE_COSTS.has(c.name)&&c.amount!==null?{...c,amount:c.amount*ratio}:c)}
 const panelCost=N?design.metrics.estimated_cost_vnd*n/N:0,r=calculateEconomics(scaled,panelCost,energy)
 return {panels:n,kwp,energy,panelCost,total:r.total,npv:r.npv,payback:r.payback,selfUsePct,missing:r.missing}
}

export function sizeSweep(a:Economics,design:Design){
 const points=Array.from({length:design.metrics.panel_count},(_,i)=>evaluateSize(a,design,i+1))
 const valid=points.filter(p=>!p.missing.length)
 // Highest NPV; on near-ties (within 0,5%) prefer the smaller system, which risks less capital.
 const top=valid.reduce<SizePoint|null>((b,p)=>!b||p.npv>b.npv?p:b,null)
 const best=top?valid.find(p=>p.npv>=top.npv-Math.abs(top.npv)*.005)!:null
 const fastest=valid.filter(p=>p.payback!==null).reduce<SizePoint|null>((b,p)=>!b||p.payback!<b.payback!?p:b,null)
 return {points,best,fastest}
}
