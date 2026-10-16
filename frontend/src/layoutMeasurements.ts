import type {PlacedPanel,Point} from './studioTypes'
export function panelCorners(p:PlacedPanel):Point[]{
 const a=(p.rotation_deg||0)*Math.PI/180,co=Math.cos(a),si=Math.sin(a),cx=p.x+p.width_m/2,cy=p.y+p.height_m/2
 return [[-p.width_m/2,-p.height_m/2],[p.width_m/2,-p.height_m/2],[p.width_m/2,p.height_m/2],[-p.width_m/2,p.height_m/2]].map(([x,y])=>({x:cx+x*co-y*si,y:cy+x*si+y*co}))
}
export const panelLabel=(index:number)=>'P'+String(index+1).padStart(3,'0')
