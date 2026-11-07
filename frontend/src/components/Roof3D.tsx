import {useEffect,useRef,useState} from 'react'
import {Icon} from './Icon'
import * as THREE from 'three'
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js'
import type {Config,Design,Obstacle,Scene} from '../studioTypes'
import {footprint} from '../editorGeometry'
import {panelCorners,panelLabel} from '../layoutMeasurements'
import {lossColor} from '../reportData'
import {assetModel,compass,skyPoint,sunModel,sunPath,type AssetMats} from './scenery3d'

type Face=NonNullable<Scene['faces']>[number]&{azimuth_deg?:number;origin?:number[];regions?:{boundary:number[][];openings:number[][][]}[];mount?:string|null;mount_tilt?:number;mount_azimuth?:number}
const D=Math.PI/180,FLOOR=3.3,BAY=3
// Fixed, neutral palette that reads well next to any roof photo or roof colour.
const PALETTE={plaster:'#ece5d8',plinth:'#a89f90',glass:'#3c4a57',frame:'#f6f3ec',parapet:0xd9d3c6,cap:0xb8b1a3,concrete:0xcfcac0,steel:0xdfe3e6,neighbour:'#e2ddd2',sky:'#9fc4e6',horizon:'#e8f0f3'}
// Drawing (x right, y up the page) -> three (X right, Y up in the air, Z towards the viewer).
const v3=(x:number,y:number,z:number)=>new THREE.Vector3(x,z,-y)
const downhill=(azimuth:number,rot:number)=>{const b=(azimuth-rot)*D;return [Math.sin(b),Math.cos(b)]}
/** Same plane equation as the backend (geometry.surface_z): elevation at the face origin plus slope. */
function zOn(face:Face,x:number,y:number,rot:number){
 const [ux,uy]=downhill(face.azimuth_deg??180,rot),g=-Math.tan((face.tilt_deg||0)*D),[ox,oy]=face.origin||[0,0]
 return face.elevation_m+g*ux*(x-ox)+g*uy*(y-oy)
}
const inside=(pt:number[],ring:number[][])=>{let c=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const [xi,yi]=ring[i],[xj,yj]=ring[j];if((yi>pt[1])!==(yj>pt[1])&&pt[0]<(xj-xi)*(pt[1]-yi)/(yj-yi)+xi)c=!c}return c}
const segDist=(p:number[],a:number[],b:number[])=>{const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)}
const onOutline=(p:number[],rings:number[][][])=>rings.some(r=>r.some((a,i)=>i<r.length-1&&segDist(p,a,r[i+1])<.02))

function canvasTexture(w:number,h:number,draw:(g:CanvasRenderingContext2D)=>void,repeat=true){
 const c=document.createElement('canvas');c.width=w;c.height=h;draw(c.getContext('2d')!)
 const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8
 if(repeat){t.wrapS=t.wrapT=THREE.RepeatWrapping}
 return t
}
/** One facade bay (BAY m wide, one FLOOR high): plaster, a window band with frames and a sill shadow. */
const facadeTexture=(base:string)=>canvasTexture(256,256,g=>{
 g.fillStyle=base;g.fillRect(0,0,256,256)
 for(let i=0;i<900;i++){g.fillStyle=`rgba(0,0,0,${Math.random()*.035})`;g.fillRect(Math.random()*256,Math.random()*256,2,2)}
 g.fillStyle=PALETTE.frame;g.fillRect(36,70,184,112)
 const glass=g.createLinearGradient(0,78,0,176);glass.addColorStop(0,'#6f8394');glass.addColorStop(1,PALETTE.glass);g.fillStyle=glass;g.fillRect(44,78,168,96)
 g.fillStyle=PALETTE.frame;g.fillRect(124,78,8,96)
 g.fillStyle='rgba(0,0,0,.18)';g.fillRect(36,182,184,6)
 g.fillStyle='rgba(0,0,0,.06)';g.fillRect(0,250,256,6)
})
const plinthTexture=()=>canvasTexture(64,64,g=>{g.fillStyle=PALETTE.plinth;g.fillRect(0,0,64,64);for(let i=0;i<200;i++){g.fillStyle=`rgba(0,0,0,${Math.random()*.06})`;g.fillRect(Math.random()*64,Math.random()*64,2,2)}})
/** Module seen from the sky: anodised aluminium frame, 6 x 10 mono cells with clipped corners and a faint
 * per-cell tone (real modules are never one flat colour), three busbars per cell column. */
const cellTexture=()=>canvasTexture(256,420,g=>{
 const W=256,H=420,f=7,cw=(W-2*f)/6,ch=(H-2*f)/10
 const al=g.createLinearGradient(0,0,W,H);al.addColorStop(0,'#dfe4e8');al.addColorStop(.5,'#a9b2ba');al.addColorStop(1,'#d3d9de');g.fillStyle=al;g.fillRect(0,0,W,H)
 g.fillStyle='#0b1828';g.fillRect(f,f,W-2*f,H-2*f)
 for(let i=0;i<6;i++)for(let j=0;j<10;j++){const x=f+i*cw,y=f+j*ch;g.fillStyle=`hsl(214,44%,${17+Math.random()*6}%)`;g.fillRect(x+1.2,y+1.2,cw-2.4,ch-2.4)
  g.fillStyle='#0b1828';for(const [cx,cy] of [[x+1.2,y+1.2],[x+cw-1.2,y+1.2],[x+1.2,y+ch-1.2],[x+cw-1.2,y+ch-1.2]]){g.beginPath();g.arc(cx,cy,3,0,Math.PI*2);g.fill()}}
 g.strokeStyle='rgba(200,214,228,.32)';g.lineWidth=1
 for(let i=0;i<6;i++)for(const k of [.25,.5,.75]){g.beginPath();g.moveTo(f+(i+k)*cw,f);g.lineTo(f+(i+k)*cw,H-f);g.stroke()}
},false)
/** Weathered concrete / waterproofing screed, one tile = 4 m with joints every 2 m. */
const concreteTexture=()=>canvasTexture(512,512,g=>{
 g.fillStyle='#c8c4ba';g.fillRect(0,0,512,512)
 for(let i=0;i<16;i++){const x=Math.random()*512,y=Math.random()*512,r=40+Math.random()*120,s=g.createRadialGradient(x,y,0,x,y,r);s.addColorStop(0,`rgba(95,88,72,${.04+Math.random()*.06})`);s.addColorStop(1,'rgba(95,88,72,0)');g.fillStyle=s;g.fillRect(0,0,512,512)}
 for(let i=0;i<9000;i++){g.fillStyle=Math.random()>.5?'rgba(255,255,255,.06)':'rgba(0,0,0,.07)';g.fillRect(Math.random()*512,Math.random()*512,1.5,1.5)}
 g.strokeStyle='rgba(80,74,62,.22)';g.lineWidth=2
 for(const q of [1,256]){g.beginPath();g.moveTo(q,0);g.lineTo(q,512);g.stroke();g.beginPath();g.moveTo(0,q);g.lineTo(512,q);g.stroke()}
})
/** Trapezoidal steel roof sheet, one tile = 1 m across the slope with four ribs; colour map or bump map. */
const sheetTexture=(bump:boolean)=>canvasTexture(256,16,g=>{
 g.fillStyle=bump?'#000':'#74889a';g.fillRect(0,0,256,16)
 for(let i=0;i<4;i++){const x=i*64+20,r=g.createLinearGradient(x,0,x+24,0)
  r.addColorStop(0,bump?'#000':'#627586');r.addColorStop(.5,bump?'#fff':'#a8b8c5');r.addColorStop(1,bump?'#000':'#627586');g.fillStyle=r;g.fillRect(x,0,24,16)}
})
const skyTexture=()=>canvasTexture(4,256,g=>{const s=g.createLinearGradient(0,0,0,256);s.addColorStop(0,PALETTE.sky);s.addColorStop(.75,PALETTE.horizon);s.addColorStop(1,'#f4f1e8');g.fillStyle=s;g.fillRect(0,0,4,256)},false)
const groundTexture=()=>canvasTexture(256,256,g=>{g.fillStyle='#9fb284';g.fillRect(0,0,256,256);for(let i=0;i<4000;i++){const l=Math.random();g.fillStyle=l>.5?'rgba(255,255,230,.06)':'rgba(40,60,20,.07)';g.fillRect(Math.random()*256,Math.random()*256,2,2)}})

/** Outer walls under a face: textured facade above a darker plinth; inner seams between faces get none. */
function wallQuads(face:Face,rot:number,outline:number[][][]){
 const fac:number[]=[],facUV:number[]=[],pl:number[]=[],plUV:number[]=[]
 for(const region of face.regions||face.polygons.map(p=>({boundary:p,openings:[]}))){
  const ring=region.boundary;let run=0
  for(let i=0;i<ring.length-1;i++){
   const [ax,ay]=ring[i],[bx,by]=ring[i+1],len=Math.hypot(bx-ax,by-ay)
   if(len<1e-6||!onOutline([(ax+bx)/2,(ay+by)/2],outline)){run+=len;continue}
   const za=zOn(face,ax,ay,rot),zb=zOn(face,bx,by,rot),base=.6,u0=run/BAY,u1=(run+len)/BAY
   // UV in metres so windows repeat every bay and every floor whatever the wall size.
   fac.push(ax,base,-ay,bx,base,-by,bx,zb,-by,ax,base,-ay,bx,zb,-by,ax,za,-ay)
   facUV.push(u0,base/FLOOR,u1,base/FLOOR,u1,zb/FLOOR,u0,base/FLOOR,u1,zb/FLOOR,u0,za/FLOOR)
   pl.push(ax,0,-ay,bx,0,-by,bx,base,-by,ax,0,-ay,bx,base,-by,ax,base,-ay)
   plUV.push(u0,0,u1,0,u1,1,u0,0,u1,1,u0,1)
   run+=len
  }
 }
 const geo=(p:number[],uv:number[])=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();return g}
 return {facade:geo(fac,facUV),plinth:geo(pl,plUV)}
}

/** Walls under a stacked roof part (faces sub<n>-…): from its outer edges down to the main eave. The lower
 * roof hides the part of the wall below it, so a raised gable or second tier reads as standing on the roof. */
function riserWalls(face:Face,rot:number,faces:Face[],floor:number){
 const prefix=face.id.split('-')[0]+'-',siblings=faces.filter(f=>f!==face&&f.id.startsWith(prefix)),pts:number[]=[]
 const rings=(f:Face)=>(f.regions||f.polygons.map(p=>({boundary:p,openings:[] as number[][][]}))).map(r=>r.boundary)
 for(const ring of rings(face))for(let i=0;i<ring.length-1;i++){
  const [ax,ay]=ring[i],[bx,by]=ring[i+1],mid:[number,number]=[(ax+bx)/2,(ay+by)/2]
  if(Math.hypot(bx-ax,by-ay)<1e-6||siblings.some(s=>onOutline(mid,rings(s))))continue
  const za=zOn(face,ax,ay,rot),zb=zOn(face,bx,by,rot)
  pts.push(ax,floor,-ay,bx,floor,-by,bx,zb,-by,ax,floor,-ay,bx,zb,-by,ax,za,-ay)
 }
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));g.computeVertexNormals();return g
}

/** Low parapet with a darker coping along the outer edge of flat roof faces. */
function parapet(face:Face,rot:number,outline:number[][][],wallMat:THREE.Material,capMat:THREE.Material){
 const group=new THREE.Group();if((face.tilt_deg||0)>1)return group
 for(const region of face.regions||[]){const ring=region.boundary
  for(let i=0;i<ring.length-1;i++){const a=ring[i],b=ring[i+1],len=Math.hypot(b[0]-a[0],b[1]-a[1]);if(len<.05||!onOutline([(a[0]+b[0])/2,(a[1]+b[1])/2],outline))continue
   const z=zOn(face,(a[0]+b[0])/2,(a[1]+b[1])/2,rot),h=.45,t=.16
   const wall=new THREE.Mesh(new THREE.BoxGeometry(len+t,h,t),wallMat),cap=new THREE.Mesh(new THREE.BoxGeometry(len+t+.06,.06,t+.08),capMat)
   const mid=v3((a[0]+b[0])/2,(a[1]+b[1])/2,z),angle=Math.atan2(b[1]-a[1],b[0]-a[0])
   for(const [m,y] of [[wall,h/2],[cap,h+.03]] as const){m.position.copy(mid);m.position.y+=y;m.rotation.y=angle;m.castShadow=true;m.receiveShadow=true;group.add(m)}
  }}
 return group
}

/** Roof face with UVs in the roof frame, so an aligned roof photo lands exactly where it was traced. */
type RoofUV='photo'|'tile'|'sheet'
function roofSurface(face:Face,rot:number,cfg:Config,material:THREE.Material,mode:RoofUV){
 const group=new THREE.Group(),[ux,uy]=downhill(face.azimuth_deg??180,rot)
 // photo: roof frame (0..1) so a traced photo lands where it was traced; tile: 4 m concrete tiles;
 // sheet: metres across / along the fall line so the ribs of a steel sheet run downhill.
 const uvOf=(x:number,y:number)=>mode==='photo'?[x/cfg.roof_width_m,y/cfg.roof_height_m]:mode==='tile'?[x/4,y/4]:[x*-uy+y*ux,x*ux+y*uy]
 for(const region of face.regions||face.polygons.map(p=>({boundary:p,openings:[]}))){
  const shape=new THREE.Shape(region.boundary.map(([x,y])=>new THREE.Vector2(x,y)))
  region.openings.forEach(h=>shape.holes.push(new THREE.Path(h.map(([x,y])=>new THREE.Vector2(x,y)))))
  const geo=new THREE.ShapeGeometry(shape),pos=geo.attributes.position as THREE.BufferAttribute,uv=geo.attributes.uv as THREE.BufferAttribute
  for(let i=0;i<pos.count;i++){const x=pos.getX(i),y=pos.getY(i);pos.setXYZ(i,x,zOn(face,x,y,rot)+.005,-y);const [u,v]=uvOf(x,y);uv.setXY(i,u,v)}
  geo.computeVertexNormals()
  const mesh=new THREE.Mesh(geo,material);mesh.receiveShadow=true;mesh.castShadow=true;group.add(mesh)
 }
 return group
}

function prism(points:{x:number;y:number}[],base:number,height:number,material:THREE.Material){
 const shape=new THREE.Shape(points.map(p=>new THREE.Vector2(p.x,p.y)))
 const geo=new THREE.ExtrudeGeometry(shape,{depth:Math.max(.02,height),bevelEnabled:false})
 geo.rotateX(-Math.PI/2);geo.translate(0,base,0)
 const mesh=new THREE.Mesh(geo,material);mesh.castShadow=true;mesh.receiveShadow=true;return mesh
}

/** Tracker rotation about a N-S axis: ideal angle tan(theta)=tan(zenith)*sin(az-180), clamped. */
function trackerAngle(sunAz:number,sunAlt:number,max:number){
 if(sunAlt<=0)return 0
 const theta=Math.atan(Math.tan((90-sunAlt)*D)*Math.sin((sunAz-180)*D))/D
 return Math.max(-max,Math.min(max,theta))
}

type PanelMats={back:THREE.Material;post:THREE.Material}
function panelModel(p:Design['panels'][number],index:number,face:Face|undefined,cfg:Config,scene:Scene|null,glassMat:THREE.Material,mats:PanelMats){
 const rot=cfg.north_rotation_deg,corners=panelCorners(p).map(c=>[c.x,c.y]),cx=p.x+p.width_m/2,cy=p.y+p.height_m/2
 const roofZ=(x:number,y:number)=>face?zOn(face,x,y,rot):cfg.roof_elevation_m,base=roofZ(cx,cy)
 let pts:THREE.Vector3[],raised=false
 if(face?.mount==='tilted_rack'||face?.mount==='tracker'){
  raised=true
  let tilt:number,facing:number,lift:number,offsets=corners.map(([x,y])=>[x-cx,y-cy])
  if(face.mount==='tilted_rack'){tilt=face.mount_tilt??15;facing=face.mount_azimuth??180
   const [ux,uy]=downhill(facing,rot),along=Math.max(...offsets.map(([dx,dy])=>dx*ux+dy*uy))*2
   lift=.3+along*Math.tan(tilt*D)/2
  }else{const theta=trackerAngle(scene?.sun.azimuth_deg??180,scene?.sun.altitude_deg??0,cfg.tracker_max_angle_deg??55)
   tilt=Math.abs(theta);facing=theta<0?90:270;lift=1.1
   // Footprint is the flat panel; rotating it shortens the east-west side by cos(theta).
   const [ex,ey]=downhill(90,rot);offsets=offsets.map(([dx,dy])=>{const e=dx*ex+dy*ey,k=e*(1-Math.cos(tilt*D));return [dx-ex*k,dy-ey*k]})}
  const [ux,uy]=downhill(facing,rot),g=-Math.tan(tilt*D)
  pts=offsets.map(([dx,dy])=>v3(cx+dx,cy+dy,base+lift+g*(ux*dx+uy*dy)))
 }else pts=corners.map(([x,y])=>v3(x,y,roofZ(x,y)+.08))
 const group=new THREE.Group()
 const top=new THREE.BufferGeometry().setFromPoints([pts[0],pts[1],pts[2],pts[0],pts[2],pts[3]])
 top.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,1,1,0,0,1,1,0,1],2));top.computeVertexNormals()
 const glass=new THREE.Mesh(top,glassMat);glass.castShadow=true;glass.receiveShadow=true;glass.userData.panel=index;group.add(glass)
 // Back sheet 4 cm below gives the module visible thickness from low viewing angles.
 const normal=new THREE.Vector3().subVectors(pts[1],pts[0]).cross(new THREE.Vector3().subVectors(pts[3],pts[0])).normalize()
 if(normal.y<0)normal.negate()
 const under=pts.map(v=>v.clone().addScaledVector(normal,-.04))
 const back=new THREE.Mesh(new THREE.BufferGeometry().setFromPoints([under[0],under[2],under[1],under[0],under[3],under[2]]),mats.back);back.castShadow=true;group.add(back)
 if(raised)for(const v of pts){const h=v.y-roofZ(v.x,-v.z);if(h<.12)continue
  const post=new THREE.Mesh(new THREE.BoxGeometry(.05,h,.05),mats.post);post.position.set(v.x,v.y-h/2,v.z);post.castShadow=true;group.add(post)}
 group.userData.glass=glass
 return group
}

type Look='real'|'loss'
type Tool='orbit'|'measure'
type Views={home:()=>void;top:()=>void;fromSun:()=>void;sunArc:()=>void}
type Stage={renderer:THREE.WebGLRenderer;scene:THREE.Scene;camera:THREE.PerspectiveCamera;controls:OrbitControls;content:THREE.Group;decor:THREE.Group;overlay:THREE.Group;sun:THREE.DirectionalLight;ambient:THREE.HemisphereLight;
 framed:number;assets:Record<string,THREE.Texture>;photo?:{src:string;tex:THREE.Texture};views?:Views;glass:THREE.Mesh[]}
const fmt=(n:number,d=1)=>n.toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d})

/** Soft outdoor reflections: a sky dome over a grass-coloured floor, pre-filtered once for PBR materials. */
function outdoorEnvironment(renderer:THREE.WebGLRenderer,sky:THREE.Texture){
 const pmrem=new THREE.PMREMGenerator(renderer),env=new THREE.Scene()
 env.add(new THREE.Mesh(new THREE.SphereGeometry(50,32,16),new THREE.MeshBasicMaterial({map:sky,side:THREE.BackSide})))
 const floor=new THREE.Mesh(new THREE.CircleGeometry(49,32),new THREE.MeshBasicMaterial({color:0x7d8c68}));floor.rotation.x=-Math.PI/2;floor.position.y=-2;env.add(floor)
 const texture=pmrem.fromScene(env,.03).texture;pmrem.dispose();return texture
}

export default function Roof3D({config,obstacles,scene,design,photo,sunDate}:{config:Config;obstacles:Obstacle[];scene:Scene|null;design:Design|null;photo?:string|null;sunDate?:string}){
 const host=useRef<HTMLDivElement>(null),state=useRef<Stage|null>(null)
 const [glError,setGlError]=useState(''),[epoch,setEpoch]=useState(0)
 const [look,setLook]=useState<Look>('real'),[tool,setTool]=useState<Tool>('orbit'),[picked,setPicked]=useState<number|null>(null),[points,setPoints]=useState<THREE.Vector3[]>([])
 const toolRef=useRef<Tool>(tool);toolRef.current=tool
 // One collapsible menu and one help popover keep the scene clear; Esc or a click elsewhere closes them.
 const [open,setOpen]=useState<'menu'|'help'|null>(null),chrome=useRef<HTMLDivElement>(null)
 useEffect(()=>{if(!open)return
  const away=(e:PointerEvent)=>{if(!chrome.current?.contains(e.target as Node))setOpen(null)}
  const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(null)}
  document.addEventListener('pointerdown',away);window.addEventListener('keydown',key)
  return()=>{document.removeEventListener('pointerdown',away);window.removeEventListener('keydown',key)}},[open])
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape'&&!open){setPicked(null);setTool('orbit')}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[open])
 useEffect(()=>{
  const el=host.current!
  // WebGL can be unavailable (old driver, too many contexts, GPU reset). Show a message, never crash the app.
  let renderer:THREE.WebGLRenderer
  try{renderer=new THREE.WebGLRenderer({antialias:true})}catch{setGlError('Trình duyệt chưa tạo được đồ họa 3D (WebGL). Đóng bớt tab có 3D hoặc bật tăng tốc phần cứng rồi tải lại.');return}
  setGlError('')
  const lost=(e:Event)=>{e.preventDefault();setGlError('Mất kết nối đồ họa 3D (trình duyệt đã thu hồi WebGL).')}
  renderer.domElement.addEventListener('webglcontextlost',lost)
  renderer.setPixelRatio(Math.min(2,window.devicePixelRatio));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1
  el.appendChild(renderer.domElement)
  const assets={facade:facadeTexture(PALETTE.plaster),neighbour:facadeTexture(PALETTE.neighbour),plinth:plinthTexture(),cells:cellTexture(),sky:skyTexture(),ground:groundTexture(),concrete:concreteTexture(),sheet:sheetTexture(false),sheetBump:sheetTexture(true)}
  const s=new THREE.Scene();s.background=assets.sky;s.fog=new THREE.Fog(PALETTE.horizon,120,420)
  s.environment=outdoorEnvironment(renderer,assets.sky);s.environmentIntensity=.55
  const camera=new THREE.PerspectiveCamera(42,1,.1,2000),controls=new OrbitControls(camera,renderer.domElement)
  controls.enableDamping=true;controls.maxPolarAngle=Math.PI*.48;controls.minDistance=2
  // normalBias keeps surfaces from shadowing themselves (acne) without detaching contact shadows.
  const ambient=new THREE.HemisphereLight(0xe6f1ff,0x8d9b74,.45),sun=new THREE.DirectionalLight(0xfff1d6,3)
  sun.castShadow=true;sun.shadow.mapSize.set(4096,4096);sun.shadow.bias=-.0002;sun.shadow.normalBias=.04;sun.shadow.radius=3;s.add(ambient,sun,sun.target)
  assets.ground.repeat.set(60,60)
  const ground=new THREE.Mesh(new THREE.CircleGeometry(400,64),new THREE.MeshStandardMaterial({map:assets.ground,roughness:1}))
  ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;s.add(ground)
  const content=new THREE.Group(),decor=new THREE.Group(),overlay=new THREE.Group();s.add(content,decor,overlay)
  state.current={renderer,scene:s,camera,controls,content,decor,overlay,sun,ambient,framed:0,assets,glass:[]}
  const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix()}
  const ro=new ResizeObserver(resize);ro.observe(el);resize()
  // A click (not a drag) picks a panel, or drops a measuring point on whatever surface is under the cursor.
  const ray=new THREE.Raycaster(),down={x:0,y:0}
  const onDown=(e:PointerEvent)=>{down.x=e.clientX;down.y=e.clientY}
  const onUp=(e:PointerEvent)=>{
   if(e.button!==0||Math.hypot(e.clientX-down.x,e.clientY-down.y)>5)return
   const r=renderer.domElement.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera)
   const hit=ray.intersectObject(content,true)[0]
   if(toolRef.current==='measure'){if(hit)setPoints(p=>p.length>=2?[hit.point.clone()]:[...p,hit.point.clone()]);return}
   setPicked(hit&&hit.object.userData.panel!==undefined?hit.object.userData.panel:null)
  }
  renderer.domElement.addEventListener('pointerdown',onDown);renderer.domElement.addEventListener('pointerup',onUp)
  let frame=0;const loop=()=>{frame=requestAnimationFrame(loop);controls.update();renderer.render(s,camera)};loop()
  return()=>{cancelAnimationFrame(frame);ro.disconnect();renderer.domElement.removeEventListener('pointerdown',onDown);renderer.domElement.removeEventListener('webglcontextlost',lost);renderer.domElement.removeEventListener('pointerup',onUp);controls.dispose();Object.values(assets).forEach(t=>t.dispose());s.environment?.dispose();state.current?.photo?.tex.dispose();renderer.dispose();renderer.forceContextLoss();el.removeChild(renderer.domElement);state.current=null}
 },[epoch])
 useEffect(()=>{
  const st=state.current;if(!st)return
  for(const g of [st.content,st.decor]){g.traverse(o=>{if(o instanceof THREE.Mesh||o instanceof THREE.Line)o.geometry.dispose()});g.clear()}
  if(photo&&st.photo?.src!==photo){st.photo?.tex.dispose();const tex=new THREE.TextureLoader().load(photo);tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=8;st.photo={src:photo,tex}}
  const rot=config.north_rotation_deg,faces=(scene?.faces||[]) as Face[],outline=scene?.roof_polygons||[],A=st.assets
  // The roof photo (satellite / drone crop aligned to the roof frame) is kept as-is so the engineer sees the
  // real objects; without a photo, flat faces get weathered concrete and sloped faces a ribbed steel sheet.
  const photoMat=photo&&st.photo?new THREE.MeshStandardMaterial({map:st.photo.tex,roughness:.92}):null
  const concreteMat=new THREE.MeshStandardMaterial({map:A.concrete,roughness:.95})
  const sheetMat=new THREE.MeshStandardMaterial({map:A.sheet,bumpMap:A.sheetBump,bumpScale:3,roughness:.45,metalness:.45})
  const facadeMat=new THREE.MeshStandardMaterial({map:A.facade,roughness:.9,side:THREE.DoubleSide}),plinthMat=new THREE.MeshStandardMaterial({map:A.plinth,roughness:1,side:THREE.DoubleSide})
  const wallMat=new THREE.MeshStandardMaterial({color:PALETTE.parapet,roughness:.9,side:THREE.DoubleSide})
  const parapetMat=new THREE.MeshStandardMaterial({color:PALETTE.parapet,roughness:.9}),capMat=new THREE.MeshStandardMaterial({color:PALETTE.cap,roughness:.8})
  for(const f of faces){
   const sloped=(f.tilt_deg||0)>3
   st.content.add(roofSurface(f,rot,config,photoMat??(sloped?sheetMat:concreteMat),photoMat?'photo':sloped?'sheet':'tile'))
   const {facade,plinth}=wallQuads(f,rot,outline)
   for(const [g,m] of [[facade,facadeMat],[plinth,plinthMat]] as const){const mesh=new THREE.Mesh(g,m);mesh.castShadow=true;mesh.receiveShadow=true;st.content.add(mesh)}
   if(!f.id.startsWith('top-'))st.content.add(parapet(f,rot,outline,parapetMat,capMat))
   if(/^sub\d+-/.test(f.id)){const mesh=new THREE.Mesh(riserWalls(f,rot,faces,config.roof_elevation_m),wallMat);mesh.castShadow=true;mesh.receiveShadow=true;st.content.add(mesh)}
  }
  const levels=new Map((scene?.obstacle_elevations||[]).map(e=>[e.id,e]))
  const obstacleMat=new THREE.MeshStandardMaterial({color:PALETTE.concrete,roughness:.85}),steelMat=new THREE.MeshStandardMaterial({color:PALETTE.steel,roughness:.3,metalness:.7})
  const neighbourMat=new THREE.MeshStandardMaterial({map:A.neighbour,roughness:.9})
  const assetMats:AssetMats={concrete:obstacleMat,steel:steelMat,dark:new THREE.MeshStandardMaterial({color:0x3a4046,roughness:.6}),white:new THREE.MeshStandardMaterial({color:0xeef0ee,roughness:.5}),
   glass:new THREE.MeshPhysicalMaterial({color:0x8fb5c9,roughness:.08,metalness:0,transparent:true,opacity:.75}),trunk:new THREE.MeshStandardMaterial({color:0x6b4f36,roughness:1}),
   leaf:new THREE.MeshStandardMaterial({color:0x4f7d3a,roughness:.9,flatShading:true}),leaf2:new THREE.MeshStandardMaterial({color:0x6b9a45,roughness:.9,flatShading:true}),facade:neighbourMat,cap:capMat}
  for(const o of obstacles){
   const lv=levels.get(o.id),base=lv?lv.base_min_m:o.scope==='neighbor'?0:config.roof_elevation_m
   if(o.scope==='neighbor'&&o.kind){st.content.add(assetModel(o,base,assetMats,()=>prism(footprint(o),base,o.height_m,neighbourMat)));continue}
   if(o.scope==='neighbor'){
    // Neighbour: facade-textured block (UV in metres for one window per bay and floor) with a roof cap.
    const pts=footprint(o),mesh=prism(pts,base,o.height_m,neighbourMat)
    const uv=mesh.geometry.attributes.uv as THREE.BufferAttribute;for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)/BAY,uv.getY(i)/FLOOR)
    st.content.add(mesh,prism(pts,base+o.height_m,.25,capMat))
   }else{
    // On a slope or across a ridge the object keeps its height above the highest roof point under it,
    // on a plinth down to the lowest one, the way a tank sits on a pitched roof; the roof never swallows it.
    const low=lv?lv.roof_min_m:base,seat=lv?lv.roof_max_m:base
    if(seat-low>.01)st.content.add(prism(footprint(o),low,seat-low,obstacleMat))
    st.content.add(assetModel(o,seat,assetMats,()=>prism(footprint(o),seat,o.height_m,o.shape==='ellipse'?steelMat:obstacleMat)))
   }
  }
  // Solar glass: low roughness and the outdoor environment give real sky reflections; no clear-coat
  // (that layer is what made modules look like plastic). Loss view: one flat colour per loss level.
  const glassMat=new THREE.MeshPhysicalMaterial({map:A.cells,roughness:.14,metalness:0,ior:1.5,specularIntensity:.9,side:THREE.DoubleSide})
  const byColour=new Map<string,THREE.Material>()
  const lossMat=(pct:number)=>{const c=lossColor(Math.round(pct*2)/2);if(!byColour.has(c))byColour.set(c,new THREE.MeshStandardMaterial({color:c,roughness:.55,emissive:c,emissiveIntensity:.18,side:THREE.DoubleSide}));return byColour.get(c)!}
  const panelMats:PanelMats={back:new THREE.MeshStandardMaterial({color:0xc9d0d6,roughness:.5,metalness:.4}),post:new THREE.MeshStandardMaterial({color:0x9aa3aa,metalness:.6,roughness:.4})}
  const faceById=new Map(faces.map(f=>[f.id,f]))
  const faceAt=(x:number,y:number)=>faces.find(f=>(f.regions||[]).some(r=>inside([x,y],r.boundary)&&!r.openings.some(h=>inside([x,y],h))))
  st.glass=[]
  ;(design?.panels||[]).forEach((p,i)=>{const id=p.face_id,model=panelModel(p,i,(id&&faceById.get(id))||faceAt(p.x+p.width_m/2,p.y+p.height_m/2),config,scene,look==='loss'?lossMat(p.shading_loss_pct):glassMat,panelMats)
   st.glass[i]=model.userData.glass;st.content.add(model)})
  const box=new THREE.Box3().setFromObject(st.content),size=box.getSize(new THREE.Vector3()),centre=box.getCenter(new THREE.Vector3())
  const reach=Math.max(8,size.length())
  const alt=scene?.sun.altitude_deg??45,az=scene?.sun.azimuth_deg??180,[bx,by]=downhill(az,rot)
  const dir=new THREE.Vector3(bx*Math.cos(alt*D),Math.sin(Math.max(alt,0)*D),-by*Math.cos(alt*D)).normalize()
  st.sun.position.copy(centre).addScaledVector(dir,reach*2);st.sun.target.position.copy(centre);st.sun.intensity=alt>0?3:0;st.ambient.intensity=alt>0?.45:.3
  // Sun disc on its sky position for this hour, the whole day's path, and a ground compass,
  // kept outside `content` so they never change the camera framing.
  const ground=new THREE.Vector3(centre.x,0,centre.z),skyR=Math.max(25,reach*1.5)
  if(alt>0){const disc=sunModel(skyR*.035);disc.position.copy(skyPoint(ground,skyR,az,alt,rot));st.decor.add(disc)}
  if(sunDate)st.decor.add(sunPath(ground,skyR,config.latitude,config.longitude,sunDate,rot))
  st.decor.add(compass(ground,Math.max(size.x,size.z)*.62+4,rot))
  st.controls.maxDistance=skyR*3
  const place=(position:THREE.Vector3,target:THREE.Vector3)=>{st.camera.position.copy(position);st.controls.target.copy(target);st.controls.update()}
  st.views={
   home:()=>place(centre.clone().add(new THREE.Vector3(reach*.55,reach*.62,reach*.8)),centre),
   // Straight down, drawing +Y at the top of the screen like the 2D plan.
   top:()=>place(centre.clone().add(new THREE.Vector3(0,reach*1.25,.001)),centre),
   // Looking along the sun's rays: whatever is hidden from this view is in shade at this hour.
   fromSun:()=>place(centre.clone().addScaledVector(dir,reach*1.3),centre),
   // The sun's daily arc as an observer sees it: from the pole side facing the equator, so east is on
   // the left, the sun rises left and sets right; aim between the building and the sky.
   sunArc:()=>{const [nx,ny]=downhill(config.latitude>=0?0:180,rot),side=new THREE.Vector3(nx,0,-ny).normalize()
    const sunPos=skyPoint(ground,skyR,180,55,rot),aim=ground.clone().lerp(sunPos,.5)
    place(aim.clone().addScaledVector(side,skyR*2.4).add(new THREE.Vector3(0,skyR*.2,0)),aim)},
  }
  const cam=st.sun.shadow.camera;cam.left=-reach;cam.right=reach;cam.top=reach;cam.bottom=-reach;cam.near=.1;cam.far=reach*5;cam.updateProjectionMatrix()
  // Frame from the south-east, above the roof; reframe only when the model size changes a lot
  // (e.g. roof faces arrive after obstacles), so user orbiting is kept on ordinary updates.
  if(!box.isEmpty()&&(st.framed===0||reach>st.framed*1.3||reach<st.framed/1.3)){st.views.home();st.framed=reach}
 },[config,obstacles,scene,design,photo,look,epoch])
 // Selection highlight and measuring line live in their own group, so they never rebuild the model.
 useEffect(()=>{
  const st=state.current;if(!st)return
  st.overlay.traverse(o=>{if(o instanceof THREE.Mesh||o instanceof THREE.Line)o.geometry.dispose()});st.overlay.clear()
  const glass=picked!==null?st.glass[picked]:undefined
  if(glass){const mark=new THREE.Mesh(glass.geometry.clone(),new THREE.MeshBasicMaterial({color:0xffc928,transparent:true,opacity:.55,depthTest:false,side:THREE.DoubleSide}));mark.renderOrder=5;st.overlay.add(mark)
   const edge=new THREE.LineSegments(new THREE.EdgesGeometry(glass.geometry),new THREE.LineBasicMaterial({color:0xff9d00,depthTest:false}));edge.renderOrder=6;st.overlay.add(edge)}
  const dot=new THREE.MeshBasicMaterial({color:0xff5a1f,depthTest:false})
  for(const p of points){const m=new THREE.Mesh(new THREE.SphereGeometry(.07,16,8),dot);m.position.copy(p);m.renderOrder=7;st.overlay.add(m)}
  if(points.length===2){const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0xff5a1f,depthTest:false}));line.renderOrder=7;st.overlay.add(line)}
 },[picked,points,design,config,scene,look,epoch])
 useEffect(()=>{if(picked!==null&&!design?.panels[picked])setPicked(null)},[design,picked])
 useEffect(()=>{if(tool==='orbit')setPoints([]);else setPicked(null)},[tool])

 function snapshot(){
  const st=state.current;if(!st)return
  const ratio=st.renderer.getPixelRatio(),{clientWidth:w,clientHeight:h}=host.current!
  st.renderer.setPixelRatio(Math.max(2,ratio));st.renderer.setSize(w,h,false);st.renderer.render(st.scene,st.camera)
  const url=st.renderer.domElement.toDataURL('image/png')
  st.renderer.setPixelRatio(ratio);st.renderer.setSize(w,h,false)
  const a=document.createElement('a');a.href=url;a.download=`SolarOpt-phoi-canh-${(config.project_name||'du-an').replace(/[^\p{L}\p{N}]+/gu,'-')}.png`;a.click()
 }
 const sun=scene?.sun,panel=picked!==null?design?.panels[picked]:undefined,panels=design?.panels||[]
 const mean=panels.length?panels.reduce((s,p)=>s+p.annual_energy_kwh,0)/panels.length:0
 const rank=panel?panels.filter(p=>p.annual_energy_kwh>panel.annual_energy_kwh).length+1:0
 const faceName=panel?.face_id?(scene?.faces?.find(f=>f.id===panel.face_id)?.label??panel.face_id):'Mái'
 const span=points.length===2?{d:points[0].distanceTo(points[1]),flat:Math.hypot(points[1].x-points[0].x,points[1].z-points[0].z),rise:Math.abs(points[1].y-points[0].y)}:null
 return <div className="roof-3d">
  {glError&&<div className="roof-3d-error" role="alert"><p>{glError}</p><button type="button" className="button secondary" onClick={()=>setEpoch(e=>e+1)}>Tải lại 3D</button></div>}
  <div ref={host} className={'roof-3d-view'+(tool==='measure'?' measuring':'')} role="img" aria-label="Phối cảnh 3D mái nhà, vật cản, tấm pin và bóng theo giờ"/>
  <div ref={chrome} className="roof-3d-chrome">
   <div className="roof-3d-menu">
    {tool==='measure'&&<button type="button" className="roof-3d-chip" onClick={()=>setTool('orbit')} title="Thoát chế độ đo (Esc)">Đang đo <span aria-hidden="true">×</span></button>}
    <button type="button" className={'roof-3d-toggle'+(open==='menu'?' on':'')} aria-expanded={open==='menu'} aria-haspopup="menu" aria-label="Góc nhìn và công cụ 3D" onClick={()=>setOpen(o=>o==='menu'?null:'menu')}><Icon name="layers" size={15}/><span className="label">Góc nhìn & công cụ</span><span className="caret" aria-hidden="true">▾</span></button>
    {open==='menu'&&<div className="roof-3d-pop" role="menu">
     <p>Góc nhìn</p>
     <div className="views">{([['home','Tổng thể','Góc nhìn mặc định từ Đông Nam'],['top','Từ trên xuống','Nhìn thẳng xuống, giống mặt bằng'],['fromSun','Từ mặt trời','Nhìn theo tia nắng: phần không thấy được là phần đang bị che'],['sunArc','Đường mặt trời','Toàn cảnh đường đi của mặt trời trong ngày']] as const).map(([id,label,hint])=><button key={id} type="button" role="menuitem" title={hint} disabled={id==='fromSun'&&(!sun||sun.altitude_deg<=0)} onClick={()=>{state.current?.views?.[id]();setOpen(null)}}>{label}</button>)}</div>
     <p>Màu tấm pin</p>
     <div className="seg" role="group" aria-label="Kiểu hiển thị tấm pin"><button type="button" className={look==='real'?'on':''} onClick={()=>setLook('real')}>Phối cảnh</button><button type="button" className={look==='loss'?'on':''} disabled={!panels.length} onClick={()=>setLook('loss')}>Tổn thất bóng</button></div>
     <p>Công cụ</p>
     <div className="views"><button type="button" role="menuitemcheckbox" aria-checked={tool==='measure'} className={'item'+(tool==='measure'?' on':'')} title="Bấm hai điểm bất kỳ trên mô hình" onClick={()=>{setTool(t=>t==='measure'?'orbit':'measure');setOpen(null)}}>Đo khoảng cách</button>
     <button type="button" role="menuitem" className="item" title="Ảnh độ phân giải cao, đúng góc đang xem" onClick={()=>{snapshot();setOpen(null)}}>Tải ảnh PNG</button></div>
    </div>}
   </div>
   <div className="roof-3d-help">
    <button type="button" className={'roof-3d-round'+(open==='help'?' on':'')} aria-label="Hướng dẫn thao tác 3D" aria-expanded={open==='help'} onClick={()=>setOpen(o=>o==='help'?null:'help')}>?</button>
    {open==='help'&&<div className="roof-3d-pop up" role="dialog" aria-label="Hướng dẫn thao tác">
     <ul><li><b>Kéo</b> để xoay · <b>chuột phải kéo</b> để dịch · <b>cuộn</b> để phóng</li><li><b>Bấm một tấm</b> để xem sản lượng và bóng của tấm đó</li><li><b>Esc</b> bỏ chọn hoặc thoát chế độ đo</li></ul>
     {(sun||photo)&&<small>{sun?`Nắng lúc này: cao ${sun.altitude_deg.toFixed(0)}°, hướng ${sun.azimuth_deg.toFixed(0)}°`:''}{sun&&photo?' · ':''}{photo?'Mái dùng ảnh chụp thật':''}</small>}
    </div>}
   </div>
  </div>
  {look==='loss'&&<div className="roof-3d-legend" aria-label="Thang tổn thất bóng cả năm"><span>Tổn thất bóng</span><b style={{background:`linear-gradient(90deg,${[0,2.5,5,7.5,10].map(v=>lossColor(v)).join(',')})`}}/><em>0%</em><em>≥ 10%</em></div>}
  {panel&&<div className="roof-3d-card" role="status"><button type="button" className="x" onClick={()=>setPicked(null)} aria-label="Bỏ chọn tấm">×</button>
   <strong>{panelLabel(picked!)}<span style={{background:lossColor(panel.shading_loss_pct)}}>{fmt(panel.shading_loss_pct)}% bóng</span></strong>
   <dl><dt>Điện năng</dt><dd>{fmt(panel.annual_energy_kwh,0)} kWh/năm · {mean?(panel.annual_energy_kwh>=mean?'+':'')+fmt((panel.annual_energy_kwh/mean-1)*100):'0'}% so với trung bình</dd>
    <dt>Xếp hạng</dt><dd>{rank}/{panels.length} theo sản lượng</dd>
    <dt>Vị trí</dt><dd>{faceName} · X {fmt(panel.x,2)} · Y {fmt(panel.y,2)} m · xoay {fmt(panel.rotation_deg||0,0)}°</dd></dl>
   {panel.shading_loss_pct>=5&&<p>Tấm này mất nhiều điện vì bóng che. Kéo thanh giờ sang sáng hoặc chiều rồi chọn “Từ mặt trời” để thấy vật gây bóng.</p>}
  </div>}
  {tool==='measure'&&<div className="roof-3d-card measure" role="status"><strong>Đo khoảng cách</strong>
   {span?<dl><dt>Khoảng cách</dt><dd>{fmt(span.d,2)} m</dd><dt>Theo phương ngang</dt><dd>{fmt(span.flat,2)} m</dd><dt>Chênh cao</dt><dd>{fmt(span.rise,2)} m</dd></dl>
    :<p>{points.length?'Bấm điểm thứ hai.':'Bấm hai điểm bất kỳ trên mái, vật cản hoặc tấm pin.'}</p>}</div>}
 </div>
}
