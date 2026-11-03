import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const source=readFileSync(new URL('../src/advisorTypes.ts',import.meta.url),'utf8')
const {describeFact,emptyCustomer}=await import('data:text/javascript;base64,'+Buffer.from(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText).toString('base64'))

test('citation chips name the scenario and format the computed value',()=>{
 assert.deepEqual(describeFact('S2.payback_years',7.84),{label:'S2 · Hoàn vốn',value:'7,84 năm'})
 assert.deepEqual(describeFact('S1.investment_vnd',31_237_000),{label:'S1 · Vốn đầu tư',value:'31 triệu đ'})
 assert.deepEqual(describeFact('previous.panel_count',4),{label:'Bản trước · Số tấm',value:'4 tấm'})
 assert.equal(describeFact('consumption.annual_kwh',null).value,'—')
})

test('a new customer starts with unknowns, not zeros',()=>{
 const c=emptyCustomer()
 assert.equal(c.monthly_bill_vnd,null);assert.equal(c.budget_vnd,null);assert.equal(c.tariff,'residential')
})
