import {Icon} from './Icon'
import type {Design,Objective} from '../studioTypes'

export const OBJECTIVES:{id:Objective;name:string;desc:string;icon:string}[]=[
 {id:'max_energy',name:'Sản lượng cao nhất',desc:'Tìm điện năng sơ bộ cao nhất trong ngân sách và các lưới đã thử.',icon:'bolt'},
 {id:'min_cost',name:'Đáp ứng nhu cầu, giảm chi phí',desc:'Tìm số tấm ít nhất đáp ứng điện năng mục tiêu; xét ngân sách và bóng che.',icon:'layers'},
 {id:'robust',name:'Dự phòng sai số',desc:'Xét mái −2%, tấm +1%, lùi mép +15 cm và ngân sách −15%; kiểm chứng bố trí sau khi chọn.',icon:'shield'},
]

// Candidate IDs belong to search trials, so compare actual panel footprints.
export function layoutSignature(design:Design){
 return JSON.stringify(design.panels.map(p=>[p.x,p.y,p.width_m,p.height_m,((p.rotation_deg||0)%180+180)%180].map(v=>Math.round(v*10000)/10000).join(',')).sort())
}
const fmt=(n:number)=>n.toLocaleString('vi-VN',{maximumFractionDigits:2})
export function DesignOptions({options,objective,ready,busy,onChoose}:{options:Partial<Record<Objective,Design>>;objective:Objective;ready:boolean;busy:boolean;onChoose:(id:Objective)=>void}){
 const results=OBJECTIVES.map(o=>options[o.id])
 const complete=ready&&results.every(Boolean)
 const empty=complete&&results.every(r=>r!.panels.length===0)
 const same=complete&&new Set(results.map(r=>layoutSignature(r!))).size===1
 const sameTotals=complete&&new Set(results.map(r=>JSON.stringify([r!.metrics.panel_count,r!.metrics.annual_energy_kwh,r!.metrics.estimated_cost_vnd]))).size===1
 return <>
  <div className="option-grid">{OBJECTIVES.map(o=>{
   const result=ready?options[o.id]:undefined
   const chosen=result?.layout_trials?.find(t=>t.selected)
   const maximum=result?Math.max(0,...result.panels.map(p=>p.shading_loss_pct)):0
   return <button key={o.id} disabled={busy||!result} aria-pressed={objective===o.id} className={`option-card ${objective===o.id?'selected':''}`} onClick={()=>onChoose(o.id)}>
    <div className="option-heading"><span><Icon name={o.icon} size={19}/></span><strong>{o.name}</strong><i>{objective===o.id&&<Icon name="check" size={12}/>}</i></div>
    <p>{o.desc}</p>
    <div className="option-metrics"><strong>{result?result.metrics.panel_count:'—'}<small>tấm pin</small></strong><strong>{result?fmt(result.metrics.annual_energy_mwh):'—'}<small>MWh/năm sơ bộ</small></strong></div>
    {result&&o.id==='max_energy'&&<div className="goal-status met"><strong>Ưu tiên điện năng sơ bộ</strong><span>Chưa yêu cầu bố trí vượt qua các tình huống sai số.</span></div>}
    {result&&o.id==='min_cost'&&<div className={`goal-status ${result.target_met?'met':'unmet'}`}><strong>{result.target_met?'Đáp ứng mục tiêu':'Chưa đáp ứng mục tiêu'}</strong><span>Mục tiêu: {fmt(result.target_energy_kwh_year||0)} kWh/năm</span>{result.target_met===false&&<span>Còn thiếu {fmt(Math.max(0,(result.target_energy_kwh_year||0)-result.panels.reduce((sum,p)=>sum+p.annual_energy_kwh,0)))} kWh/năm. Kiểm tra ngân sách, vùng mái hoặc điều chỉnh nhu cầu thực.</span>}</div>}
    {result&&o.id==='robust'&&<div className={`goal-status ${result.robustness_checks?.every(c=>c.status==='PASS')&&result.robustness_checks.length?'met':'unmet'}`}><strong>{result.robustness_checks?.filter(c=>c.status==='PASS').length??0}/{result.robustness_checks?.length??0} tình huống đạt không cảnh báo khi tạo</strong><span>Dùng tối đa 85% ngân sách để dự phòng.</span>{result.robustness_checks?.some(c=>c.status!=='PASS')&&<span>Có cảnh báo hoặc tình huống chưa đạt; xem Kiểm tra & bàn giao để xử lý.</span>}</div>}
    {result&&<div className="option-shading"><span>Bóng che trung bình: <strong>{fmt(result.metrics.average_shading_loss_pct)}%</strong></span><span>Tấm chịu bóng nhiều nhất: <strong>{fmt(maximum)}%</strong></span>{chosen&&<span>Góc xếp: {fmt(chosen.angle_deg)}° · Loại do bóng: {chosen.shading_rejected_count??'—'} vị trí trên lưới chọn{o.id==='robust'?` · Loại do sai số hình học: ${chosen.robustness_rejected_count??0}`:''}</span>}</div>}
    <div className="option-bottom"><span>{result?`${fmt(result.metrics.estimated_cost_vnd/1_000_000)} triệu đ`:busy?'Đang tính…':ready?'Chưa tính lựa chọn này':'Cần tính lại'}</span><small>chỉ tấm pin</small></div>
   </button>
  })}</div>
  <div className="option-explanation" role="status">{busy?'Đang tính cả ba mục tiêu trên cùng đầu vào…':!ready?'Nhập điện năng mục tiêu rồi nhấn Tính lại phương án để so sánh.':!complete?'Hiện chỉ có kết quả của mục tiêu đã cập nhật. Nhấn Tính lại phương án để tính đủ ba lựa chọn.':empty?'Cả ba mục tiêu chưa chọn được tấm pin. Kiểm tra ngân sách, vùng mái sử dụng được và các ràng buộc.':same?'Ba mục tiêu cùng chọn một bố trí trong phạm vi đã thử. Kiểm tra trạng thái đáp ứng nhu cầu và kiểm chứng sai số; số tấm giống nhau chưa có nghĩa cả ba đạt mục tiêu.':sameTotals?'Các tổng chỉ số giống nhau nhưng vị trí bố trí khác nhau. Chọn từng thẻ để đối chiếu bản vẽ.':'Chọn thẻ để đối chiếu phần đánh đổi: sản lượng tối đa, chi phí tấm pin để đáp ứng nhu cầu, hoặc dự phòng sai số.'} <span>Nắng năm quy đổi theo 12 ngày trời quang đại diện cho từng mặt mái; bóng dùng 9 thời điểm. Kiểm chứng dự phòng chỉ áp dụng các tình huống đã thử; kỹ sư vẫn cần xác nhận trước khi thi công.</span></div>
 </>
}
