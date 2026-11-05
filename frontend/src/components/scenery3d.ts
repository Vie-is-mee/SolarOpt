import * as THREE from 'three'
import type {Obstacle} from '../studioTypes'
import {solarPosition} from '../solarPosition'
export {solarPosition}

const D=Math.PI/180
/** Drawing (x right, y up the page) -> three (X right, Y up in the air, Z towards the viewer). */
export const v3=(x:number,y:number,z:number)=>new THREE.Vector3(x,z,-y)
/** Unit vector in drawing coordinates for a compass azimuth, given the azimuth of the drawing's +Y axis. */
export const compassDir=(azimuth:number,rot:number)=>{const b=(azimuth-rot)*D;return [Math.sin(b),Math.cos(b)]}

/** Point on the sky dome at radius r for a compass azimuth/altitude. */
export function skyPoint(centre:THREE.Vector3,r:number,az:number,alt:number,rot:number){
 const [bx,by]=compassDir(az,rot)
 return new THREE.Vector3(centre.x+bx*Math.cos(alt*D)*r,Math.max(0,centre.y*0)+Math.sin(alt*D)*r,centre.z-by*Math.cos(alt*D)*r)
}

function label(text:string,color:string,size=1){
 const c=document.createElement('canvas');c.width=256;c.height=128;const g=c.getContext('2d')!
 g.font='700 64px "Be Vietnam Pro", system-ui, sans-serif';g.textAlign='center';g.textBaseline='middle'
 g.lineWidth=10;g.strokeStyle='rgba(255,255,255,.9)';g.strokeText(text,128,64);g.fillStyle=color;g.fillText(text,128,64)
 const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace
 const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,depthWrite:false,fog:false}));sprite.scale.set(2*size,size,1);return sprite
}

/** Sun disc with a soft glow, drawn outside the fog so it stays visible when zoomed out. */
export function sunModel(radius:number){
 const group=new THREE.Group()
 group.add(new THREE.Mesh(new THREE.SphereGeometry(radius,32,16),new THREE.MeshBasicMaterial({color:0xffd75e,fog:false})))
 const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d')!,grad=g.createRadialGradient(64,64,8,64,64,64)
 grad.addColorStop(0,'rgba(255,226,120,.95)');grad.addColorStop(.35,'rgba(255,205,90,.45)');grad.addColorStop(1,'rgba(255,200,80,0)');g.fillStyle=grad;g.fillRect(0,0,128,128)
 const glowTex=new THREE.CanvasTexture(c);glowTex.colorSpace=THREE.SRGBColorSpace
 const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex,depthWrite:false,fog:false,transparent:true}));glow.scale.setScalar(radius*7);group.add(glow)
 return group
}

/** Dashed arc of the day's sun path above the horizon, with sunrise/sunset ticks. */
export function sunPath(centre:THREE.Vector3,r:number,lat:number,lon:number,date:string,rot:number){
 const pts:THREE.Vector3[]=[]
 for(let h=4;h<=20;h+=.1){const p=solarPosition(lat,lon,date,h);if(p.alt>-.5)pts.push(skyPoint(centre,r,p.az,Math.max(0,p.alt),rot))}
 const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineDashedMaterial({color:0xf0b429,dashSize:r*.03,gapSize:r*.02,fog:false,transparent:true,opacity:.85}))
 line.computeLineDistances();return line
}

/** Ground compass: four arrows with labels, north highlighted, oriented to true north of the drawing. */
export function compass(centre:THREE.Vector3,radius:number,rot:number){
 const group=new THREE.Group(),dirs:[number,string,string][]=[[0,'BẮC','#c0392b'],[90,'ĐÔNG','#1e6b45'],[180,'NAM','#1e6b45'],[270,'TÂY','#1e6b45']]
 const ring=new THREE.Mesh(new THREE.RingGeometry(radius*.985,radius,96),new THREE.MeshBasicMaterial({color:0xffffff,transparent:true,opacity:.75,side:THREE.DoubleSide}))
 ring.rotation.x=-Math.PI/2;ring.position.set(centre.x,.03,centre.z);group.add(ring)
 for(const [az,text,color] of dirs){
  const [bx,by]=compassDir(az,rot),ox=centre.x+bx*radius,oz=centre.z-by*radius,len=radius*.2,w=radius*.07
  const tip=new THREE.Vector3(ox+bx*len,.05,oz-by*len),px=-by,py=-bx   // perpendicular in three (x,z)
  const shape=[tip,new THREE.Vector3(ox+px*w,.05,oz+py*w),new THREE.Vector3(ox-px*w,.05,oz-py*w)]
  const arrow=new THREE.Mesh(new THREE.BufferGeometry().setFromPoints(shape),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide}))
  group.add(arrow)
  const tag=label(text,color,radius*.2);tag.position.set(ox+bx*len*1.9,radius*.08,oz-by*len*1.9);group.add(tag)
 }
 return group
}

export type AssetMats={concrete:THREE.Material;steel:THREE.Material;dark:THREE.Material;white:THREE.Material;glass:THREE.Material;trunk:THREE.Material;leaf:THREE.Material;leaf2:THREE.Material;facade:THREE.Material;cap:THREE.Material}

/** 3D model for an obstacle by kind; unknown kinds fall back to a footprint prism. Centred on the
 * footprint centre and rotated like the drawing (CCW in plan = rotation about +Y). */
export function assetModel(o:Obstacle,base:number,m:AssetMats,prism:()=>THREE.Object3D):THREE.Object3D{
 const w=o.width_m,d=o.depth_m,h=Math.max(.05,o.height_m),g=new THREE.Group()
 const add=(geo:THREE.BufferGeometry,mat:THREE.Material,x=0,y=0,z=0)=>{const mesh=new THREE.Mesh(geo,mat);mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;g.add(mesh);return mesh}
 switch(o.kind){
  case 'tank':{const r=Math.min(w,d)/2;add(new THREE.CylinderGeometry(r,r,h*.86,28),m.steel,0,h*.43);add(new THREE.CylinderGeometry(r*.6,r*1.02,h*.14,28),m.steel,0,h*.93)
   for(const s of [-1,1])add(new THREE.BoxGeometry(r*2.1,.08,.12),m.dark,0,.04,s*r*.6);break}
  case 'chimney':add(new THREE.BoxGeometry(w,h*.9,d),m.concrete,0,h*.45);add(new THREE.BoxGeometry(w*1.25,h*.1,d*1.25),m.dark,0,h*.95);break
  case 'ac':{add(new THREE.BoxGeometry(w,h,d),m.white,0,h/2);const fan=add(new THREE.CylinderGeometry(Math.min(h,w)*.36,Math.min(h,w)*.36,.02,24),m.dark,w*.18,h/2,d/2+.011);fan.rotation.x=Math.PI/2;break}
  case 'stair':{add(new THREE.BoxGeometry(w,h,d),m.facade,0,h/2);add(new THREE.BoxGeometry(w*1.04,.12,d*1.04),m.cap,0,h+.06);add(new THREE.BoxGeometry(.9,2.1,.04),m.dark,0,1.05,d/2+.02);break}
  case 'skylight':add(new THREE.BoxGeometry(w,h*.5,d),m.concrete,0,h*.25);add(new THREE.BoxGeometry(w*.92,h*.5,d*.92),m.glass,0,h*.75);break
  case 'tree_round':{add(new THREE.CylinderGeometry(.14,.22,h*.45,8),m.trunk,0,h*.225)
   const canopy=add(new THREE.IcosahedronGeometry(.5,1),m.leaf,0,h*.62);canopy.scale.set(w,h*.62,d)
   const top=add(new THREE.IcosahedronGeometry(.5,1),m.leaf2,w*.12,h*.8,-d*.08);top.scale.set(w*.62,h*.34,d*.62);break}
  case 'tree_cone':add(new THREE.CylinderGeometry(.1,.16,h*.25,8),m.trunk,0,h*.125);add(new THREE.ConeGeometry(Math.min(w,d)/2,h*.55,10),m.leaf,0,h*.48);add(new THREE.ConeGeometry(Math.min(w,d)/2.6,h*.4,10),m.leaf2,0,h*.78);break
  case 'tree_palm':{add(new THREE.CylinderGeometry(.11,.17,h*.88,8),m.trunk,0,h*.44)
   for(let i=0;i<7;i++){const leaf=add(new THREE.ConeGeometry(.22,Math.min(w,d)*.62,4),i%2?m.leaf:m.leaf2,0,h*.9,0);leaf.rotation.set(Math.PI/2.4,i/7*Math.PI*2,0,'YXZ');leaf.translateY(Math.min(w,d)*.28)}
   break}
  case 'house':{const box=add(new THREE.BoxGeometry(w,h,d),m.facade,0,h/2),uv=box.geometry.attributes.uv as THREE.BufferAttribute
   // Facade texture repeats per 3 m bay and 3.3 m floor on each side of the box.
   const sizes=[[d,h],[d,h],[w,d],[w,d],[w,h],[w,h]];for(let f=0;f<6;f++)for(let k=0;k<4;k++){const i=f*4+k;uv.setXY(i,uv.getX(i)*sizes[f][0]/3,uv.getY(i)*sizes[f][1]/3.3)}
   add(new THREE.BoxGeometry(w+.3,.25,d+.3),m.cap,0,h+.12);break}
  case 'tank_flat':{const r=Math.min(d,h*.85)/2,c=add(new THREE.CylinderGeometry(r,r,w*.95,24),m.steel,0,h-r);c.rotation.z=Math.PI/2
   for(const s of [-1,1])add(new THREE.BoxGeometry(.12,h-r,d*.9),m.dark,s*w*.32,(h-r)/2);break}
  case 'solar_heater':{const tank=add(new THREE.CylinderGeometry(.22,.22,w*.95,18),m.steel,0,h-.22,-d*.32);tank.rotation.z=Math.PI/2
   const tubes=add(new THREE.BoxGeometry(w*.9,.06,d*.95),m.glass,0,h*.5,0);tubes.rotation.x=-Math.atan2(h*.8,d)
   for(const s of [-1,1])add(new THREE.BoxGeometry(.05,h,.05),m.dark,s*w*.45,h/2,-d*.32);break}
  case 'hatch':add(new THREE.BoxGeometry(w,h,d),m.concrete,0,h/2);add(new THREE.BoxGeometry(w*.9,.05,d*.9),m.dark,0,h+.025);break
  case 'parapet':case 'wall':add(new THREE.BoxGeometry(w,h,d),o.kind==='wall'?m.facade:m.concrete,0,h/2);break
  case 'vent_turbine':add(new THREE.CylinderGeometry(w*.2,w*.25,h*.35,12),m.steel,0,h*.175);add(new THREE.SphereGeometry(Math.min(w,d)/2,16,12),m.steel,0,h*.62);break
  case 'dish':{add(new THREE.CylinderGeometry(.04,.04,h*.75,8),m.dark,0,h*.375);const dish=add(new THREE.SphereGeometry(Math.min(w,d)/2,20,10,0,Math.PI*2,0,Math.PI/3.2),m.white,0,h*.75);dish.rotation.x=-Math.PI/2.6;break}
  case 'lightning':case 'pole':add(new THREE.CylinderGeometry(Math.min(w,d)*.25,Math.min(w,d)*.5,h,10),o.kind==='pole'?m.concrete:m.steel,0,h/2);if(o.kind==='pole')add(new THREE.BoxGeometry(1.4,.08,.08),m.dark,0,h*.9);break
  case 'cooling':add(new THREE.CylinderGeometry(Math.min(w,d)/2,Math.min(w,d)/2*.85,h*.85,24),m.white,0,h*.425);add(new THREE.CylinderGeometry(Math.min(w,d)/2*.6,Math.min(w,d)/2*.6,h*.15,20),m.dark,0,h*.925);break
  case 'sign':add(new THREE.BoxGeometry(w,h*.6,.08),m.white,0,h*.7);for(const s of [-1,1])add(new THREE.BoxGeometry(.08,h*.4,.08),m.dark,s*w*.4,h*.2);break
  case 'drying':for(const s of [-1,1])add(new THREE.BoxGeometry(.05,h,d),m.steel,s*w/2,h/2);for(let i=0;i<4;i++)add(new THREE.BoxGeometry(w,.02,.02),m.dark,0,h*.95,-d/2+i*d/3);break
  case 'tower':{const box=add(new THREE.BoxGeometry(w,h,d),m.facade,0,h/2),uv=box.geometry.attributes.uv as THREE.BufferAttribute
   const sizes=[[d,h],[d,h],[w,d],[w,d],[w,h],[w,h]];for(let f=0;f<6;f++)for(let k=0;k<4;k++){const i=f*4+k;uv.setXY(i,uv.getX(i)*sizes[f][0]/3,uv.getY(i)*sizes[f][1]/3.3)}
   add(new THREE.BoxGeometry(w+.3,.3,d+.3),m.cap,0,h+.15);break}
  default:return prism()
 }
 g.position.copy(v3(o.x+w/2,o.y+d/2,base));g.rotation.y=(o.rotation_deg||0)*D
 return g
}
