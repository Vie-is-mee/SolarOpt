import {test} from 'node:test'
import assert from 'node:assert/strict'
import {loadTs} from './tsload.mjs'
const {residentialBill,residentialKwh,bandShares,TOU}=await loadTs('tariff')
const {selfConsumption,kwhFromBill,consumptionOf,nearestProfile,daytimeShare}=await loadTs('loadProfiles')
const {defaultEconomics,calculateEconomics,calculateScenarios}=await loadTs('economics')
const {DAYS}=await loadTs('yieldLosses')

// Typical-day output: a sine from 6:00 to 18:00, stronger in the dry season; about 15 000 kWh a year.
const season=[1,1.15,1.25,1.25,1.05,1.05,.95,.9,.9,.95,.8,.9]
const profile=Array.from({length:288},(_,i)=>{const m=Math.floor(i/24),h=i%24+.5;return h>6&&h<18?season[m]*7.6*Math.sin(Math.PI*(h-6)/12):0})
const annual=profile.reduce((s,v,i)=>s+v*DAYS[Math.floor(i/24)],0)
const site={profile,latitude:10.78}

test('residential bill follows the five tiers of QĐ 2892 and inverts exactly',()=>{
 assert.equal(residentialBill(800,0),100*1901+100*2289+200*2894+300*3456+100*3844)
 for(const kwh of [40,150,350,650,1200])assert(Math.abs(residentialKwh(residentialBill(kwh))-kwh)<1e-6)
})
test('time bands: six off-peak hours, five peak hours Monday to Saturday, none on Sunday',()=>{
 const sum=(sunday,band)=>Array.from({length:24},(_,h)=>bandShares(h,sunday)[band]).reduce((s,v)=>s+v,0)
 assert.equal(sum(false,'off'),6);assert.equal(sum(false,'peak'),5);assert.equal(sum(true,'peak'),0)
 for(let h=0;h<24;h++)for(const sunday of [false,true]){const s=bandShares(h,sunday);assert.equal(s.normal+s.off+s.peak,1)}
 assert.equal(bandShares(12,false).peak,0)          // solar noon is no longer peak time
})
test('self-use never exceeds output or demand, and the rest is exported',()=>{
 for(const monthlyKwh of [50,300,900,5000]){
  const r=selfConsumption(profile,{kind:'residential',profile:'home_day',monthlyKwh,voltage:'low',latitude:10.78})
  assert(r.selfKwh<=r.productionKwh+1e-6&&r.selfKwh<=r.loadKwh+1e-6)
  assert(Math.abs(r.exportKwh-(r.productionKwh-r.selfKwh))<1e-6)
  assert(Math.abs(r.productionKwh-annual)<1e-6)
 }
 const huge=selfConsumption(profile,{kind:'industrial',profile:'continuous',monthlyKwh:1e7,voltage:'low',latitude:10.78})
 assert(huge.selfPct>99.9)
})
test('a household away during the day uses less of its roof than one at home',()=>{
 const c={kind:'residential',monthlyKwh:500,voltage:'low',latitude:10.78}
 const away=selfConsumption(profile,{...c,profile:'away_day'}),home=selfConsumption(profile,{...c,profile:'home_day'})
 assert(away.selfPct<home.selfPct)
 assert(away.selfPct>5&&home.selfPct<80)
})
test('avoided price is the tier the roof removes, or the normal band for a shop',()=>{
 const small=profile.map(v=>v*.05)
 const res=selfConsumption(small,{kind:'residential',profile:'home_day',monthlyKwh:600,voltage:'low',latitude:10.78})
 assert(Math.abs(res.buyPrice-3456*1.08)/(3456*1.08)<.02,'600 kWh/month sits in tier 4')
 const shop=selfConsumption(profile,{kind:'business',profile:'shop',monthlyKwh:3000,voltage:'low',latitude:10.78})
 assert(Math.abs(shop.buyPrice-TOU.business.low[0]*1.08)/(TOU.business.low[0]*1.08)<.03)
})
test('a bill becomes kWh through the tariff the customer is on',()=>{
 assert(Math.abs(kwhFromBill(residentialBill(450),'residential','home_day','low')-450)<1e-6)
 const kwh=kwhFromBill(10_000_000,'business','shop','low')
 assert(kwh>2500&&kwh<3200)
 assert.equal(consumptionOf({customer_type:'industrial',load_profile:'home_day',monthly_use_kwh:1000},10).profile,'factory_1')
 assert.equal(consumptionOf({monthly_use_kwh:null},10),null)
})
test('economics take self-use and avoided price from the hourly model, typed values win',()=>{
 const a={...defaultEconomics(),monthly_use_kwh:600,load_profile:'away_day'}
 const r=calculateEconomics(a,0,annual,10,site)
 assert(r.hourly&&Math.abs(r.resolved.self_use_pct-r.hourly.selfPct)<.01)
 assert.equal(r.resolved.buy_price,Math.round(r.hourly.buyPrice))
 const typed=calculateEconomics({...a,self_use_pct:70,buy_price:3000},0,annual,10,site)
 assert.equal(typed.resolved.self_use_pct,70);assert.equal(typed.resolved.buy_price,3000)
 assert.equal(calculateEconomics(defaultEconomics(),0,annual,10,site).hourly,null)
})
test('scenarios recompute self-use from their own output and load',()=>{
 const a={...defaultEconomics(),monthly_use_kwh:600,load_profile:'home_day'}
 const [low,base,high]=calculateScenarios(a,0,annual,10,site)
 assert(low.result.hourly&&high.result.hourly)
 assert(low.result.payback>base.result.payback&&base.result.payback>high.result.payback)
 assert(Math.abs(low.result.hourly.loadKwh/base.result.hourly.loadKwh-.85)<1e-6)
})
test('golden figures shared with the backend twin (backend/tests/test_selfuse.py)',()=>{
 const golden=[[{kind:'residential',profile:'home_day',monthlyKwh:500},[21496.9881,6001.4795,2978.0801,10037298.9646]],[{kind:'business',profile:'shop',monthlyKwh:3000},[21496.9881,36000,18811.6141,63134813.5348]]]
 for(const [c,[production,load,used,avoided]] of golden){
  const r=selfConsumption(profile,{...c,voltage:'low',latitude:10.78})
  assert(Math.abs(r.productionKwh-production)<1e-3);assert(Math.abs(r.loadKwh-load)<1e-3);assert(Math.abs(r.selfKwh-used)<1e-3);assert(Math.abs(r.avoidedVnd-avoided)<1)
 }
})
test('daytime extra load and profile matching agree with the backend twin',()=>{
 const r=selfConsumption(profile,{kind:'residential',profile:'away_day',monthlyKwh:400,voltage:'low',latitude:10.78,extraDaytimeKwhYear:1800})
 assert(Math.abs(r.loadKwh-6601.1836)<1e-3);assert(Math.abs(r.selfKwh-3614.0059)<1e-3);assert(Math.abs(r.avoidedVnd-12388894.18)<1)
 assert(Math.abs(daytimeShare('home_day')-41.82)<.01);assert.equal(nearestProfile('residential',40),'home_day');assert.equal(nearestProfile('residential',25),'away_day')
})
