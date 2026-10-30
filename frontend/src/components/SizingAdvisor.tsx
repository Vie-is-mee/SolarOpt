import type {Economics} from '../economics'
import type {Design,Objective} from '../studioTypes'
import {evaluateSize,sizeSweep,withReferenceCosts,type SizePoint} from '../sizing'
import {OBJECTIVES} from './DesignOptions'

const money=(n:number)=>n.toLocaleString('vi-VN',{maximumFractionDigits:0})+' đ'
const million=(n:number)=>(n/1e6).toLocaleString('vi-VN',{maximumFractionDigits:1})+' tr'
const years=(p:number|null)=>p===null?'chưa hoàn vốn trong kỳ':p.toLocaleString('vi-VN',{maximumFractionDigits:1})+' năm'

function NpvChart({points,best,current}:{points:SizePoint[];best:SizePoint;current:number}){
 const W=560,H=190,L=56,R=12,T=14,B=30,max=Math.max(...points.map(p=>p.npv),0),min=Math.min(...points.map(p=>p.npv),0),span=max-min||1
 const x=(n:number)=>L+(points.length>1?(n-1)/(points.length-1):.5)*(W-L-R),y=(v:number)=>T+(max-v)/span*(H-T-B)
 const ticks=[max,(max+min)/2,min]
 return <svg className="npv-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`NPV theo số tấm; cao nhất tại ${best.panels} tấm`}>
  {ticks.map((t,i)=><g key={i}><line x1={L} x2={W-R} y1={y(t)} y2={y(t)} className="npv-grid"/><text x={L-6} y={y(t)+3} textAnchor="end">{million(t)}</text></g>)}
  {min<0&&max>0&&<line x1={L} x2={W-R} y1={y(0)} y2={y(0)} className="npv-zero"/>}
  <polyline points={points.map(p=>`${x(p.panels)},${y(p.npv)}`).join(' ')} className="npv-line"/>
  <line x1={x(current)} x2={x(current)} y1={T} y2={H-B} className="npv-current"/>
  <circle cx={x(best.panels)} cy={y(best.npv)} r={5} className="npv-best"/>
  <text x={L} y={H-8}>1 tấm</text><text x={W-R} y={H-8} textAnchor="end">{points.length} tấm ({points[points.length-1].kwp.toLocaleString('vi-VN',{maximumFractionDigits:1})} kWp)</text>
  <text x={Math.min(W-R-4,Math.max(L+4,x(best.panels)))} y={y(best.npv)+20} textAnchor="middle" className="npv-best-label">Gợi ý: {best.panels} tấm</text>
 </svg>
}

export function SizingAdvisor({economics,onEconomics,design,options,panelPrice,budget,onBudget}:{economics:Economics;onEconomics:(v:Economics)=>void;design:Design;options:Partial<Record<Objective,Design>>;panelPrice:number;budget:number;onBudget:(v:number)=>void}){
 const N=design.metrics.panel_count,bound=design.metrics.area_upper_bound_panels
 const full=N?evaluateSize(economics,design,N):null
 const {points,best,fastest}=sizeSweep(economics,design)
 const daytime=economics.daytime_use_kwh_month??null
 const budgetLimited=budget<(N+1)*panelPrice
 const optionRows=OBJECTIVES.flatMap(o=>{const d=options[o.id];if(!d||!d.metrics.panel_count)return [];return [{name:o.name,design:d,point:evaluateSize(economics,d,d.metrics.panel_count,design.metrics.peak_power_kwp)}]}).filter(r=>!r.point.missing.length)
 const bestOption=optionRows.reduce<typeof optionRows[number]|null>((b,r)=>!b||r.point.npv>b.point.npv?r:b,null)
 return <section className="card sizing-advisor">
  <h3>Gợi ý quy mô và ngân sách</h3>
  <p className="muted-note">SolarOpt thử giữ lại 1…{N} tấm cho sản lượng cao nhất của phương án hiện tại, tính dòng tiền cho từng quy mô theo giả định ở bảng dự toán, rồi chọn quy mô có giá trị hiện tại ròng (NPV) cao nhất. Đây là lời khuyên để kỹ sư cân nhắc, không thay báo giá.</p>
  <div className="field-grid">
   <label className="field"><span>Điện dùng ban ngày của khách (kWh/tháng)</span><div className="input-wrap"><input type="number" min={0} aria-label="Điện dùng ban ngày" value={daytime??''} placeholder="Ví dụ 350" onChange={e=>onEconomics({...economics,daytime_use_kwh_month:e.target.value===''?null:Math.max(0,Number(e.target.value))})}/><small>kWh</small></div><em>Lấy từ hóa đơn: phần điện dùng 6h–18h. Khi có số này, tỷ lệ tự dùng được tính theo từng quy mô.</em></label>
   <div className="field sizing-actions"><span>Chưa có báo giá?</span><button type="button" className="button secondary small" onClick={()=>onEconomics(withReferenceCosts(economics,design.metrics.peak_power_kwp))}>Điền đơn giá tham khảo vào ô trống</button><em>Chỉ điền ô chi phí còn trống; ghi chú nguồn là giả định lập kế hoạch.</em></div>
  </div>
  {!N?<p className="muted-note">Chưa có tấm pin trong phương án.</p>:full&&full.missing.length?<p className="tracer-error" role="status">Cần thêm dữ liệu ở bảng dự toán để gợi ý: {full.missing.join('; ')}.</p>:best&&<>
   <div className="sizing-summary">
    <div><span>Quy mô gợi ý</span><strong>{best.panels} tấm · {best.kwp.toLocaleString('vi-VN',{maximumFractionDigits:2})} kWp</strong></div>
    <div><span>Tổng đầu tư ước tính</span><strong>{money(best.total)}</strong></div>
    <div><span>NPV / hoàn vốn</span><strong>{million(best.npv)} · {years(best.payback)}</strong></div>
    <div><span>Ngân sách tấm pin tương ứng</span><strong>{money(best.panelCost)}</strong></div>
   </div>
   <NpvChart points={points.filter(p=>!p.missing.length)} best={best} current={N}/>
   <ul className="sizing-notes">
    {best.panels<N&&<li>Thêm tấm sau mức {best.panels} tấm làm NPV giảm{daytime?': điện tạo thêm vượt nhu cầu ban ngày, phần dư chỉ được trả theo giá điện dư đã nhập.':'.'}</li>}
    {best.panels===N&&(budgetLimited||(bound!=null&&bound>N))&&<li>NPV vẫn tăng tới tấm cuối cùng. {budgetLimited?'Ngân sách tấm pin hiện tại đang giới hạn số tấm; tăng ngân sách rồi tính lại để xem quy mô lớn hơn.':'Mái có thể còn chỗ; thử phương án khác hoặc nới ngưỡng bóng.'}</li>}
    {fastest&&fastest.panels!==best.panels&&<li>Hoàn vốn nhanh nhất ở {fastest.panels} tấm ({years(fastest.payback)}), nhưng tổng lợi ích thấp hơn.</li>}
    {!daytime&&<li>Chưa nhập điện dùng ban ngày nên tỷ lệ tự dùng được giữ cố định ({economics.self_use_pct??0}%) ở mọi quy mô; khi đó NPV thường tăng đều theo số tấm. Nhập nhu cầu để định cỡ sát thực tế hơn.</li>}
    {daytime!=null&&daytime>0&&<li>Tỷ lệ tự dùng ở quy mô gợi ý ≈ {best.selfUsePct.toLocaleString('vi-VN',{maximumFractionDigits:0})}%, tính theo tổng năm; chưa xét lệch giờ, mùa và ngày nghỉ nên có thể lạc quan.</li>}
   </ul>
   <div className="inline-actions"><button type="button" className="button primary small" disabled={Math.abs(budget-best.panelCost)<1} onClick={()=>onBudget(Math.round(best.panelCost))}>Đặt ngân sách tấm pin = {million(best.panelCost)}</button></div>
  </>}
  {optionRows.length>1&&<div className="table-scroll"><table><caption>So sánh các phương án đã tính theo cùng giả định</caption><thead><tr><th>Phương án</th><th>Tấm</th><th>kWp</th><th>Tổng đầu tư</th><th>NPV</th><th>Hoàn vốn</th></tr></thead><tbody>{optionRows.map(r=><tr key={r.name} className={r===bestOption?'recommended':''}><td>{r.name}{r===bestOption&&<strong> · Khuyến nghị</strong>}</td><td>{r.design.metrics.panel_count}</td><td>{r.point.kwp.toLocaleString('vi-VN',{maximumFractionDigits:2})}</td><td>{money(r.point.total)}</td><td>{million(r.point.npv)}</td><td>{years(r.point.payback)}</td></tr>)}</tbody></table></div>}
  <p className="muted-note">Chi phí inverter, khung, dây và nhân công được co giãn theo kWp; khảo sát, hồ sơ, thiết kế và chi phí khác giữ nguyên; khoản vay co giãn theo quy mô. Khi bỏ bớt tấm, SolarOpt giữ những tấm có sản lượng cao nhất, chưa sắp xếp lại vị trí hay đấu chuỗi.</p>
 </section>
}
