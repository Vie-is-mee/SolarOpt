// Mirrors backend/app/services/advisor/models.py.
export type Need='max_energy'|'min_cost'|'robust'
export type Customer={monthly_kwh:number|null;monthly_bill_vnd:number|null;tariff:'residential'|'business';business_price_vnd_kwh:number|null;vat_pct:number;daytime_share_pct:number|null;budget_vnd:number|null;capex_million_per_kwp:number|null;notes:string}
export type ScenarioParams={objective:Need;target_energy_kwh_year:number|null;max_investment_vnd:number|null;edge_reserve_m:number;extra_daytime_kwh_year?:number}
export type Scenario={id:string;label:string;intent:string;params:ScenarioParams;panel_count:number;peak_power_kwp:number;annual_energy_kwh:number;coverage_pct:number|null;self_use_pct:number;average_shading_loss_pct:number;investment_vnd:number;annual_saving_vnd:number;payback_years:number|null;npv_vnd:number;target_met:boolean|null;warnings:string[]}
export type ApplyPlan={objective:Need;budget_vnd:number;target_energy_kwh_year:number|null;layout_edge_reserve_m:number}
export type Proposal={mode:'llm'|'rules';model:string;need:Need;consumption:{annual_kwh:number|null;monthly_kwh:number|null;daytime_share_pct:number;daytime_kwh_year:number|null;source:string};capex_million_per_kwp:number;capex_source:string;scenarios:Scenario[];recommended_id:string;recommended_budget_vnd:number;summary:string;reasons:{text:string;refs:string[]}[];risks:string[];questions:string[];assumptions:string[];facts:Record<string,number|string|null>;apply:ApplyPlan;plans:Record<string,ApplyPlan>;trace:{step:string;detail:string}[];notice:string;elapsed_ms:number;replay?:string}
/** One round of the conversation: the engineer's note that produced it (none for the first). */
export type ProposalRound={proposal:Proposal;feedback:string|null}

export const emptyCustomer=():Customer=>({monthly_kwh:null,monthly_bill_vnd:null,tariff:'residential',business_price_vnd_kwh:null,vat_pct:8,daytime_share_pct:null,budget_vnd:null,capex_million_per_kwp:null,notes:''})

const FACT_LABELS:Record<string,[string,string]>={panel_count:['Số tấm','tấm'],peak_power_kwp:['Công suất','kWp'],annual_energy_kwh:['Sản lượng','kWh/năm'],coverage_pct:['Đáp ứng nhu cầu','%'],self_use_pct:['Tự dùng','%'],average_shading_loss_pct:['Tổn thất bóng','%'],investment_vnd:['Vốn đầu tư','đ'],annual_saving_vnd:['Tiết kiệm năm đầu','đ'],payback_years:['Hoàn vốn','năm'],npv_vnd:['NPV','đ'],
 annual_kwh:['Điện tiêu thụ','kWh/năm'],monthly_kwh:['Điện tiêu thụ','kWh/tháng'],daytime_share_pct:['Dùng ban ngày','%'],daytime_kwh_year:['Điện ban ngày','kWh/năm'],budget_vnd:['Ngân sách','đ'],million_per_kwp:['Suất đầu tư','triệu đ/kWp'],max_kwp_by_area:['Mái chứa tối đa','kWp'],max_panels_by_area:['Mái chứa tối đa','tấm'],usable_area_m2:['Diện tích khả dụng','m²'],roof_area_m2:['Diện tích mái','m²'],tallest_obstacle_m:['Vật cản cao nhất','m'],obstacles:['Vật cản trên mái','']}

/** "S2.payback_years" -> {label:'S2 · Hoàn vốn', value:'7,8 năm'} for the citation chips. */
export function describeFact(key:string,value:number|string|null|undefined){
 const [scope,field]=key.includes('.')?[key.slice(0,key.indexOf('.')),key.slice(key.indexOf('.')+1)]:['',key]
 const [label,unit]=FACT_LABELS[field]||[field,'']
 const prefix=/^S\d+$/.test(scope)?scope+' · ':scope==='previous'?'Bản trước · ':''
 if(value===null||value===undefined)return{label:prefix+label,value:'—'}
 if(typeof value==='string')return{label:prefix+label,value}
 const text=unit==='đ'?(Math.abs(value)>=1e9?(value/1e9).toLocaleString('vi-VN',{maximumFractionDigits:2})+' tỷ đ':Math.round(value/1e6).toLocaleString('vi-VN')+' triệu đ'):value.toLocaleString('vi-VN',{maximumFractionDigits:2})+(unit?' '+unit:'')
 return{label:prefix+label,value:text}
}
