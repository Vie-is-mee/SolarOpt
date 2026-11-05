import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
import {loadTs} from './tsload.mjs'
const module=name=>loadTs(name.replace(/\.ts$/,''))
const {defaultEconomics,calculateEconomics,calculateScenarios}=await module('economics.ts')
const {panelCorners}=await module('layoutMeasurements.ts')
function assumptions(){const v=defaultEconomics();v.cost_mode='itemized';for(const k of Object.keys(v))if(v[k]===null)v[k]=0;v.costs=v.costs.map(c=>({...c,amount:0}));v.self_use_pct=100;v.buy_price=1000;v.years=10;v.source='Synthetic arithmetic test, not market prices';return v}
test('unpriced quote lines are unknown, never a complete free installation',()=>{const v=defaultEconomics();v.cost_mode='itemized';const r=calculateEconomics(v,1000000,1000,5);assert.equal(r.missing.length,8)})
test('empty assumptions take the market reference, so a new project has a complete estimate',()=>{const r=calculateEconomics(defaultEconomics(),0,13000,10);assert.deepEqual(r.missing,[]);assert.equal(r.total,12e6*10);assert(r.payback>3&&r.payback<12);assert(r.irr>0&&r.lcoe>0)
 const factory=calculateEconomics({...defaultEconomics(),customer_type:'industrial'},0,130000,100);assert.equal(factory.costPerKwp,8e6)})
test('three scenarios bracket the base case',()=>{const s=calculateScenarios(defaultEconomics(),0,13000,10);assert.deepEqual(s.map(x=>x.id),['low','base','high'])
 const [low,base,high]=s.map(x=>x.result);assert(low.total>base.total&&base.total>high.total);assert(low.npv<base.npv&&base.npv<high.npv);assert(low.payback>base.payback&&base.payback>high.payback)
 assert.equal(s[0].econ.sell_price,0);assert.equal(s[0].energy,13000*.88)})
test('surplus paid only up to half of the output',()=>{const v=assumptions();v.self_use_pct=20;v.sell_price=1000;const r=calculateEconomics(v,0,1000);assert.equal(r.rows[1].exportRevenue,500000)})
test('quote separates installer markup, tax and customer cashflows',()=>{const v=assumptions();v.costs[0].amount=1000000;v.contingency_pct=10;v.markup_pct=20;v.vat_pct=10;const r=calculateEconomics(v,1000000,1000);assert.equal(r.cost,2200000);assert.equal(r.profit,440000);assert.equal(r.total,2904000);assert.equal(r.rows[1].net,1000000);assert.equal(r.payback,2.904);assert.equal(r.netBenefit,7096000)})
test('no double counting exported and self-used energy; degradation and replacement apply',()=>{const v=assumptions();v.self_use_pct=60;v.sell_price=500;v.degradation_pct=10;v.maintenance_year=100000;v.replacement_year=2;v.replacement_cost=300000;const r=calculateEconomics(v,1000000,1000);assert.equal(r.rows[1].saving,600000);assert.equal(r.rows[1].exportRevenue,200000);assert.equal(r.rows[2].energy,900);assert.equal(r.rows[2].net,320000)})
test('zero interest loan principal is repaid, not treated as profit',()=>{const v=assumptions();v.loan_amount=500000;v.loan_years=5;const r=calculateEconomics(v,1000000,1000);assert.equal(r.rows[0].net,-500000);assert.equal(r.annualDebt,100000);assert.equal(r.totalLoanInterest,0);assert.equal(r.netBenefit,9000000)})
test('no benefit has no payback; huge invalid horizon cannot cause an unbounded loop',()=>{const v=assumptions();v.buy_price=0;assert.equal(calculateEconomics(v,1000000,1000).payback,null);v.years=1e12;const r=calculateEconomics(v,1000000,1000);assert.equal(r.rows.length,41);assert(r.missing.includes('Số năm phân tích'))})
test('all-in price per kWp sets the total; item costs, margin and tax are not added on top',()=>{const v=defaultEconomics();for(const k of Object.keys(v))if(v[k]===null)v[k]=0;v.self_use_pct=100;v.buy_price=2000;v.years=10;v.source='Synthetic';v.cost_mode='per_kwp';v.capex_million_per_kwp=12;v.vat_pct=10;v.markup_pct=20
 const r=calculateEconomics(v,99e6,1300e3,1000);assert.deepEqual(r.missing,[]);assert.equal(r.total,12e9);assert.equal(r.tax,0);assert.equal(r.costPerKwp,12e6);assert.equal(r.rows[1].net,2.6e9)
 assert.equal(calculateEconomics({...v,capex_million_per_kwp:null},0,1,10).total,12e6*10)
 assert(calculateEconomics(v,0,1,0).missing.includes('Công suất hệ (kWp)'))
 const itemized=assumptions();itemized.costs[0].amount=4e6;assert.equal(calculateEconomics(itemized,6e6,1000,2).costPerKwp,5e6)})
test('rotated panel corners retain side lengths and opposite-corner midpoint',()=>{const p={x:2,y:3,width_m:1,height_m:2,rotation_deg:37};const c=panelCorners(p);assert(Math.abs(Math.hypot(c[1].x-c[0].x,c[1].y-c[0].y)-1)<1e-12);assert(Math.abs(Math.hypot(c[2].x-c[1].x,c[2].y-c[1].y)-2)<1e-12);assert(Math.abs((c[0].x+c[2].x)/2-2.5)<1e-12);assert(Math.abs((c[0].y+c[2].y)/2-4)<1e-12)})
