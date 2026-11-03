// Mirrors backend/app/services/assistant.py.
export type AssistantActionKind='go_to_step'|'set_target_energy'|'set_budget'|'set_edge_reserve'|'set_obstacle'|'run_design'|'run_electrical'
export type AssistantAction={kind:AssistantActionKind;label:string;params:Record<string,number|string>}
export type AssistantReply={mode:'llm'|'rules';model:string;reply:string;facts_used:string[];facts:Record<string,number|string|null>;actions:AssistantAction[];unverified:string[];notice:string;elapsed_ms:number;replay?:string}
/** One message on screen; assistant turns keep the full reply for chips and action buttons. */
export type ChatMessage={role:'user'|'assistant';content:string;reply?:AssistantReply;applied?:number[]}

const FACT_LABELS:Record<string,[string,string]>={
 'design.panel_count':['Số tấm','tấm'],'design.peak_power_kwp':['Công suất','kWp'],'design.annual_energy_kwh':['Sản lượng','kWh/năm'],'design.panel_cost_vnd':['Tiền tấm pin','đ'],
 'design.area_upper_bound_panels':['Mái chứa tối đa','tấm'],'design.roof_utilization_pct':['Dùng mặt bằng','%'],'site.roof_area_m2':['Diện tích mái','m²'],'site.usable_area_m2':['Diện tích khả dụng','m²'],
 'site.max_panels_by_area':['Mái chứa tối đa','tấm'],'site.obstacles':['Vật cản trên mái',''],'site.tallest_obstacle_m':['Vật cản cao nhất','m'],'site.setback_m':['Lùi mép bắt buộc','m'],
 'site.edge_reserve_m':['Lùi mép thêm','m'],'site.budget_vnd':['Ngân sách tấm pin','đ'],'site.target_energy_kwh_year':['Điện năng mục tiêu','kWh/năm'],
 'shading.average_loss_pct':['Tổn thất bóng TB','%'],'shading.max_loss_pct':['Tấm bị che nhiều nhất','%'],'shading.worst_panels':['Tấm chịu bóng nhiều',''],'shading.tallest_obstacle_m':['Vật cản cao nhất','m'],
 'electrical.summary':['Thiết kế điện',''],'electrical.inverter':['Inverter',''],'electrical.strings':['Số chuỗi',''],'electrical.dc_ac_ratio':['DC/AC',''],'electrical.warnings':['Lưu ý điện',''],'electrical.bom_vnd':['Vật tư điện','đ'],
 'whatif.panel_count':['Thử: số tấm','tấm'],'whatif.annual_energy_kwh':['Thử: sản lượng','kWh/năm'],
 'economics.total_vnd':['Tổng đầu tư','đ'],'economics.payback_years':['Hoàn vốn','năm'],'economics.npv_vnd':['NPV','đ'],'economics.missing':['Dự toán còn thiếu',''],
}
/** Long text facts (lists, summaries) stay out of the chip row; the reply already says them. */
export function factChip(key:string,value:number|string|null|undefined){
 const [label,unit]=FACT_LABELS[key]||[null,'']
 if(!label)return null
 if(value===null||value===undefined||value==='')return null
 if(typeof value==='string')return value.length>40?null:{label,value}
 const text=unit==='đ'?(Math.abs(value)>=1e9?(value/1e9).toLocaleString('vi-VN',{maximumFractionDigits:2})+' tỷ đ':(value/1e6).toLocaleString('vi-VN',{maximumFractionDigits:1})+' triệu đ'):value.toLocaleString('vi-VN',{maximumFractionDigits:2})+(unit?' '+unit:'')
 return {label,value:text}
}
