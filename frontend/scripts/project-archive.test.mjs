import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const source=readFileSync(new URL('../src/projectArchive.ts',import.meta.url),'utf8')
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText
const {parseArchive,inputFingerprint}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'))
const base={format:'solaropt-project-v2',config:{roof_width_m:12},panel:{},obstacles:[]}
test('old project files remain readable without pretending they contain images',()=>{
 assert.equal(parseArchive(JSON.stringify(base)).evidence,undefined)
})
test('new archive preserves source and calibration payload',()=>{
 const value={...base,format:'solaropt-project-v3',evidence:{source_image:'data:image/png;base64,YWJj',calibration:{reference_m:6}}}
 assert.deepEqual(parseArchive(JSON.stringify(value)),value)
 // Raster bytes and calibration schema are also checked by the backend before import.
})
test('remote, SVG and oversized embedded images cannot enter archive viewer',()=>{
 for(const image of ['https://example.com/a.jpg','data:image/svg+xml;base64,YWJj','data:image/png;base64,'+'a'.repeat(4_000_001)])assert.throws(()=>parseArchive(JSON.stringify({...base,evidence:{source_image:image}})))
})
test('fingerprint identifies same inputs across JSON key orders and rejects different roofs',()=>{
 assert.equal(inputFingerprint({config:{a:1,b:2},panels:[]}),inputFingerprint({panels:[],config:{b:2,a:1}}))
 assert.notEqual(inputFingerprint({width:12}),inputFingerprint({width:13}))
})
test('invalid format and objective are rejected before changing project',()=>{
 assert.throws(()=>parseArchive(JSON.stringify({...base,format:'unknown'})))
 assert.throws(()=>parseArchive(JSON.stringify({...base,objective:'unknown'})))
})
