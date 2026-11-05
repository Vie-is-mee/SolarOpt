import {consumptionOf,scaleProfile,selfConsumption,type LoadProfileId,type SelfConsumption} from './loadProfiles'
import type {Voltage} from './tariff'
export type CostItem={name:string;amount:number|null}
export type CustomerType='residential'|'business'|'industrial'
/** Changes from the base case to the pessimistic ('low') or optimistic ('high') case. */
export type Spread={capex_pct:number;yield_pct:number;self_use_pts:number;load_pct?:number;buy_price_pct:number;price_growth_pts:number;degradation_pts:number;sell_price_pct:number;om_pct:number;discount_pts:number}
export type Economics={costs:CostItem[];contingency_pct:number|null;markup_pct:number|null;vat_pct:number|null;self_use_pct:number|null;buy_price:number|null;sell_price:number|null;maintenance_year:number|null;degradation_pct:number|null;price_growth_pct:number|null;discount_pct:number|null;years:number;replacement_year:number;replacement_cost:number|null;loan_amount:number|null;loan_rate_pct:number|null;loan_years:number;source:string;daytime_use_kwh_month?:number|null;cost_mode?:CostMode;capex_million_per_kwp?:number|null;customer_type?:CustomerType|null;spread_low?:Spread|null;spread_high?:Spread|null;
 // Consumption for the hour-by-hour self-use: average monthly kWh, or the monthly bill it is derived from.
 monthly_use_kwh?:number|null;monthly_bill_vnd?:number|null;load_profile?:LoadProfileId|null;voltage?:Voltage|null}
/** The layout's typical-day output (288 month-hour values, kWh) and the site latitude for the load seasons. */
export type Site={profile?:number[]|null;latitude:number}
// 'per_kwp': one all-in installed price (EPC, tax included) in million VND per kWp, for estimates before itemised quotes.
export type CostMode='itemized'|'per_kwp'

/* ---- Market reference (Việt Nam, 11/2026) -------------------------------------------------------
 * An empty field means "use the reference": the engineer only types what they actually know.
 * Sources: EVN tariff (QĐ 2892/QĐ-BCT from 01/11/2026; peak 17:30–22:30 per QĐ 963/QĐ-BCT); rooftop surplus sale ≤ 50 % of output at the previous
 * year's average market price (NĐ 58/2025/NĐ-CP, amended by NĐ 243/2026/NĐ-CP); press quotes 2026:
 * households about 12–15 million VND/kWp all-in, businesses about 7.5–13. Planning values, not quotes. */
export const CUSTOMER:Record<CustomerType,{label:string;buy:number;self:number;note:string}>={
 residential:{label:'Hộ gia đình',buy:3450,self:50,note:'giá bậc 3–4 sinh hoạt (2.894–3.456 đ, QĐ 2892) + VAT 8%: điện mặt trời thay phần đắt nhất của hóa đơn'},
 business:{label:'Kinh doanh, văn phòng',buy:3340,self:80,note:'giá kinh doanh hạ áp giờ bình thường 3.089 đ + VAT 8%; giờ cao điểm nay là buổi tối (17h30–22h30) nên điện mặt trời chủ yếu thay giờ bình thường'},
 industrial:{label:'Sản xuất',buy:2120,self:90,note:'giá sản xuất hạ áp giờ bình thường 1.966 đ + VAT 8%; giờ cao điểm nay là buổi tối'},
}
/** All-in EPC price (million VND per kWp, tax included); small systems carry more fixed cost per kWp. */
export function marketCapex(type:CustomerType,kwp:number){
 if(type==='residential')return kwp<=5?13.5:kwp<=15?12:11
 if(type==='business')return kwp<=50?10:kwp<=200?8.5:7.5
 return kwp<=200?8:7
}
/** Share of yearly output that may be sold to the grid (NĐ 243/2026 amending NĐ 58/2025). */
export const EXPORT_CAP=.5
export const SURPLUS_PRICE=670
export const MARKET_NOTE='Giá trị tham khảo SolarOpt (thị trường Việt Nam 11/2026, chưa phải báo giá): suất đầu tư trọn gói theo quy mô; giá điện EVN QĐ 2892/QĐ-BCT (cao điểm 17h30–22h30); bán điện dư tối đa 50% sản lượng theo giá thị trường bình quân năm trước (NĐ 58/2025, sửa bởi NĐ 243/2026) — kiểm tra giá công bố trước khi ký; bảo trì 150.000 đ/kWp/năm; thay inverter năm 12 khoảng 1,5 triệu đ/kWp. Thay bằng số liệu thật khi có.'
export function marketDefaults(type:CustomerType,kwp:number):Partial<Economics>{
 const k=Math.max(0,kwp)
 return {capex_million_per_kwp:marketCapex(type,k),contingency_pct:3,markup_pct:15,vat_pct:8,self_use_pct:CUSTOMER[type].self,buy_price:CUSTOMER[type].buy,sell_price:SURPLUS_PRICE,maintenance_year:Math.round(150_000*k),degradation_pct:.55,price_growth_pct:3,discount_pct:8,replacement_cost:Math.round(1_500_000*k),loan_amount:0,loan_rate_pct:0}
}
export const AUTO_KEYS=['capex_million_per_kwp','contingency_pct','markup_pct','vat_pct','self_use_pct','buy_price','sell_price','maintenance_year','degradation_pct','price_growth_pct','discount_pct','replacement_cost','loan_amount','loan_rate_pct'] as const
/** Empty fields take the market reference for this customer type and size; returns which ones did. */
export function resolveEconomics(a:Economics,kwp:number){
 const type=a.customer_type??'residential',d=marketDefaults(type,kwp),value:Economics={...a,customer_type:type},auto:(keyof Economics)[]=[]
 for(const k of AUTO_KEYS){if(value[k]==null){(value as Record<string,unknown>)[k]=d[k];auto.push(k)}}
 if(!value.source.trim())value.source=MARKET_NOTE
 return {value,auto}
}

export const DEFAULT_SPREAD:{low:Spread;high:Spread}={
 // Thận trọng: dearer build, a cloudier or dirtier year, less self-use, no surplus payment, flat tariff.
 // With an hourly load, self-use follows from the load (load_pct) instead of a fixed change in points.
 low:{capex_pct:15,yield_pct:-12,self_use_pts:-15,load_pct:-15,buy_price_pct:-5,price_growth_pts:-3,degradation_pts:.25,sell_price_pct:-100,om_pct:50,discount_pts:2},
 // Thuận lợi: competitive quote, good year, more daytime use, tariff rising faster.
 high:{capex_pct:-10,yield_pct:5,self_use_pts:10,load_pct:10,buy_price_pct:5,price_growth_pts:2,degradation_pts:-.15,sell_price_pct:50,om_pct:-30,discount_pts:-2},
}
export const SPREAD_FIELDS:[keyof Spread,string,string][]=[['capex_pct','Vốn đầu tư','%'],['yield_pct','Sản lượng','%'],['self_use_pts','Tỷ lệ tự dùng (khi chưa có điện tiêu thụ)','điểm %'],['load_pct','Điện tiêu thụ (khi tính theo giờ)','%'],['buy_price_pct','Giá điện tránh mua','%'],['price_growth_pts','Tăng giá điện/năm','điểm %'],['degradation_pts','Suy giảm/năm','điểm %'],['sell_price_pct','Giá bán điện dư','%'],['om_pct','Bảo trì','%'],['discount_pts','Chiết khấu','điểm %']]

export const defaultEconomics=():Economics=>({costs:['Bộ biến đổi điện (inverter)','Khung, ray và phụ kiện','Dây điện, bảo vệ và tiếp địa','Nhân công và an toàn thi công','Khảo sát, đo đạc / drone','Vận chuyển, hồ sơ và đấu nối','Thiết kế, phần mềm và quản lý dự án','Chi phí khác'].map(name=>({name,amount:null})),contingency_pct:null,markup_pct:null,vat_pct:null,self_use_pct:null,buy_price:null,sell_price:null,maintenance_year:null,degradation_pct:null,price_growth_pct:null,discount_pct:null,years:25,replacement_year:12,replacement_cost:null,loan_amount:null,loan_rate_pct:null,loan_years:5,source:'',cost_mode:'per_kwp',capex_million_per_kwp:null,customer_type:'residential'})
export const economicFields:[keyof Economics,string,string][]=[['contingency_pct','Dự phòng chi phí','%'],['markup_pct','Lãi cộng trên giá vốn đơn vị lắp đặt','%'],['vat_pct','Thuế trên giá bán trước thuế','%'],['self_use_pct','Tỷ lệ điện dùng tại chỗ','%'],['buy_price','Giá điện tránh mua','đ/kWh'],['sell_price','Giá điện dư được thanh toán','đ/kWh'],['maintenance_year','Vệ sinh, bảo trì, bảo hiểm mỗi năm','đ/năm'],['degradation_pct','Suy giảm sản lượng mỗi năm','%'],['price_growth_pct','Tăng giá điện mỗi năm','%'],['discount_pct','Tỷ lệ chiết khấu dòng tiền','%'],['replacement_cost','Chi phí thay thiết bị dự kiến','đ'],['loan_amount','Khoản vay ban đầu','đ'],['loan_rate_pct','Lãi vay mỗi năm','%']]
// Quote build-up fields that an all-in price per kWp already contains.
const QUOTE_KEYS=new Set<keyof Economics>(['contingency_pct','markup_pct','vat_pct'])
export const CAPEX_LABEL='Suất đầu tư trọn gói'
export function economicsErrors(a:Economics){
 const errors:string[]=[],perKwp=a.cost_mode==='per_kwp'
 if(perKwp){const v=a.capex_million_per_kwp;if(v==null||!Number.isFinite(v)||v<=0||v>200)errors.push(CAPEX_LABEL)}
 else for(const item of a.costs)if(item.amount===null||!Number.isFinite(item.amount)||item.amount<0||item.amount>1e12)errors.push(item.name)
 for(const [key,label] of economicFields){if(perKwp&&QUOTE_KEYS.has(key))continue;const v=a[key];if(typeof v!=='number'||!Number.isFinite(v)||v<0||v>1e12||(String(key).endsWith('_pct')&&v>(key==='markup_pct'?500:100)))errors.push(label)}
 if(!Number.isInteger(a.years)||a.years<1||a.years>40)errors.push('Số năm phân tích')
 if(!Number.isInteger(a.replacement_year)||a.replacement_year<1||a.replacement_year>40)errors.push('Năm thay thiết bị')
 if(!Number.isInteger(a.loan_years)||a.loan_years<1||a.loan_years>40)errors.push('Kỳ hạn vay')
 if((a.loan_amount??0)>0&&a.loan_years>a.years)errors.push('Kỳ hạn vay phải nằm trong kỳ phân tích')
 if(!a.source.trim())errors.push('Nguồn báo giá và phạm vi chi phí')
 return errors
}
/** Hour-by-hour self-use for this economics, or null when the output profile or the consumption is unknown. */
export function hourlyFor(a:Economics,annualEnergy:number,site?:Site|null):SelfConsumption|null{
 const c=site?consumptionOf(a,site.latitude):null
 if(!c||!site?.profile||site.profile.length!==288||!(annualEnergy>0))return null
 return selfConsumption(scaleProfile(site.profile,annualEnergy),c)
}
/** Fill self-use and the avoided price from the hourly model when the engineer left them empty, then the market
 * reference for everything else. Typed values always win. Without an hourly model a known daytime demand
 * (older projects) still caps self-use. */
export function prepareEconomics(input:Economics,annualEnergy:number,kwp:number,site?:Site|null){
 const hourly=hourlyFor(input,annualEnergy,site),fromHourly:(keyof Economics)[]=[]
 let a=input
 if(hourly){
  if(a.self_use_pct==null){a={...a,self_use_pct:Math.round(hourly.selfPct*100)/100};fromHourly.push('self_use_pct')}
  if(a.buy_price==null&&hourly.buyPrice>0){a={...a,buy_price:Math.round(hourly.buyPrice)};fromHourly.push('buy_price')}
 }else{
  const daytime=input.daytime_use_kwh_month
  if(input.self_use_pct==null&&daytime!=null&&daytime>0&&annualEnergy>0){a={...a,self_use_pct:Math.min(100,daytime*12/annualEnergy*100)};fromHourly.push('self_use_pct')}
 }
 const r=resolveEconomics(a,kwp)
 return {value:r.value,auto:r.auto,fromHourly,hourly}
}
/** kwp is the installed peak power: it prices the per-kWp mode and gives the all-in cost per kWp in both modes.
 * Empty assumptions take the market reference (resolveEconomics); only unpriced itemised quote lines stay missing. */
export function calculateEconomics(input:Economics,panelCost:number,annualEnergy:number,kwp=0,site?:Site|null){
 const {value:a,hourly}=prepareEconomics(input,annualEnergy,kwp,site)
 const missing=economicsErrors(a),n=(v:number|null|undefined)=>v!=null&&Number.isFinite(v)?Math.min(1e12,Math.max(0,v)):0
 const years=Math.min(40,Math.max(1,Math.trunc(a.years)||1)),loanYears=Math.min(40,Math.max(1,Math.trunc(a.loan_years)||1))
 const perKwp=a.cost_mode==='per_kwp'
 if(perKwp&&!(kwp>0))missing.push('Công suất hệ (kWp)')
 // An all-in price already holds equipment, labour, margin and tax: nothing is built up on top of it.
 const direct=perKwp?n(a.capex_million_per_kwp)*1e6*Math.max(0,kwp):panelCost+a.costs.reduce((s,c)=>s+n(c.amount),0)
 const contingency=perKwp?0:direct*n(a.contingency_pct)/100,cost=direct+contingency
 const profit=perKwp?0:cost*n(a.markup_pct)/100,preTax=cost+profit,tax=perKwp?0:preTax*n(a.vat_pct)/100,total=preTax+tax
 if(n(a.loan_amount)>total)missing.push('Khoản vay vượt tổng đầu tư')
 const loan=n(a.loan_amount),rate=n(a.loan_rate_pct)/100
 const debt=rate?loan*rate/(1-(1+rate)**-loanYears):loan/loanYears
 const rows=[{year:0,energy:0,selfUse:0,exportEnergy:0,saving:0,exportRevenue:0,maintenance:0,replacement:0,debt:0,net:-total+loan,cumulative:-total+loan,discounted:-total+loan}]
 let cumulative=-total+loan,npv=cumulative,payback:number|null=null
 for(let year=1;year<=years;year++){
  const energy=annualEnergy*(1-n(a.degradation_pct)/100)**(year-1),selfUse=energy*n(a.self_use_pct)/100,exportEnergy=energy-selfUse
  // Only part of the output may be sold; the rest of any surplus is curtailed or given away unpaid.
  const paidExport=Math.min(exportEnergy,energy*EXPORT_CAP)
  const growth=(1+n(a.price_growth_pct)/100)**(year-1),saving=selfUse*n(a.buy_price)*growth,exportRevenue=paidExport*n(a.sell_price)*growth
  const maintenance=n(a.maintenance_year),replacement=year===a.replacement_year?n(a.replacement_cost):0,payment=year<=loanYears?debt:0
  const net=saving+exportRevenue-maintenance-replacement-payment,previous=cumulative;cumulative+=net
  if(total>loan&&payback===null&&cumulative>=0&&net>0)payback=year-1+Math.max(0,-previous)/net
  const discounted=net/(1+n(a.discount_pct)/100)**year;npv+=discounted
  rows.push({year,energy,selfUse,exportEnergy,saving,exportRevenue,maintenance,replacement,debt:payment,net,cumulative,discounted})
 }
 // Levelised cost: lifetime cost over lifetime output, both discounted (what each kWh really costs the owner).
 const d=n(a.discount_pct)/100
 const pvEnergy=rows.slice(1).reduce((s,r)=>s+r.energy/(1+d)**r.year,0),pvCost=total+rows.slice(1).reduce((s,r)=>s+(r.maintenance+r.replacement)/(1+d)**r.year,0)
 return {missing,costPerKwp:kwp>0?total/kwp:null,direct,contingency,cost,profit,preTax,tax,total,rows,npv,payback,netBenefit:cumulative,annualDebt:debt,totalLoanInterest:debt*loanYears-loan,irr:irr(rows.map(r=>r.net)),lcoe:pvEnergy>0?pvCost/pvEnergy:null,resolved:a,hourly}
}
/** Internal rate of return of yearly cash flows (year 0 first); null when the flows never change sign. */
export function irr(flows:number[]){
 const npv=(r:number)=>flows.reduce((s,f,i)=>s+f/(1+r)**i,0)
 let lo=-.99,hi=1
 if(npv(lo)*npv(hi)>0)return null
 for(let i=0;i<100;i++){const mid=(lo+hi)/2;if(npv(lo)*npv(mid)<=0)hi=mid;else lo=mid}
 return (lo+hi)/2
}

export type ScenarioId='low'|'base'|'high'
export const SCENARIOS:{id:ScenarioId;name:string;hint:string}[]=[{id:'low',name:'Thận trọng',hint:'chi phí cao, năm nắng kém, ít tự dùng, không bán điện dư'},{id:'base',name:'Cơ sở',hint:'giả định đang nhập hoặc giá trị tham khảo'},{id:'high',name:'Thuận lợi',hint:'báo giá tốt, nắng tốt, dùng điện ban ngày nhiều'}]
/** One scenario's assumptions: the base, moved by the spread. Yield changes the energy, capex the price.
 * With an hourly load, self-use and the avoided price are recomputed from the scenario's output and a load
 * moved by load_pct, so a weaker year correctly uses a larger share of what it makes. */
export function scenarioInputs(input:Economics,kwp:number,id:ScenarioId,annualEnergy=0,site?:Site|null){
 if(id==='base')return {econ:input,yieldFactor:1,capexFactor:1}
 const prep=prepareEconomics(input,annualEnergy,kwp,site),base=prep.value
 const s=(id==='low'?input.spread_low:input.spread_high)??DEFAULT_SPREAD[id],clamp=(v:number,lo:number,hi:number)=>Math.min(hi,Math.max(lo,v))
 const capexFactor=Math.max(.1,1+s.capex_pct/100),om=Math.max(0,1+s.om_pct/100)
 const econ:Economics={...base,
  capex_million_per_kwp:base.capex_million_per_kwp!=null?base.capex_million_per_kwp*capexFactor:null,
  costs:base.costs.map(c=>c.amount==null?c:{...c,amount:c.amount*capexFactor}),
  self_use_pct:clamp((base.self_use_pct??0)+s.self_use_pts,0,100),
  buy_price:Math.max(0,(base.buy_price??0)*(1+s.buy_price_pct/100)),
  price_growth_pct:clamp((base.price_growth_pct??0)+s.price_growth_pts,0,100),
  degradation_pct:clamp((base.degradation_pct??0)+s.degradation_pts,0,100),
  sell_price:Math.max(0,(base.sell_price??0)*(1+s.sell_price_pct/100)),
  maintenance_year:(base.maintenance_year??0)*om,
  replacement_cost:(base.replacement_cost??0)*capexFactor,
  discount_pct:clamp((base.discount_pct??0)+s.discount_pts,0,100)}
 if(prep.hourly){
  const load=Math.max(0,1+(s.load_pct??DEFAULT_SPREAD[id].load_pct??0)/100),c=consumptionOf(input,site!.latitude)!
  econ.monthly_use_kwh=c.monthlyKwh*load;econ.monthly_bill_vnd=null
  if(prep.fromHourly.includes('self_use_pct'))econ.self_use_pct=null
  if(prep.fromHourly.includes('buy_price'))econ.buy_price=null
 }
 return {econ,yieldFactor:Math.max(0,1+s.yield_pct/100),capexFactor}
}
export function calculateScenarios(a:Economics,panelCost:number,annualEnergy:number,kwp:number,site?:Site|null){
 return SCENARIOS.map(sc=>{const {yieldFactor,capexFactor,econ:input}=scenarioInputs(a,kwp,sc.id,annualEnergy,site);const result=calculateEconomics(input,panelCost*capexFactor,annualEnergy*yieldFactor,kwp,site);return {...sc,econ:result.resolved,yieldFactor,energy:annualEnergy*yieldFactor,result}})
}
