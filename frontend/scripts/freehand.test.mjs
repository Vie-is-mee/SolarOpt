import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
async function module(name){const source=readFileSync(new URL('../src/'+name,import.meta.url),'utf8');return import('data:text/javascript;base64,'+Buffer.from(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText).toString('base64'))}
const {simplify,chaikin,smoothStroke,strokeLength,}=await module('freehand.ts')
const fmtVnd=await module('format.ts')

test('collinear jitter collapses to the two end points',()=>{const s=[0,1,2,3,4,5].map(x=>({x,y:x%2?0.001:0}));assert.deepEqual(simplify(s,.01),[s[0],s[5]])})
test('chaikin keeps the stroke ends and rounds the corner',()=>{const s=[{x:0,y:0},{x:1,y:0},{x:1,y:1}];const c=chaikin(s,1);assert.deepEqual(c[0],s[0]);assert.deepEqual(c.at(-1),s[2]);assert.ok(c.every(p=>!(p.x===1&&p.y===0)))})
test('a dense circle stroke becomes a smooth polygon within the vertex cap',()=>{const s=Array.from({length:600},(_,i)=>{const a=i/600*Math.PI*2;return{x:5+3*Math.cos(a)+(i%3)*.002,y:5+3*Math.sin(a)}});const out=smoothStroke(s,.01,48);assert.ok(out.length<=48&&out.length>=12,String(out.length));for(const p of out)assert.ok(Math.abs(Math.hypot(p.x-5,p.y-5)-3)<.08)})
test('stroke length sums segments',()=>{assert.equal(strokeLength([{x:0,y:0},{x:3,y:4},{x:3,y:0}]),9)})
test('money reads in triệu / tỷ by magnitude',()=>{const {vnd,parseDigits,grouped}=fmtVnd;assert.equal(vnd(850000),'850.000 đ');assert.equal(vnd(21924000),'21,9 triệu đ');assert.equal(vnd(1990000),'1,99 triệu đ');assert.equal(vnd(120000000),'120 triệu đ');assert.equal(vnd(2500000000),'2,5 tỷ đ');assert.equal(vnd(-5600000),'-5,6 triệu đ');assert.equal(vnd(15000000,'đ/năm'),'15 triệu đ/năm');assert.equal(parseDigits('21.924.000 đ'),21924000);assert.equal(parseDigits(''),null);assert.equal(grouped(1234567),'1.234.567')})
