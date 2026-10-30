export type CostItem={name:string;amount:number|null}
export type Economics={costs:CostItem[];contingency_pct:number|null;markup_pct:number|null;vat_pct:number|null;self_use_pct:number|null;buy_price:number|null;sell_price:number|null;maintenance_year:number|null;degradation_pct:number|null;price_growth_pct:number|null;discount_pct:number|null;years:number;replacement_year:number;replacement_cost:number|null;loan_amount:number|null;loan_rate_pct:number|null;loan_years:number;source:string;daytime_use_kwh_month?:number|null}
export const defaultEconomics=():Economics=>({costs:['Bộ biến đổi điện (inverter)','Khung, ray và phụ kiện','Dây điện, bảo vệ và tiếp địa','Nhân công và an toàn thi công','Khảo sát, đo đạc / drone','Vận chuyển, hồ sơ và đấu nối','Thiết kế, phần mềm và quản lý dự án','Chi phí khác'].map(name=>({name,amount:null})),contingency_pct:null,markup_pct:null,vat_pct:null,self_use_pct:null,buy_price:null,sell_price:null,maintenance_year:null,degradation_pct:null,price_growth_pct:null,discount_pct:null,years:25,replacement_year:12,replacement_cost:null,loan_amount:null,loan_rate_pct:null,loan_years:5,source:''})
export const economicFields:[keyof Economics,string,string][]=[['contingency_pct','Dự phòng chi phí','%'],['markup_pct','Lãi cộng trên giá vốn đơn vị lắp đặt','%'],['vat_pct','Thuế trên giá bán trước thuế','%'],['self_use_pct','Tỷ lệ điện dùng tại chỗ','%'],['buy_price','Giá điện tránh mua','đ/kWh'],['sell_price','Giá điện dư được thanh toán','đ/kWh'],['maintenance_year','Vệ sinh, bảo trì, bảo hiểm mỗi năm','đ/năm'],['degradation_pct','Suy giảm sản lượng mỗi năm','%'],['price_growth_pct','Tăng giá điện mỗi năm','%'],['discount_pct','Tỷ lệ chiết khấu dòng tiền','%'],['replacement_cost','Chi phí thay thiết bị dự kiến','đ'],['loan_amount','Khoản vay ban đầu','đ'],['loan_rate_pct','Lãi vay mỗi năm','%']]
export function economicsErrors(a:Economics){
 const errors:string[]=[]
 for(const item of a.costs)if(item.amount===null||!Number.isFinite(item.amount)||item.amount<0||item.amount>1e12)errors.push(item.name)
 for(const [key,label] of economicFields){const v=a[key];if(typeof v!=='number'||!Number.isFinite(v)||v<0||v>1e12||(String(key).endsWith('_pct')&&v>(key==='markup_pct'?500:100)))errors.push(label)}
 if(!Number.isInteger(a.years)||a.years<1||a.years>40)errors.push('Số năm phân tích')
 if(!Number.isInteger(a.replacement_year)||a.replacement_year<1||a.replacement_year>40)errors.push('Năm thay thiết bị')
 if(!Number.isInteger(a.loan_years)||a.loan_years<1||a.loan_years>40)errors.push('Kỳ hạn vay')
 if((a.loan_amount??0)>0&&a.loan_years>a.years)errors.push('Kỳ hạn vay phải nằm trong kỳ phân tích')
 if(!a.source.trim())errors.push('Nguồn báo giá và phạm vi chi phí')
 return errors
}
export function calculateEconomics(a:Economics,panelCost:number,annualEnergy:number){
 const missing=economicsErrors(a),n=(v:number|null)=>v!==null&&Number.isFinite(v)?Math.min(1e12,Math.max(0,v)):0
 const years=Math.min(40,Math.max(1,Math.trunc(a.years)||1)),loanYears=Math.min(40,Math.max(1,Math.trunc(a.loan_years)||1))
 const direct=panelCost+a.costs.reduce((s,c)=>s+n(c.amount),0)
 const contingency=direct*n(a.contingency_pct)/100,cost=direct+contingency
 const profit=cost*n(a.markup_pct)/100,preTax=cost+profit,tax=preTax*n(a.vat_pct)/100,total=preTax+tax
 if(n(a.loan_amount)>total)missing.push('Khoản vay vượt tổng đầu tư')
 const loan=n(a.loan_amount),rate=n(a.loan_rate_pct)/100
 const debt=rate?loan*rate/(1-(1+rate)**-loanYears):loan/loanYears
 const rows=[{year:0,energy:0,selfUse:0,exportEnergy:0,saving:0,exportRevenue:0,maintenance:0,replacement:0,debt:0,net:-total+loan,cumulative:-total+loan,discounted:-total+loan}]
 let cumulative=-total+loan,npv=cumulative,payback:number|null=null
 for(let year=1;year<=years;year++){
  const energy=annualEnergy*(1-n(a.degradation_pct)/100)**(year-1),selfUse=energy*n(a.self_use_pct)/100,exportEnergy=energy-selfUse
  const growth=(1+n(a.price_growth_pct)/100)**(year-1),saving=selfUse*n(a.buy_price)*growth,exportRevenue=exportEnergy*n(a.sell_price)*growth
  const maintenance=n(a.maintenance_year),replacement=year===a.replacement_year?n(a.replacement_cost):0,payment=year<=loanYears?debt:0
  const net=saving+exportRevenue-maintenance-replacement-payment,previous=cumulative;cumulative+=net
  if(total>loan&&payback===null&&cumulative>=0&&net>0)payback=year-1+Math.max(0,-previous)/net
  const discounted=net/(1+n(a.discount_pct)/100)**year;npv+=discounted
  rows.push({year,energy,selfUse,exportEnergy,saving,exportRevenue,maintenance,replacement,debt:payment,net,cumulative,discounted})
 }
 return {missing,direct,contingency,cost,profit,preTax,tax,total,rows,npv,payback,netBenefit:cumulative,annualDebt:debt,totalLoanInterest:debt*loanYears-loan}
}
