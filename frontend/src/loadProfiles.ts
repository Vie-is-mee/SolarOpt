// Hour-by-hour self-consumption: the layout's typical-day output (12 months × 24 hours, from the backend)
// against a load profile built from the customer's monthly consumption. Planning profiles, not metering:
// they encode when each kind of customer uses power (air conditioning at night for households, office hours
// for shops, shifts for factories), and are replaced by meter data when the engineer has it.
import {DAYS} from './yieldLosses'
import {RESIDENTIAL_TIERS,TOU,VAT_PCT,hourPrice,residentialBill,residentialKwh,type Voltage} from './tariff'

export type CustomerKind='residential'|'business'|'industrial'
export type LoadProfileId='home_day'|'away_day'|'shop'|'factory_1'|'factory_2'|'continuous'
type DayShape={shape:number[];weight:number}
export type LoadProfile={id:LoadProfileId;label:string;hint:string;kinds:CustomerKind[];workday:DayShape;saturday:DayShape;sunday:DayShape;seasonal:boolean}

const home=[3.5,3.2,3,3,3,3.2,4,4.5,4.2,4,4.2,4.6,4.8,4.6,4.4,4.2,4.2,4.6,5.5,6.2,6.4,6,5,4.2]
const away=[4.5,4.2,4,4,4,4.2,5.2,4.6,2.2,1.8,1.8,1.9,2,1.9,1.8,1.8,2,3.5,6,7.2,7.4,7,6,5]
const shop=[1,1,1,1,1,1,1.5,3,7,8.5,9,9.2,8.6,8.8,9,9,8.5,7,3,1.5,1.2,1,1,1]
const shift1=[1.5,1.5,1.5,1.5,1.5,1.5,3,8,8.5,8.5,8.5,6,7.5,8.5,8.5,8.5,6,2.5,1.5,1.5,1.5,1.5,1.5,1.5]
const shift2=[2,2,2,2,2,2,7,8,8,8,8,7,8,8,8,8,8,7.5,7.5,7.5,7.5,7,4,2]
const flat=Array.from({length:24},(_,h)=>h>=6&&h<18?1.1:1)
const standby=Array(24).fill(1)

export const LOAD_PROFILES:LoadProfile[]=[
 {id:'away_day',label:'Hộ đi làm, đi học cả ngày',hint:'ban ngày gần như vắng nhà; điều hòa buổi tối và đêm',kinds:['residential'],workday:{shape:away,weight:.95},saturday:{shape:home,weight:1.12},sunday:{shape:home,weight:1.12},seasonal:true},
 {id:'home_day',label:'Hộ có người ở nhà ban ngày',hint:'nội trợ, người già, làm việc tại nhà',kinds:['residential'],workday:{shape:home,weight:1},saturday:{shape:home,weight:1},sunday:{shape:home,weight:1},seasonal:true},
 {id:'shop',label:'Cửa hàng, văn phòng (8h–18h)',hint:'nghỉ Chủ nhật, máy lạnh giờ làm việc',kinds:['business'],workday:{shape:shop,weight:1},saturday:{shape:shop,weight:.9},sunday:{shape:standby,weight:.25},seasonal:false},
 {id:'factory_1',label:'Xưởng 1 ca (7h–17h, 6 ngày)',hint:'tải nền nhỏ ngoài giờ',kinds:['industrial','business'],workday:{shape:shift1,weight:1},saturday:{shape:shift1,weight:1},sunday:{shape:standby,weight:.2},seasonal:false},
 {id:'factory_2',label:'Xưởng 2 ca (6h–22h, 6 ngày)',hint:'',kinds:['industrial'],workday:{shape:shift2,weight:1},saturday:{shape:shift2,weight:1},sunday:{shape:standby,weight:.25},seasonal:false},
 {id:'continuous',label:'Chạy liên tục 24/7',hint:'kho lạnh, xưởng 3 ca, khách sạn',kinds:['industrial','business'],workday:{shape:flat,weight:1},saturday:{shape:flat,weight:1},sunday:{shape:flat,weight:1},seasonal:false},
]
export const profileById=(id:LoadProfileId|null|undefined)=>LOAD_PROFILES.find(p=>p.id===id)
export const defaultProfile=(kind:CustomerKind):LoadProfileId=>kind==='residential'?'away_day':kind==='business'?'shop':'factory_1'

/** Month factors of household consumption (mean 1): air conditioning peaks in the hot dry months in the
 * south and in summer in the north. Businesses and factories are taken as flat over the year. */
const SOUTH=[.92,.95,1.08,1.15,1.12,1.02,.98,.97,.95,.96,.94,.96]
const NORTH=[.85,.8,.82,.9,1.1,1.25,1.3,1.25,1.1,.95,.85,.83]
export const seasonFactors=(p:LoadProfile,latitude:number)=>p.seasonal?(Math.abs(latitude)>=18?NORTH:SOUTH):Array(12).fill(1)

/** Output varies day to day around the typical day; three kinds of day keep the overlap with the load honest
 * (the overlap of averages always overstates self-use). Mean factor 1, spread about ±27 %. */
export const DAY_KINDS:[number,number][]=[[.5,.2],[1,.4],[1.25,.4]]
// Mon–Fri, Saturday, Sunday as shares of the days of a month.
const DAY_TYPES:[keyof Pick<LoadProfile,'workday'|'saturday'|'sunday'>,number,boolean][]=[['workday',5/7,false],['saturday',1/7,false],['sunday',1/7,true]]

/** extraDaytimeKwhYear: load added evenly from 9:00 to 17:00 every day (EV charging, a heat pump). */
export type Consumption={kind:CustomerKind;profile:LoadProfileId;monthlyKwh:number;voltage:Voltage;latitude:number;extraDaytimeKwhYear?:number}

/** Average monthly kWh from a bill: the stepped tariff for households, the profile's time-band mix otherwise. */
export function kwhFromBill(bill:number,kind:CustomerKind,profile:LoadProfileId,voltage:Voltage){
 if(kind==='residential')return residentialKwh(bill)
 const p=profileById(profile)!,prices=TOU[kind][voltage]
 let energy=0,cost=0
 for(const [type,share,sunday] of DAY_TYPES){const d=p[type],sum=d.shape.reduce((s,v)=>s+v,0);d.shape.forEach((v,h)=>{const e=share*d.weight*v/sum;energy+=e;cost+=e*hourPrice(prices,h,sunday)})}
 return bill/(cost/energy*(1+VAT_PCT/100))
}

/** The consumption an economics entry describes, or null when neither monthly kWh nor a bill is known.
 * A profile that does not fit the customer kind (e.g. a household profile on a factory) falls back to the kind's default. */
export function consumptionOf(a:{customer_type?:CustomerKind|null;load_profile?:LoadProfileId|null;voltage?:Voltage|null;monthly_use_kwh?:number|null;monthly_bill_vnd?:number|null;extra_daytime_kwh_month?:number|null},latitude:number):Consumption|null{
 const kind=a.customer_type??'residential',chosen=profileById(a.load_profile),profile=chosen&&chosen.kinds.includes(kind)?chosen.id:defaultProfile(kind),voltage=kind==='residential'?'low':a.voltage??'low'
 const monthly=a.monthly_use_kwh!=null&&a.monthly_use_kwh>0?a.monthly_use_kwh:a.monthly_bill_vnd!=null&&a.monthly_bill_vnd>0?kwhFromBill(a.monthly_bill_vnd,kind,profile,voltage):null
 return monthly&&Number.isFinite(monthly)&&monthly>0?{kind,profile,monthlyKwh:monthly,voltage,latitude,extraDaytimeKwhYear:Math.max(0,a.extra_daytime_kwh_month??0)*12}:null
}

export type SelfConsumption={productionKwh:number;loadKwh:number;selfKwh:number;exportKwh:number;selfPct:number;coveragePct:number;avoidedVnd:number;buyPrice:number;
 months:{production:number;load:number;self:number}[];day:(month:number)=>{production:number[];load:number[]}}

/** Year-one self-consumption and avoided bill. production: kWh per typical day of each month, 288 values. */
export function selfConsumption(production:number[],c:Consumption):SelfConsumption{
 const p=profileById(c.profile)!,season=seasonFactors(p,c.latitude),mean=DAYS.reduce((s,d)=>s+d,0)/12
 const norm=DAY_TYPES.reduce((s,[t,share])=>s+share*p[t].weight,0)
 const extra=Array.from({length:24},(_,h)=>h>=9&&h<17?(c.extraDaytimeKwhYear??0)/365/8:0)
 const loadOf=(m:number,type:'workday'|'saturday'|'sunday')=>{const daily=c.monthlyKwh*season[m]/mean*p[type].weight/norm,sum=p[type].shape.reduce((s,v)=>s+v,0);return p[type].shape.map((v,h)=>daily*v/sum+extra[h])}
 const prices=c.kind==='residential'?null:TOU[c.kind][c.voltage]
 let selfKwh=0,prodKwh=0,loadKwh=0,avoided=0
 const months=[]
 for(let m=0;m<12;m++){
  const days=DAYS[m],prod=production.slice(m*24,m*24+24)
  let mSelf=0,mLoad=0,mAvoidedTou=0
  for(const [type,share,sunday] of DAY_TYPES){
   const load=loadOf(m,type)
   for(let h=0;h<24;h++){
    const used=DAY_KINDS.reduce((s,[k,pk])=>s+pk*Math.min(k*prod[h],load[h]),0)
    mSelf+=days*share*used;mLoad+=days*share*load[h]
    if(prices)mAvoidedTou+=days*share*used*hourPrice(prices,h,sunday)
   }
  }
  const mProd=prod.reduce((s,v)=>s+v,0)*days
  avoided+=prices?mAvoidedTou*(1+VAT_PCT/100):residentialBill(mLoad)-residentialBill(mLoad-mSelf)
  selfKwh+=mSelf;prodKwh+=mProd;loadKwh+=mLoad
  months.push({production:mProd,load:mLoad,self:mSelf})
 }
 return {productionKwh:prodKwh,loadKwh,selfKwh,exportKwh:Math.max(0,prodKwh-selfKwh),selfPct:prodKwh>0?selfKwh/prodKwh*100:0,coveragePct:loadKwh>0?selfKwh/loadKwh*100:0,
  avoidedVnd:avoided,buyPrice:selfKwh>0?avoided/selfKwh:0,months,
  day:(m:number)=>({production:production.slice(m*24,m*24+24),load:DAY_TYPES.reduce((acc,[t,share])=>{loadOf(m,t).forEach((v,h)=>acc[h]+=share*v);return acc},Array(24).fill(0) as number[])})}
}
const DAYTIME=[7,17]
/** Share of a week's consumption between 7 and 17 o'clock (backend selfuse.daytime_share). */
export function daytimeShare(id:LoadProfileId){
 const p=profileById(id)!;let total=0,day=0
 for(const [t,share] of DAY_TYPES){const {shape,weight}=p[t],s=shape.reduce((a,v)=>a+v,0);total+=share*weight;day+=share*weight*shape.slice(DAYTIME[0],DAYTIME[1]).reduce((a,v)=>a+v,0)/s}
 return day/total*100
}
/** The profile matching a stated daytime share (backend selfuse.nearest_profile). */
export function nearestProfile(kind:CustomerKind,daytimePct:number|null|undefined):LoadProfileId{
 if(kind!=='residential')return kind==='business'?'shop':'factory_1'
 if(daytimePct==null)return 'away_day'
 return (['away_day','home_day'] as LoadProfileId[]).reduce((b,p)=>Math.abs(daytimeShare(p)-daytimePct)<Math.abs(daytimeShare(b)-daytimePct)?p:b)
}
/** Scale a typical-day profile so its year sums to annualEnergy (a scenario or a smaller system). */
export function scaleProfile(profile:number[],annualEnergy:number){
 const total=profile.reduce((s,v,i)=>s+v*DAYS[Math.floor(i/24)],0)
 return total>0?profile.map(v=>v*annualEnergy/total):profile
}
export const TOP_TIER=RESIDENTIAL_TIERS[RESIDENTIAL_TIERS.length-1][1]
