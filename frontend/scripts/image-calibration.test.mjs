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
test('does not stretch 2:1 imagery into a square measured frame',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredWidth:12,measuredHeight:12})
 assert.equal(r.width,12);assert.equal(r.height,6);assert.equal(r.valid,false)
})
test('reference segment remains the scale even when entered frame conflicts',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredWidth:20,measuredHeight:10,referencePixels:200,referenceMetres:3})
 assert.equal(r.width,12);assert.equal(r.height,6);assert.equal(r.valid,false);assert.equal(r.reference,true)
})
test('accepts a consistent reference and independent frame checks',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredWidth:12,measuredHeight:6,referencePixels:200,referenceMetres:3})
 assert.equal(r.valid,true);assert.equal(r.mismatch,0)
})
test('small measurement rounding preserves one scale',()=>{
 const r=assessCalibration({pixelWidth:800,pixelHeight:400,measuredWidth:12,measuredHeight:6.1})
 assert.equal(r.height,6);assert.equal(r.valid,true)
})
test('missing or degenerate geometry cannot pass',()=>{
 assert.equal(assessCalibration({pixelWidth:0,pixelHeight:0,measuredWidth:12,measuredHeight:6}).valid,false)
 assert.equal(assessCalibration({pixelWidth:800,pixelHeight:400}).valid,false)
 assert.equal(assessCalibration({pixelWidth:800,pixelHeight:400,measuredWidth:12,measuredHeight:NaN}).valid,false)
})
