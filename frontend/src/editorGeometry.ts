import type {Config,Obstacle,Point} from './studioTypes'
export const outerRoof=(c:Config)=>c.roof_polygon.length?c.roof_polygon:[{x:0,y:0},{x:c.roof_width_m,y:0},{x:c.roof_width_m,y:c.roof_height_m},{x:0,y:c.roof_height_m}]
export function footprint(o:Obstacle):Point[]{
 const points=o.shape==='polygon'&&o.points?.length?o.points:o.shape==='ellipse'?Array.from({length:48},(_,i)=>({x:o.width_m/2+Math.cos(i*Math.PI/24)*o.width_m/2,y:o.depth_m/2+Math.sin(i*Math.PI/24)*o.depth_m/2})):[{x:0,y:0},{x:o.width_m,y:0},{x:o.width_m,y:o.depth_m},{x:0,y:o.depth_m}]
 const a=(o.rotation_deg||0)*Math.PI/180,co=Math.cos(a),si=Math.sin(a),cx=o.width_m/2,cy=o.depth_m/2
 return points.map(p=>({x:o.x+cx+(p.x-cx)*co-(p.y-cy)*si,y:o.y+cy+(p.x-cx)*si+(p.y-cy)*co}))
}
export function polygonObstacle(points:Point[]):Partial<Obstacle>{const minX=Math.min(...points.map(p=>p.x)),minY=Math.min(...points.map(p=>p.y)),w=Math.max(.05,Math.max(...points.map(p=>p.x))-minX),h=Math.max(.05,Math.max(...points.map(p=>p.y))-minY);return {x:minX,y:minY,width_m:w,depth_m:h,rotation_deg:0,shape:'polygon',points:points.map(p=>({x:p.x-minX,y:p.y-minY}))}}
export const pathOf=(points:Point[])=>points.length?'M'+points.map(p=>`${p.x},${p.y}`).join('L')+'Z':''
