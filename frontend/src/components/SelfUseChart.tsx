import {useState} from 'react'
import type {SelfConsumption} from '../loadProfiles'

const MONTHS=['Th1','Th2','Th3','Th4','Th5','Th6','Th7','Th8','Th9','Th10','Th11','Th12']
const num=(v:number,d=0)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})

/** A typical day of one month: roof output against the customer's demand, hour by hour. The overlap is what
 * the customer uses directly; output above the demand is exported, demand above the output is bought. */
export function SelfUseChart({hourly}:{hourly:SelfConsumption}){
 const [month,setMonth]=useState(3)
 const {production,load}=hourly.day(month),W=560,H=200,L=40,R=10,T=12,B=26
 const max=Math.max(...production,...load,.1),x=(h:number)=>L+h*(W-L-R)/24,y=(v:number)=>T+(1-v/max)*(H-T-B),bw=(W-L-R)/24
 const used=production.map((p,h)=>Math.min(p,load[h]))
 const m=hourly.months[month]
 return <figure className="selfuse-chart">
  <div className="segmented month-picker" role="group" aria-label="Chọn tháng">{MONTHS.map((label,i)=><button key={i} type="button" className={i===month?'active':''} aria-pressed={i===month} onClick={()=>setMonth(i)}>{label}</button>)}</div>
  <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Ngày điển hình tháng ${month+1}: sản lượng và nhu cầu theo giờ`}>
   {[0,.5,1].map(t=><g key={t}><line x1={L} x2={W-R} y1={y(max*t)} y2={y(max*t)} className="grid"/><text x={L-5} y={y(max*t)+3} textAnchor="end">{num(max*t,1)}</text></g>)}
   {production.map((p,h)=><rect key={'p'+h} x={x(h)+1} y={y(p)} width={bw-2} height={y(0)-y(p)} className="bar-export"/>)}
   {used.map((u,h)=><rect key={'u'+h} x={x(h)+1} y={y(u)} width={bw-2} height={y(0)-y(u)} className="bar-self"/>)}
   <polyline points={load.map((v,h)=>`${x(h)+bw/2},${y(v)}`).join(' ')} className="load-line"/>
   {[0,6,12,18,24].map(h=><text key={h} x={x(h)} y={H-8} textAnchor="middle">{h}h</text>)}
   <text x={L} y={T-2} className="unit">kWh mỗi giờ</text>
  </svg>
  <figcaption><span className="key self"/>Dùng ngay tại chỗ <span className="key export"/>Dư, phát lên lưới <span className="key load"/>Nhu cầu của khách · Tháng {month+1}: tự dùng {num(m.production>0?m.self/m.production*100:0)}% sản lượng, đáp ứng {num(m.load>0?m.self/m.load*100:0)}% nhu cầu. Ngày nắng, ngày mây được tính riêng nên phần dùng chung thấp hơn so với chỉ nhìn ngày trung bình.</figcaption>
 </figure>
}
