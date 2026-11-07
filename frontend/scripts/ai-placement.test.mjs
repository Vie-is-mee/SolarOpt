import {test} from 'node:test'
import assert from 'node:assert/strict'
import {loadTs} from './tsload.mjs'
const {draftsFromVision,mergeReading,reviewQueue,reviewReasons,touchedPatch,withKind}=await loadTs('aiPlacement')

const box=(o={})=>({id:'o1',label:'Bồn nước',kind:'tank',scope:'roof',x_pct:50,y_pct:20,width_pct:10,depth_pct:10,height_m:null,confidence:.9,observation:'',requires_placement:false,...o})
const draft=(o={})=>draftsFromVision([box(o)],12,10,'gemini','t')[0]

test('an AI box becomes an unconfirmed library object at its place in metres',()=>{
 const d=draft()
 assert.deepEqual([d.x,d.y,d.width_m,d.depth_m],[6,2,1.2,1]);assert.equal(d.kind,'tank');assert.equal(d.confirmed,false);assert.equal(d.ai_ref,'o1');assert.equal(d.shape,'ellipse')})
test('a height nobody read comes from the library and is marked assumed; one the AI read is not',()=>{
 const d=draft();assert.equal(d.height_m,1.6);assert.equal(d.height_assumed,true)
 const read=draft({height_m:2});assert.equal(read.height_m,2);assert.equal(read.height_assumed,false)})
test('an unknown object stays a plain block with its own label, never the wrong model',()=>{
 const d=draft({kind:'other',label:'Khối lạ'});assert.equal(d.kind,null);assert.equal(d.shape,'rect');assert.equal(d.height_m,1);assert.equal(d.height_assumed,true)})
test('a tree goes around the roof and keeps its position outside the frame',()=>{
 const d=draft({kind:'tree_round',scope:'around',x_pct:-30});assert.equal(d.scope,'neighbor');assert.equal(d.x,-3.6);assert.equal(d.height_m,7)})
test('without a position an object takes the library size, a temporary spot and says so',()=>{
 const d=draft({requires_placement:true});assert.deepEqual([d.width_m,d.depth_m],[1.2,1.2]);assert.equal(d.position_assumed,true);assert.match(d.label,/vị trí tạm/)})
test('a long box is not forced into a round tank',()=>{assert.equal(draft({width_pct:40,depth_pct:10}).shape,'rect')})

const manual={id:'m',label:'Bồn tự vẽ',x:6,y:2,width_m:1.2,depth_m:1,height_m:2,scope:'roof',source:'manual',confidence:1,confirmed:false}
test('a new reading keeps the engineer work and replaces only untouched drafts',()=>{
 const old=draft({id:'old'}),edited={...draft({id:'e',x_pct:0,y_pct:0}),ai_edited:true},ok={...draft({id:'c',x_pct:80,y_pct:80}),confirmed:true}
 const fresh=[draft({id:'n',x_pct:30,y_pct:50})],r=mergeReading([old,edited,ok,manual],fresh)
 assert.deepEqual(r.objects.map(o=>o.ai_ref??o.id),['e','c','m','n']);assert.equal(r.added,1)})
test('a draft where the engineer already has an object is skipped',()=>{
 const r=mergeReading([manual],[draft()]);assert.equal(r.objects.length,1);assert.equal(r.skipped,1)})

test('review starts with what has no position, then the most doubtful and tallest',()=>{
 const placed={...draft({id:'a'}),id:'a',height_assumed:false,height_m:1},tall={...draft({id:'b'}),id:'b',height_m:3},free={...draft({id:'c',requires_placement:true}),id:'c',height_m:.5},done={...tall,id:'d',confirmed:true}
 assert.deepEqual(reviewQueue([placed,tall,free,done,manual]).map(o=>o.id),['c','b','a'])})
test('a pasted copy with an assumed height still waits for review',()=>{
 assert.deepEqual(reviewQueue([{...draft(),ai_ref:null,id:'p'}]).map(o=>o.id),['p'])})
test('reasons name what is doubtful and never a percentage',()=>{
 const why=reviewReasons({...draft({kind:'other',confidence:.4})});assert.ok(why.length>=3);assert.ok(why.every(w=>!/%/.test(w)))
 assert.deepEqual(reviewReasons({...draft(),height_assumed:false}),[])})
test('editing an AI object makes it the engineer work and clears what was typed',()=>{
 const d=draft({requires_placement:true})
 assert.deepEqual(touchedPatch(d,{height_m:2}),{ai_edited:true,height_assumed:false})
 const moved=touchedPatch(d,{x:1,y:1});assert.equal(moved.position_assumed,false);assert.equal(moved.label,'Bồn nước')
 assert.deepEqual(touchedPatch(d,{confirmed:true}),{});assert.deepEqual(touchedPatch(manual,{height_m:3}),{})})
test('changing the type brings its shape and, if assumed, its height',()=>{
 assert.deepEqual(withKind(draft(),'ac'),{kind:'ac',shape:'rect',height_m:.7,height_assumed:true})
 const measured=withKind({...draft(),height_assumed:false},'ac');assert.equal('height_m'in measured,false)
 assert.deepEqual(withKind(draft(),''),{kind:null})})
