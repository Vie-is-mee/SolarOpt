import {test} from 'node:test'
import assert from 'node:assert/strict'
import {loadTs} from './tsload.mjs'
const {slopeFrame}=await loadTs('slopeCoords')

const rect=(x0,y0,x1,y1)=>[{x:x0,y:y0},{x:x1,y:y0},{x:x1,y:y1},{x:x0,y:y1}]
const cfg=(rot=0)=>({north_rotation_deg:rot,roof_tilt_deg:0,roof_azimuth_deg:180,roof_width_m:12,roof_height_m:9,roof_polygon:[],
 roof_faces:[{id:'s',label:'Mái dốc 1',polygon:rect(0,0,12,4.5),tilt_deg:24,azimuth_deg:(180+rot)%360},{id:'n',label:'Mái dốc 2',polygon:rect(0,4.5,12,9),tilt_deg:24,azimuth_deg:rot%360},{id:'f',label:'Mái bằng',polygon:rect(0,0,1,1),tilt_deg:0,azimuth_deg:180}]})
const c=Math.cos(24*Math.PI/180),close=(a,b)=>assert(Math.abs(a-b)<1e-9,`${a} ≠ ${b}`)

test('distances up the slope are measured on the roof from the eave',()=>{
 const s=slopeFrame(cfg(),'s')
 close(s.at({x:3,y:4}).up,4/c)             // 4 m in plan = 4,38 m on a 24° roof
 assert(Math.abs(4/c-4.379)<.001)
 close(s.at({x:3,y:0}).up,0)
 close(s.at({x:3,y:4}).along,3)            // facing up (north) from the south eave: left end is x = 0
 const n=slopeFrame(cfg(),'n')
 close(n.at({x:3,y:9}).up,0);close(n.at({x:3,y:5}).up,4/c)
 close(n.at({x:3,y:5}).along,12-3)        // facing south from the north eave, left is east (x = 12)
})

test('the frame turns with the house and ignores flat faces',()=>{
 const s=slopeFrame(cfg(90),'s')
 close(s.at({x:3,y:4}).up,4/c);close(s.at({x:3,y:4}).along,3)
 assert.equal(slopeFrame(cfg(),'f'),null)
 assert.equal(slopeFrame(cfg(),'missing'),null)
 const plain={...cfg(),roof_faces:[],roof_tilt_deg:15,roof_azimuth_deg:180}
 close(slopeFrame(plain,'base').at({x:0,y:3}).up,3/Math.cos(15*Math.PI/180))
})
