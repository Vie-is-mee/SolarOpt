import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const load=name=>'data:text/javascript;base64,'+Buffer.from(ts.transpileModule(readFileSync(new URL(`../src/${name}.ts`,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText).toString('base64')
const {defaultEconomics}=await import(load('economics'))
const {estimateFromBom,ESTIMATE_ITEMS}=await import(load('electricalTypes'))

test('bill of materials maps onto existing estimate lines and leaves panels out',()=>{
 const items=estimateFromBom({cost_by_group:{panel:88_200_000,inverter:30_000_000,dc:4_650_000,ac:2_270_000,earthing:2_402_000,mounting:9_495_000}})
 assert.deepEqual(items,[{name:'Bộ biến đổi điện (inverter)',amount:30_000_000},{name:'Dây điện, bảo vệ và tiếp địa',amount:9_322_000},{name:'Khung, ray và phụ kiện',amount:9_495_000}])
 // Panels are priced separately from the panel spec, never through these lines.
 assert.equal(items.reduce((s,i)=>s+i.amount,0),48_817_000)
})

test('every estimate line the electrical design fills exists in the default estimate',()=>{
 const names=defaultEconomics().costs.map(c=>c.name)
 for(const item of ESTIMATE_ITEMS)assert(names.includes(item.name),item.name)
})
