import {test} from 'node:test'
import assert from 'node:assert/strict'
import {loadTs} from './tsload.mjs'
const {insertNode,removeNode,setEdgeLength,moveNode,nearestEdge,edgeLength,ringIsSimple,insideRing,pasteObjects}=await loadTs('roofEdit')

const square=[{x:0,y:0},{x:10,y:0},{x:10,y:10},{x:0,y:10}],frame={width:20,height:20}

test('a new node joins the ring on the nearest edge, between its two ends',()=>{
 const r=insertNode(square,{x:5,y:.4})
 assert.ok(r.ok);assert.deepEqual(r.ring[1],{x:5,y:.4});assert.equal(r.ring.length,5);assert.ok(ringIsSimple(r.ring))
 assert.equal(nearestEdge(square,{x:9.8,y:5}),1)})
test('a node on top of another or one that would cross the outline is refused',()=>{
 assert.equal(insertNode(square,{x:10,y:0}).ok,false)
 const notch=[{x:0,y:0},{x:10,y:0},{x:10,y:10},{x:6,y:10},{x:6,y:2},{x:4,y:2},{x:4,y:10},{x:0,y:10}]
 const r=insertNode(notch,{x:8,y:3});if(r.ok)assert.ok(ringIsSimple(r.ring))})
test('deleting a node joins its neighbours and the roof keeps at least 3 nodes',()=>{
 const r=removeNode([...square,{x:-1,y:5}],4)
 assert.ok(r.ok);assert.deepEqual(r.ring,square)
 assert.equal(removeNode(square.slice(0,3),0).ok,false)})
test('deleting a node that makes the outline cross itself is refused',()=>{
 const spike=[{x:0,y:0},{x:10,y:0},{x:10,y:10},{x:0,y:10},{x:0,y:6},{x:8,y:5},{x:0,y:4}]
 assert.equal(ringIsSimple(spike),true)
 assert.equal(removeNode(spike,2).ok,false)})
test('typing an edge length moves the far node along the edge and keeps the selected one',()=>{
 const r=setEdgeLength(square,0,1,6,frame)
 assert.ok(r.ok);assert.deepEqual(r.ring[0],square[0]);assert.deepEqual(r.ring[1],{x:6,y:0});assert.equal(edgeLength(r.ring,0,1),6)
 assert.equal(setEdgeLength(square,0,1,25,frame).ok,false)
 assert.equal(setEdgeLength(square,0,1,0,frame).ok,false)})
test('a node cannot be moved outside the frame or across the outline',()=>{
 assert.equal(moveNode(square,0,{x:-1,y:0},frame).ok,false)
 assert.equal(moveNode(square,0,{x:5,y:12},frame).ok,false)
 assert.ok(moveNode(square,0,{x:1,y:1},frame).ok)})
test('points inside and outside a ring',()=>{assert.ok(insideRing(square,{x:5,y:5}));assert.equal(insideRing(square,{x:15,y:5}),false)})

const tank={id:'a',label:'Bồn nước',x:2,y:5,width_m:1,depth_m:1,height_m:1.2,scope:'roof',source:'gemini',confidence:.8,confirmed:true,ai_ref:'o1',ai_edited:true}
let n=0;const id=()=>'new'+(++n)
test('a pasted object is a new, unconfirmed object with the next free name and no link to the AI box',()=>{
 const [c]=pasteObjects([tank],[tank],1,frame,id)
 assert.notEqual(c.id,'a');assert.equal(c.label,'Bồn nước 2');assert.equal(c.confirmed,false);assert.equal(c.ai_ref,null);assert.equal(c.height_m,1.2)
 assert.deepEqual([c.x,c.y],[2.5,4.5])
 const [d]=pasteObjects([tank],[tank,c],2,frame,id)
 assert.equal(d.label,'Bồn nước 3');assert.deepEqual([d.x,d.y],[3,4])})
test('a group keeps its spacing and is pushed back as one at the frame edge',()=>{
 const left={...tank,x:18.8,y:.2},right={...tank,id:'b',x:17,y:3}
 const [a,b]=pasteObjects([left,right],[left,right],1,frame,id)
 assert.ok(a.x+a.width_m<=20&&a.y>=0);assert.equal(+(a.x-b.x).toFixed(3),1.8);assert.equal(+(b.y-a.y).toFixed(3),2.8)})
