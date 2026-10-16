import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const source=readFileSync(new URL('../src/panelLabels.ts',import.meta.url),'utf8')
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText
const {panelBadges}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'))
const panels=Array.from({length:250},(_,i)=>({id:'p'+i,x:(i%25)*1.3,y:Math.floor(i/25)*2.4,width_m:1.134,height_m:2.278}))
test('dense overview retains only the selected identifier, including three-digit indices',()=>{
 const labels=panelBadges(panels,'p249',9,x=>100+x*9,y=>550-y*9,.8)
 assert.equal(labels.length,1);assert.equal(labels[0].id,'p249');assert.equal(labels[0].index,249)
})
test('zoom reveals fitting identifiers without any overlapping badges',()=>{
 const labels=panelBadges(panels.slice(0,20),'p5',60,x=>50+x*60,y=>400-y*60,1)
 assert(labels.length>1);assert.equal(labels[0].id,'p5')
 for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++){
  const a=labels[i],b=labels[j]
  assert(Math.abs(a.x-b.x)>=(a.width+b.width)/2+4||Math.abs(a.y-b.y)>=(a.height+b.height)/2+4)
 }
})
test('small viewport still gives active badge priority and bounded coordinates',()=>{
 const labels=panelBadges(panels,'p0',9,()=>0,()=>0,.3)
 assert.equal(labels[0].id,'p0');assert(labels[0].x-labels[0].width/2>=8);assert(labels[0].y-labels[0].height/2>=8)
})
