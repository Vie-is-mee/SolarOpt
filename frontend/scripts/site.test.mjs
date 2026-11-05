import {test} from 'node:test'
import assert from 'node:assert/strict'
import {loadTs} from './tsload.mjs'
const {defaultEconomics,calculateEconomics,calculateScenarios}=await loadTs('economics')
const {datasheetOf,warrantedEnd,panelFigures}=await loadTs('siteSurvey')
const {BUILTIN_PANELS}=await loadTs('panelLibrary')

test('not selling surplus removes export revenue and nothing else',()=>{
 const base={...defaultEconomics(),self_use_pct:40}
 const sell=calculateEconomics(base,0,15000,10)
 const keep=calculateEconomics({...base,sell_surplus:false},0,15000,10)
 assert(sell.rows[1].exportRevenue>0)
 assert.equal(keep.rows[1].exportRevenue,0)
 assert.equal(keep.rows[1].saving,sell.rows[1].saving)
 assert.equal(keep.total,sell.total)
 assert(keep.payback>sell.payback)
 // Every scenario honours the choice, including the optimistic one that raises the surplus price.
 for(const s of calculateScenarios({...base,sell_surplus:false},0,15000,10))assert.equal(s.result.rows[1].exportRevenue,0)
})

test('panel datasheets give mass, uplift rating and the warranted power at year 25',()=>{
 const longi=datasheetOf(BUILTIN_PANELS[0])
 assert.equal(longi.mass_kg,27.5)
 assert.equal(Math.round(warrantedEnd(longi)*10)/10,88.9)
 for(const p of BUILTIN_PANELS)assert(datasheetOf(p),p.model)
 assert.equal(datasheetOf({...BUILTIN_PANELS[0],model:'Khác'}),null)
})

test('the site review receives the panel figures from the datasheet, or nothing for unknown panels',()=>{
 assert.deepEqual(panelFigures(BUILTIN_PANELS[0]),{panel_mass_kg:27.5,panel_rear_load_pa:2400})
 assert.deepEqual(panelFigures({...BUILTIN_PANELS[0],model:'Khác'}),{panel_mass_kg:null,panel_rear_load_pa:null})
})
