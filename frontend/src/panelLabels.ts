import type {PlacedPanel} from './studioTypes'
export type PanelBadge={id:string;index:number;x:number;y:number;width:number;height:number;active:boolean}
/** Screen-space collision rejection: the selected panel always gets priority. */
export function panelBadges(panels:PlacedPanel[],activeId:string|undefined,scale:number,sx:(x:number)=>number,sy:(y:number)=>number,viewportRatio=1){
 const badges:PanelBadge[]=[],ratio=Math.max(.2,viewportRatio)
 const order=panels.map((p,index)=>({p,index})).sort((a,b)=>Number(b.p.id===activeId)-Number(a.p.id===activeId))
 for(const {p,index} of order){
  const active=p.id===activeId,width=(Math.max(4,String(index+1).length+1)*6+14)/ratio,height=20/ratio
  // At overview scale, keep only the active badge. Rotated panels use their
  // smaller side as a conservative fit bound rather than their bounding box.
  if(!active&&Math.min(p.width_m,p.height_m)*scale<width+6/ratio)continue
  const cx=sx(p.x+p.width_m/2),cy=sy(p.y+p.height_m/2)
  if(!active&&(cx<0||cx>900||cy<0||cy>630))continue
  const x=Math.max(width/2+8,Math.min(892-width/2,sx(p.x+p.width_m/2))),y=Math.max(height/2+8,Math.min(622-height/2,sy(p.y+p.height_m/2)-(active?height:0)))
  if(badges.some(b=>Math.abs(b.x-x)<(b.width+width)/2+4/ratio&&Math.abs(b.y-y)<(b.height+height)/2+4/ratio))continue
  badges.push({id:p.id,index,x,y,width,height,active})
 }
 return badges
}
