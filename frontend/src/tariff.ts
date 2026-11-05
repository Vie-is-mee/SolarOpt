// EVN retail tariff, mirrors backend app/services/advisor/tariff.py. VND/kWh before VAT.
// Prices: Quyết định 2892/QĐ-BCT (from 01/11/2026). Time bands: Quyết định 963/QĐ-BCT (22/04/2026):
// peak 17:30–22:30 Monday–Saturday, off-peak 0:00–6:00 every day, normal otherwise; Sunday has no peak.
export const TARIFF_SOURCE='Biểu giá EVN theo QĐ 2892/QĐ-BCT (từ 01/11/2026), khung giờ theo QĐ 963/QĐ-BCT; cao điểm 17h30–22h30 thứ Hai–thứ Bảy'
export const VAT_PCT=8
/** [kWh in the tier, price]; the last tier is open-ended. */
export const RESIDENTIAL_TIERS:[number,number][]=[[100,1901],[100,2289],[200,2894],[300,3456],[Infinity,3844]]
export type Voltage='low'|'medium'
export type Band='normal'|'off'|'peak'
/** [normal, off-peak, peak] for low (≤ 1 kV) and medium (1–35 kV) voltage. */
export const TOU:Record<'business'|'industrial',Record<Voltage,[number,number,number]>>={
 business:{low:[3089,1880,5313],medium:[2829,1577,4924]},
 industrial:{low:[1966,1274,3586],medium:[1814,1166,3348]},
}
export function residentialBill(kwh:number,vat=VAT_PCT){
 let left=Math.max(0,kwh),total=0
 for(const [size,price] of RESIDENTIAL_TIERS){const used=Math.min(left,size);total+=used*price;left-=used;if(left<=0)break}
 return total*(1+vat/100)
}
export function residentialKwh(bill:number,vat=VAT_PCT){
 let left=Math.max(0,bill)/(1+vat/100),kwh=0
 for(const [size,price] of RESIDENTIAL_TIERS){const cost=size*price;if(left<=cost)return kwh+left/price;left-=cost;kwh+=size}
 return kwh
}
/** Share of each band in the hour starting at h (0–23). Sunday has no peak hours. */
export function bandShares(h:number,sunday:boolean):Record<Band,number>{
 if(h<6)return {normal:0,off:1,peak:0}
 if(sunday)return {normal:1,off:0,peak:0}
 if(h===17||h===22)return {normal:.5,off:0,peak:.5}
 if(h>=18&&h<=21)return {normal:0,off:0,peak:1}
 return {normal:1,off:0,peak:0}
}
export function hourPrice(prices:[number,number,number],h:number,sunday:boolean){
 const s=bandShares(h,sunday);return s.normal*prices[0]+s.off*prices[1]+s.peak*prices[2]
}
