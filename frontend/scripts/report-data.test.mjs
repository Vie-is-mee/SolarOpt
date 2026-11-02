import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const source=readFileSync(new URL('../src/reportData.ts',import.meta.url),'utf8')
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText
const {lossBreakdown,shadingHistogram,faceSummary,niceStep,lossColor}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'))
const panel=(kwh,loss,face)=>({id:'p',x:0,y:0,width_m:1,height_m:2,annual_energy_kwh:kwh,shading_loss_pct:loss,preserved:false,face_id:face})

test('loss breakdown walks back from delivered energy to the ideal yield',()=>{
 const r=lossBreakdown([panel(900,10,'a'),panel(800,0,'a')],.8)
 assert.equal(r.delivered,1700);assert.equal(r.shading,100);assert.equal(r.ideal,2250);assert.equal(r.system,450)
 assert.equal(r.ideal-r.system-r.shading,r.delivered)
})
test('histogram puts every panel in exactly one band',()=>{
 const h=shadingHistogram([panel(1,0),panel(1,.99),panel(1,1),panel(1,4.5),panel(1,10),panel(1,40)])
 assert.deepEqual(h.map(b=>b.count),[2,1,1,0,2])
})
test('face summary groups panels by face and averages loss',()=>{
 const [a,b]=faceSummary([panel(500,2,'f1'),panel(400,4,'f1'),panel(300,0,'f2')],580,{f1:'Mái Nam'})
 assert.equal(a.label,'Mái Nam');assert.equal(a.count,2);assert.equal(a.kwh,900);assert.equal(a.loss,3);assert.ok(Math.abs(a.kwp-1.16)<1e-9)
 assert.equal(b.label,'f2')
})
test('axis steps are round numbers',()=>{
 assert.equal(niceStep(1600),500);assert.equal(niceStep(95),25);assert.equal(niceStep(0),1)
})
test('loss colour runs from green to red',()=>{
 assert.equal(lossColor(0),'#236b50');assert.equal(lossColor(25),'#c4402e');assert.equal(lossColor(5),'#e2a526')
})
