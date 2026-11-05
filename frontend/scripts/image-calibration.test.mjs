import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const source=readFileSync(new URL('../src/imageCalibration.ts',import.meta.url),'utf8')
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText
const {assessCalibration,pixelDistance}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'))

test('uses pixel aspect ratio when measuring a diagonal',()=>{
 assert.equal(pixelDistance([{x:0,y:0},{x:100,y:100}],400,300),500)
})
test('one measured side is enough: the photo gives the other',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:12})
 assert.equal(r.width,12);assert.equal(r.height,6);assert.equal(r.sound,true);assert.equal(r.checked,false)
})
test('the long side scales the long axis even when it runs down the photo',()=>{
 const r=assessCalibration({pixelWidth:400,pixelHeight:800,measuredLong:12})
 assert.equal(r.width,6);assert.equal(r.height,12)
})
test('does not stretch 2:1 imagery into a square measured frame',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:12,measuredShort:12})
 assert.equal(r.width,12);assert.equal(r.height,6);assert.equal(r.valid,false);assert.equal(r.sound,true)
})
test('reference segment remains the scale even when entered frame conflicts',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:20,measuredShort:10,referencePixels:200,referenceMetres:3})
 assert.equal(r.width,12);assert.equal(r.height,6);assert.equal(r.valid,false);assert.equal(r.reference,true)
})
test('accepts a consistent reference and independent frame checks',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:12,measuredShort:6,referencePixels:200,referenceMetres:3})
 assert.equal(r.valid,true);assert.equal(r.mismatch,0)
})
test('eaves-sized mismatch warns softly, a large one warns strongly, neither blocks',()=>{
 const soft=assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:12,measuredShort:6.3})
 assert.equal(soft.valid,false);assert.equal(soft.acceptable,true);assert.equal(soft.sound,true)
 const wrong=assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:12,measuredShort:7})
 assert.equal(wrong.acceptable,false);assert.equal(wrong.sound,true)
})
test('missing or degenerate geometry cannot pass',()=>{
 assert.equal(assessCalibration({pixelWidth:0,pixelHeight:0,measuredLong:12}).sound,false)
 assert.equal(assessCalibration({pixelWidth:800,pixelHeight:400}).sound,false)
 assert.equal(assessCalibration({pixelWidth:800,pixelHeight:400,measuredLong:12,measuredShort:NaN}).sound,false)
})
