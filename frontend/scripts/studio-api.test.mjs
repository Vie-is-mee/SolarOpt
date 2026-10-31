import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const source=readFileSync(new URL('../src/services/studioApi.ts',import.meta.url),'utf8').replace('import.meta.env.VITE_API_BASE',"''")
const ownerSource=readFileSync(new URL('../src/draftOwner.ts',import.meta.url),'utf8')
const ownerCompiled=ts.transpileModule(ownerSource,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText
const ownerUrl='data:text/javascript;base64,'+Buffer.from(ownerCompiled).toString('base64')
const {setDraftOwner}=await import(ownerUrl)
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText.replace("'../draftOwner'",JSON.stringify(ownerUrl))
const {studioApi}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'))

test('requests bind the displayed account identity to shared-cookie API calls',async()=>{
 const before=globalThis.fetch,seen=[]
 try{
  globalThis.fetch=async(path,init)=>{seen.push(init);return new Response('[]',{status:200})}
  setDraftOwner(7)
  await studioApi.history()
  await studioApi.design({},{},[],'robust')
  setDraftOwner(null)
  await studioApi.history()
  assert.deepEqual(seen.map(value=>value.headers['X-SolarOpt-User']),['7','7','guest'])
  assert.ok(seen.every(value=>value.credentials==='include'&&value.headers['X-SolarOpt-Request']==='1'))
 }finally{globalThis.fetch=before;setDraftOwner(null)}
})

test('timeout has an actionable Vietnamese message and user cancellation stays cancellation',async()=>{
 const fetchBefore=globalThis.fetch,timeoutBefore=AbortSignal.timeout
 try{
  AbortSignal.timeout=()=>AbortSignal.abort(new DOMException('signal timed out','TimeoutError'))
  globalThis.fetch=async()=>{throw new DOMException('signal timed out','TimeoutError')}
  await assert.rejects(studioApi.design({},{},[],'robust'),/Máy chủ tính quá thời gian chờ/)
  const cancelled=AbortSignal.abort()
  globalThis.fetch=async()=>{throw cancelled.reason}
  await assert.rejects(studioApi.scene({},[],'2026-10-16',12,cancelled),e=>e.name==='AbortError')
 }finally{globalThis.fetch=fetchBefore;AbortSignal.timeout=timeoutBefore}
})
