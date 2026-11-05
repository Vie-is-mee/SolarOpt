// Where to mark a panel on a sloped roof: installers measure on the roof surface, from the eave up the
// fall line and along the eave, not on the horizontal plan. A plan distance d up the slope is d / cos(tilt)
// on the roof (4 m in plan is 4,38 m on a 24° roof).
import type {Config,Point} from './studioTypes'

export type SlopeFrame={faceId:string;label:string;tilt:number;at:(p:Point)=>{up:number;along:number}}

/** Frame of a sloped face (tilt above 1°): up = distance on the roof from the eave (its lowest edge),
 * along = distance along the eave from its left end as seen standing at the eave looking up to the ridge. */
export function slopeFrame(config:Config,faceId:string|null|undefined):SlopeFrame|null{
 const face=(config.roof_faces||[]).find(f=>f.id===faceId)
 const base=!face&&faceId==='base'
 const tilt=face?face.tilt_deg:base?config.roof_tilt_deg:0
 if(!(tilt>1))return null
 const azimuth=face?face.azimuth_deg:config.roof_azimuth_deg
 const pts=face?face.polygon:config.roof_polygon.length?config.roof_polygon:[{x:0,y:0},{x:config.roof_width_m,y:0},{x:config.roof_width_m,y:config.roof_height_m},{x:0,y:config.roof_height_m}]
 const b=(azimuth-config.north_rotation_deg)*Math.PI/180,u=[Math.sin(b),Math.cos(b)],v=[-Math.cos(b),Math.sin(b)],c=Math.cos(tilt*Math.PI/180)
 const dot=(p:Point,d:number[])=>p.x*d[0]+p.y*d[1]
 const eave=Math.max(...pts.map(p=>dot(p,u))),left=Math.min(...pts.map(p=>dot(p,v)))
 return {faceId:faceId!,label:face?.label??'Mái',tilt,at:p=>({up:(eave-dot(p,u))/c,along:dot(p,v)-left})}
}
