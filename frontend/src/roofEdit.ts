import type {Obstacle,Point} from './studioTypes'

/** Editing the roof outline as a closed ring of nodes. Every operation returns a ring that is still closed and
 * does not cross itself, or a reason it was refused, so the outline can never be left broken. */
export type RingEdit={ok:true;ring:Point[]}|{ok:false;reason:string}
const round=(v:number)=>Math.round(v*1000)/1000
const cross=(o:Point,a:Point,b:Point)=>(a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x)
function segmentsCross(a:Point,b:Point,c:Point,d:Point){return cross(a,b,c)*cross(a,b,d)<-1e-12&&cross(c,d,a)*cross(c,d,b)<-1e-12}
function onSegment(p:Point,a:Point,b:Point){const len=Math.hypot(b.x-a.x,b.y-a.y);if(len<1e-9)return Math.hypot(p.x-a.x,p.y-a.y)<1e-6;return Math.abs(cross(a,b,p))/len<1e-6&&(p.x-a.x)*(b.x-a.x)+(p.y-a.y)*(b.y-a.y)>-1e-9&&(p.x-b.x)*(a.x-b.x)+(p.y-b.y)*(a.y-b.y)>-1e-9}

export function insideRing(ring:Point[],p:Point){let c=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if((a.y>p.y)!==(b.y>p.y)&&p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x)c=!c}return c}

export function ringArea(ring:Point[]){let a=0;ring.forEach((p,i)=>{const q=ring[(i+1)%ring.length];a+=p.x*q.y-q.x*p.y});return Math.abs(a)/2}

/** True when no two edges of the ring cross or touch, other than neighbours sharing their node. */
export function ringIsSimple(ring:Point[]){const n=ring.length
 if(n<3)return false
 for(let i=0;i<n;i++){const a=ring[i],b=ring[(i+1)%n]
  if(Math.hypot(b.x-a.x,b.y-a.y)<1e-6)return false
  for(let j=i+1;j<n;j++){if(j===i+1||(i===0&&j===n-1))continue
   const c=ring[j],d=ring[(j+1)%n]
   if(segmentsCross(a,b,c,d)||onSegment(c,a,b)||onSegment(d,a,b)||onSegment(a,c,d)||onSegment(b,c,d))return false}}
 return true}

function distanceToSegment(p:Point,a:Point,b:Point){const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)}

/** Index i of the edge from node i to node i+1 nearest to p. */
export function nearestEdge(ring:Point[],p:Point){let best=0,dist=Infinity;ring.forEach((a,i)=>{const d=distanceToSegment(p,a,ring[(i+1)%ring.length]);if(d<dist-1e-9){dist=d;best=i}});return best}

/** A new node always joins the ring between the two ends of the nearest edge, so it can never be left alone. */
export function insertNode(ring:Point[],p:Point):RingEdit{const i=nearestEdge(ring,p),at={x:round(p.x),y:round(p.y)}
 if(ring.some(v=>Math.hypot(v.x-at.x,v.y-at.y)<.01))return{ok:false,reason:'Node mới trùng một node đã có.'}
 const next=[...ring.slice(0,i+1),at,...ring.slice(i+1)]
 return ringIsSimple(next)?{ok:true,ring:next}:{ok:false,reason:'Node ở đây làm biên mái tự cắt; chọn điểm khác.'}}

/** Removing a node joins its two neighbours. */
export function removeNode(ring:Point[],index:number):RingEdit{if(ring.length<=3)return{ok:false,reason:'Mái cần ít nhất 3 node.'}
 const next=ring.filter((_,i)=>i!==index)
 if(!ringIsSimple(next))return{ok:false,reason:'Xóa node này làm biên mái tự cắt.'}
 if(ringArea(next)<.2)return{ok:false,reason:'Xóa node này làm mái gần như không còn diện tích.'}
 return{ok:true,ring:next}}

/** Length of the edge from a node to the node before (-1) or after (+1) it. */
export function edgeLength(ring:Point[],index:number,side:1|-1){const n=ring.length,a=ring[index],b=ring[(index+side+n)%n];return Math.hypot(b.x-a.x,b.y-a.y)}

/** Type an edge length: the selected node stays, the node at the other end slides along the edge. */
export function setEdgeLength(ring:Point[],index:number,side:1|-1,length:number,frame:{width:number;height:number}):RingEdit{const n=ring.length,other=(index+side+n)%n,a=ring[index],b=ring[other],current=Math.hypot(b.x-a.x,b.y-a.y)
 if(!(length>=.05))return{ok:false,reason:'Chiều dài cạnh phải từ 0,05 m.'}
 const moved={x:round(a.x+(b.x-a.x)*length/current),y:round(a.y+(b.y-a.y)*length/current)}
 if(moved.x<-1e-6||moved.y<-1e-6||moved.x>frame.width+1e-6||moved.y>frame.height+1e-6)return{ok:false,reason:'Cạnh này vượt khung mái; đổi kích thước khung ở bước Dữ liệu.'}
 const next=ring.map((p,i)=>i===other?moved:p)
 return ringIsSimple(next)?{ok:true,ring:next}:{ok:false,reason:'Chiều dài này làm biên mái tự cắt.'}}

export function moveNode(ring:Point[],index:number,to:Point,frame:{width:number;height:number}):RingEdit{const at={x:round(to.x),y:round(to.y)}
 if(at.x<0||at.y<0||at.x>frame.width||at.y>frame.height)return{ok:false,reason:'Node phải nằm trong khung mái.'}
 const next=ring.map((p,i)=>i===index?at:p)
 return ringIsSimple(next)?{ok:true,ring:next}:{ok:false,reason:'Vị trí này làm biên mái tự cắt.'}}

const PASTE_STEP=.5
const baseName=(label:string)=>label.replace(/\s*·\s*(bản sao|vị trí tạm)$/,'').replace(/\s+\d+$/,'')

/** Copies of objects keeping their spacing; each paste lands one more step away so they do not stack. A copy is new
 * data, so it waits for confirmation, and it keeps no link to the AI box it came from. */
export function pasteObjects(copied:Obstacle[],existing:Obstacle[],pasteNumber:number,frame:{width:number;height:number},newId:()=>string):Obstacle[]{
 const taken=new Set(existing.map(o=>o.label)),shift=PASTE_STEP*pasteNumber
 const onRoof=copied.filter(o=>o.scope==='roof')
 // The whole group is pushed back as one if it would leave the frame, so its spacing survives.
 const backX=Math.max(0,...onRoof.map(o=>o.x+o.width_m+shift-frame.width)),backY=Math.max(0,...onRoof.map(o=>shift-o.y))
 return copied.map(o=>{const name=baseName(o.label);let n=2,label=`${name} ${n}`;while(taken.has(label)){n++;label=`${name} ${n}`}taken.add(label)
  return {...structuredClone(o),id:newId(),label,x:round(o.x+shift-backX),y:round(o.y-shift+backY),confirmed:false,ai_ref:null,ai_edited:false,position_assumed:false}})}
