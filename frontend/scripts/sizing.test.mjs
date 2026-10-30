import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const load=(name,replace=s=>s)=>'data:text/javascript;base64,'+Buffer.from(replace(ts.transpileModule(readFileSync(new URL(`../src/${name}.ts`,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText)).toString('base64')
const economicsUrl=load('economics')
const {defaultEconomics}=await import(economicsUrl)
const {evaluateSize,sizeSweep,withReferenceCosts,REFERENCE_NOTE}=await import(load('sizing',s=>s.replace("'./economics'",`'${economicsUrl}'`)))

// 20 panels, 580 W, 4,2 tr each; energy falls off so the last panels are the weakest.
const panels=Array.from({length:20},(_,i)=>({id:'p'+i,x:i,y:0,width_m:1.134,height_m:2.278,annual_energy_kwh:900-i*10,shading_loss_pct:0,preserved:false}))
const design={panels,warnings:[],solver_status:'OPTIMAL',metrics:{panel_count:20,peak_power_kwp:11.6,annual_energy_kwh:panels.reduce((s,p)=>s+p.annual_energy_kwh,0),annual_energy_mwh:0,estimated_cost_vnd:84_000_000,average_shading_loss_pct:0,roof_utilization_pct:50,preserved_panel_count:0,layout_preservation_rate_pct:0}}
const complete=()=>({...withReferenceCosts(defaultEconomics(),11.6),contingency_pct:0,markup_pct:0,vat_pct:0,self_use_pct:100,buy_price:2500,sell_price:0,maintenance_year:1_000_000,degradation_pct:.5,price_growth_pct:0,discount_pct:6,replacement_cost:0,loan_amount:0,loan_rate_pct:0})

test('reference costs fill only empty items and label the source as an assumption',()=>{
 const base=defaultEconomics();base.costs[0].amount=5_000_000
 const filled=withReferenceCosts(base,10)
 assert.equal(filled.costs[0].amount,5_000_000)
 assert.equal(filled.costs[1].amount,10_000_000)
 assert(filled.source.includes(REFERENCE_NOTE))
 assert.equal(withReferenceCosts(filled,10).source,filled.source)
})

test('full-size evaluation matches the design totals and keeps the strongest panels first',()=>{
 const a=complete(),full=evaluateSize(a,design,20),half=evaluateSize(a,design,10)
 assert.deepEqual(full.missing,[])
 assert.equal(full.energy,design.metrics.annual_energy_kwh)
 assert.equal(half.energy,panels.slice(0,10).reduce((s,p)=>s+p.annual_energy_kwh,0))
 assert.equal(half.panelCost,42_000_000)
})

test('daytime demand caps self-use, so the advisor stops before exporting unpaid energy',()=>{
 const a={...complete(),daytime_use_kwh_month:600}
 const {best,points}=sizeSweep(a,design)
 assert(best.panels<20,`expected a smaller system, got ${best.panels}`)
 assert(best.energy<=600*12+900,'best size should sit near annual daytime demand')
 assert(points[19].selfUsePct<100)
})

test('missing assumptions are reported instead of producing a suggestion',()=>{
 const {best,points}=sizeSweep(defaultEconomics(),design)
 assert.equal(best,null)
 assert(points[0].missing.length>0)
})

test('another option is costed on the unit prices entered for the design on screen',()=>{
 const a=complete(),half={...design,panels:panels.slice(0,10),metrics:{...design.metrics,panel_count:10,peak_power_kwp:5.8,estimated_cost_vnd:42_000_000,annual_energy_kwh:panels.slice(0,10).reduce((s,p)=>s+p.annual_energy_kwh,0)}}
 const asOption=evaluateSize(a,half,10,design.metrics.peak_power_kwp),asSubset=evaluateSize(a,design,10)
 assert.equal(asOption.total,asSubset.total)
 assert.equal(asOption.energy,asSubset.energy)
})
