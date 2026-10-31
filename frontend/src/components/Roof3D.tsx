import {useEffect,useRef} from 'react'
import * as THREE from 'three'
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js'
import type {Config,Design,Obstacle,Scene} from '../studioTypes'
import {footprint} from '../editorGeometry'
import {panelCorners} from '../layoutMeasurements'
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
/** Monocrystalline cells (6 x 10) under glass with thin silver busbars; the aluminium frame is drawn separately. */
const cellTexture=()=>canvasTexture(240,400,g=>{
 const grad=g.createLinearGradient(0,0,240,400);grad.addColorStop(0,'#1b3550');grad.addColorStop(1,'#0f2238');g.fillStyle=grad;g.fillRect(0,0,240,400)
 g.strokeStyle='rgba(205,220,235,.55)';g.lineWidth=2
 for(let i=1;i<6;i++){g.beginPath();g.moveTo(i*40,0);g.lineTo(i*40,400);g.stroke()}
 for(let j=1;j<10;j++){g.beginPath();g.moveTo(0,j*40);g.lineTo(240,j*40);g.stroke()}
 g.strokeStyle='rgba(205,220,235,.18)';g.lineWidth=1
 for(let i=0;i<6;i++)for(const k of [13,27]){g.beginPath();g.moveTo(i*40+k,0);g.lineTo(i*40+k,400);g.stroke()}
},false)
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
function roofSurface(face:Face,rot:number,cfg:Config,material:THREE.Material){
 const group=new THREE.Group()
 for(const region of face.regions||face.polygons.map(p=>({boundary:p,openings:[]}))){
  const shape=new THREE.Shape(region.boundary.map(([x,y])=>new THREE.Vector2(x,y)))
  region.openings.forEach(h=>shape.holes.push(new THREE.Path(h.map(([x,y])=>new THREE.Vector2(x,y)))))
  const geo=new THREE.ShapeGeometry(shape),pos=geo.attributes.position as THREE.BufferAttribute,uv=geo.attributes.uv as THREE.BufferAttribute
  for(let i=0;i<pos.count;i++){const x=pos.getX(i),y=pos.getY(i);pos.setXYZ(i,x,zOn(face,x,y,rot)+.005,-y);uv.setXY(i,x/cfg.roof_width_m,y/cfg.roof_height_m)}
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

type PanelMats={glass:THREE.Material;back:THREE.Material;frame:THREE.LineBasicMaterial;post:THREE.Material}
function panelModel(p:Design['panels'][number],face:Face|undefined,cfg:Config,scene:Scene|null,mats:PanelMats){
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
 const glass=new THREE.Mesh(top,mats.glass);glass.castShadow=true;glass.receiveShadow=true;group.add(glass)
 // Back sheet 4 cm below gives the module visible thickness from low viewing angles.
 const normal=new THREE.Vector3().subVectors(pts[1],pts[0]).cross(new THREE.Vector3().subVectors(pts[3],pts[0])).normalize()
 if(normal.y<0)normal.negate()
 const under=pts.map(v=>v.clone().addScaledVector(normal,-.04))
 const back=new THREE.Mesh(new THREE.BufferGeometry().setFromPoints([under[0],under[2],under[1],under[0],under[3],under[2]]),mats.back);back.castShadow=true;group.add(back)
 group.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),mats.frame))
 if(raised)for(const v of pts){const h=v.y-roofZ(v.x,-v.z);if(h<.12)continue
  const post=new THREE.Mesh(new THREE.BoxGeometry(.05,h,.05),mats.post);post.position.set(v.x,v.y-h/2,v.z);post.castShadow=true;group.add(post)}
 return group
}

export default function Roof3D({config,obstacles,scene,design,photo,sunDate}:{config:Config;obstacles:Obstacle[];scene:Scene|null;design:Design|null;photo?:string|null;sunDate?:string}){
 const host=useRef<HTMLDivElement>(null)
 const state=useRef<{renderer:THREE.WebGLRenderer;camera:THREE.PerspectiveCamera;controls:OrbitControls;content:THREE.Group;decor:THREE.Group;sun:THREE.DirectionalLight;sunView?:()=>void;ambient:THREE.HemisphereLight;framed:number;assets:Record<string,THREE.Texture>;photo?:{src:string;tex:THREE.Texture}}|null>(null)
 useEffect(()=>{
  const el=host.current!,renderer=new THREE.WebGLRenderer({antialias:true})
  renderer.setPixelRatio(Math.min(2,window.devicePixelRatio));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05
  el.appendChild(renderer.domElement)
  const assets={facade:facadeTexture(PALETTE.plaster),neighbour:facadeTexture(PALETTE.neighbour),plinth:plinthTexture(),cells:cellTexture(),sky:skyTexture(),ground:groundTexture()}
  const s=new THREE.Scene();s.background=assets.sky;s.fog=new THREE.Fog(PALETTE.horizon,120,420)
  const camera=new THREE.PerspectiveCamera(42,1,.1,2000),controls=new OrbitControls(camera,renderer.domElement)
  controls.enableDamping=true;controls.maxPolarAngle=Math.PI*.48;controls.minDistance=4
  // normalBias keeps surfaces from shadowing themselves (acne) without detaching contact shadows.
  const ambient=new THREE.HemisphereLight(0xe6f1ff,0x8d9b74,.9),sun=new THREE.DirectionalLight(0xfff1d6,3)
  sun.castShadow=true;sun.shadow.mapSize.set(4096,4096);sun.shadow.bias=-.0002;sun.shadow.normalBias=.04;sun.shadow.radius=3;s.add(ambient,sun,sun.target)
  assets.ground.repeat.set(60,60)
  const ground=new THREE.Mesh(new THREE.CircleGeometry(400,64),new THREE.MeshStandardMaterial({map:assets.ground,roughness:1}))
  ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;s.add(ground)
  const content=new THREE.Group(),decor=new THREE.Group();s.add(content,decor)
  state.current={renderer,camera,controls,content,decor,sun,ambient,framed:0,assets}
  const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix()}
  const ro=new ResizeObserver(resize);ro.observe(el);resize()
  let frame=0;const loop=()=>{frame=requestAnimationFrame(loop);controls.update();renderer.render(s,camera)};loop()
  return()=>{cancelAnimationFrame(frame);ro.disconnect();controls.dispose();Object.values(assets).forEach(t=>t.dispose());state.current?.photo?.tex.dispose();renderer.dispose();el.removeChild(renderer.domElement);state.current=null}
 },[])
 useEffect(()=>{
  const st=state.current;if(!st)return
  for(const g of [st.content,st.decor]){g.traverse(o=>{if(o instanceof THREE.Mesh||o instanceof THREE.Line)o.geometry.dispose()});g.clear()}
  if(photo&&st.photo?.src!==photo){st.photo?.tex.dispose();const tex=new THREE.TextureLoader().load(photo);tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=8;st.photo={src:photo,tex}}
  const rot=config.north_rotation_deg,faces=(scene?.faces||[]) as Face[],outline=scene?.roof_polygons||[],A=st.assets
  // The roof photo (satellite / drone crop aligned to the roof frame) is kept as-is on a flat roof so the
  // engineer sees the real objects; without a photo a neutral concrete finish is used.
  const roofMat=photo&&st.photo?new THREE.MeshStandardMaterial({map:st.photo.tex,roughness:.92}):new THREE.MeshStandardMaterial({color:PALETTE.concrete,roughness:.95})
  const facadeMat=new THREE.MeshStandardMaterial({map:A.facade,roughness:.9,side:THREE.DoubleSide}),plinthMat=new THREE.MeshStandardMaterial({map:A.plinth,roughness:1,side:THREE.DoubleSide})
  const parapetMat=new THREE.MeshStandardMaterial({color:PALETTE.parapet,roughness:.9}),capMat=new THREE.MeshStandardMaterial({color:PALETTE.cap,roughness:.8})
  for(const f of faces){
   st.content.add(roofSurface(f,rot,config,roofMat))
   const {facade,plinth}=wallQuads(f,rot,outline)
   for(const [g,m] of [[facade,facadeMat],[plinth,plinthMat]] as const){const mesh=new THREE.Mesh(g,m);mesh.castShadow=true;mesh.receiveShadow=true;st.content.add(mesh)}
   if(!f.id.startsWith('top-'))st.content.add(parapet(f,rot,outline,parapetMat,capMat))
  }
  const levels=new Map((scene?.obstacle_elevations||[]).map(e=>[e.id,e]))
  const obstacleMat=new THREE.MeshStandardMaterial({color:PALETTE.concrete,roughness:.85}),steelMat=new THREE.MeshStandardMaterial({color:PALETTE.steel,roughness:.35,metalness:.45})
  const neighbourMat=new THREE.MeshStandardMaterial({map:A.neighbour,roughness:.9})
  const assetMats:AssetMats={concrete:obstacleMat,steel:steelMat,dark:new THREE.MeshStandardMaterial({color:0x3a4046,roughness:.6}),white:new THREE.MeshStandardMaterial({color:0xeef0ee,roughness:.5}),
   glass:new THREE.MeshPhysicalMaterial({color:0x8fb5c9,roughness:.1,metalness:.1,transparent:true,opacity:.7}),trunk:new THREE.MeshStandardMaterial({color:0x6b4f36,roughness:1}),
   leaf:new THREE.MeshStandardMaterial({color:0x4f7d3a,roughness:.9,flatShading:true}),leaf2:new THREE.MeshStandardMaterial({color:0x6b9a45,roughness:.9,flatShading:true}),facade:neighbourMat,cap:capMat}
  for(const o of obstacles){
   const lv=levels.get(o.id),base=lv?lv.base_min_m:o.scope==='neighbor'?0:config.roof_elevation_m
   if(o.scope==='neighbor'&&o.kind){st.content.add(assetModel(o,base,assetMats,()=>prism(footprint(o),base,o.height_m,neighbourMat)));continue}
   if(o.scope==='neighbor'){
    // Neighbour: facade-textured block (UV in metres for one window per bay and floor) with a roof cap.
    const pts=footprint(o),mesh=prism(pts,base,o.height_m,neighbourMat)
    const uv=mesh.geometry.attributes.uv as THREE.BufferAttribute;for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)/BAY,uv.getY(i)/FLOOR)
    st.content.add(mesh,prism(pts,base+o.height_m,.25,capMat))
   }else st.content.add(assetModel(o,base,assetMats,()=>prism(footprint(o),base,o.height_m,o.shape==='ellipse'?steelMat:obstacleMat)))
  }
  const panelMats:PanelMats={glass:new THREE.MeshPhysicalMaterial({map:A.cells,roughness:.22,metalness:.25,clearcoat:1,clearcoatRoughness:.08,side:THREE.DoubleSide}),
   back:new THREE.MeshStandardMaterial({color:0xd8dde2,roughness:.7}),frame:new THREE.LineBasicMaterial({color:0xd5dde4}),post:new THREE.MeshStandardMaterial({color:0x9aa3aa,metalness:.6,roughness:.4})}
  const faceById=new Map(faces.map(f=>[f.id,f]))
  const faceAt=(x:number,y:number)=>faces.find(f=>(f.regions||[]).some(r=>inside([x,y],r.boundary)&&!r.openings.some(h=>inside([x,y],h))))
  for(const p of design?.panels||[]){const id=(p as {face_id?:string}).face_id;st.content.add(panelModel(p,(id&&faceById.get(id))||faceAt(p.x+p.width_m/2,p.y+p.height_m/2),config,scene,panelMats))}
  const box=new THREE.Box3().setFromObject(st.content),size=box.getSize(new THREE.Vector3()),centre=box.getCenter(new THREE.Vector3())
  const reach=Math.max(8,size.length())
  const alt=scene?.sun.altitude_deg??45,az=scene?.sun.azimuth_deg??180,[bx,by]=downhill(az,rot)
  const dir=new THREE.Vector3(bx*Math.cos(alt*D),Math.sin(Math.max(alt,0)*D),-by*Math.cos(alt*D)).normalize()
  st.sun.position.copy(centre).addScaledVector(dir,reach*2);st.sun.target.position.copy(centre);st.sun.intensity=alt>0?3:0;st.ambient.intensity=alt>0?.9:.45
  // Sun disc on its sky position for this hour, the whole day's path, and a ground compass,
  // kept outside `content` so they never change the camera framing.
  const ground=new THREE.Vector3(centre.x,0,centre.z),skyR=Math.max(25,reach*1.5)
  if(alt>0){const disc=sunModel(skyR*.035);disc.position.copy(skyPoint(ground,skyR,az,alt,rot));st.decor.add(disc)}
  if(sunDate)st.decor.add(sunPath(ground,skyR,config.latitude,config.longitude,sunDate,rot))
  st.decor.add(compass(ground,Math.max(size.x,size.z)*.62+4,rot))
  st.controls.maxDistance=skyR*3
  // View of the sun's daily arc as an observer sees it: from the pole side facing the equator, so east
  // is on the left, the sun rises left and sets right; aim between the building and the sky.
  st.sunView=()=>{const [nx,ny]=downhill(config.latitude>=0?0:180,rot),side=new THREE.Vector3(nx,0,-ny).normalize()   // stand on the pole side, face the sun's arc
   const sunPos=skyPoint(ground,skyR,180,55,rot),aim=ground.clone().lerp(sunPos,.5)
   st.camera.position.copy(aim).addScaledVector(side,skyR*2.4).add(new THREE.Vector3(0,skyR*.2,0));st.controls.target.copy(aim);st.controls.update()}
  const cam=st.sun.shadow.camera;cam.left=-reach;cam.right=reach;cam.top=reach;cam.bottom=-reach;cam.near=.1;cam.far=reach*5;cam.updateProjectionMatrix()
  // Frame from the south-east, above the roof; reframe only when the model size changes a lot
  // (e.g. roof faces arrive after obstacles), so user orbiting is kept on ordinary updates.
  if(!box.isEmpty()&&(st.framed===0||reach>st.framed*1.3||reach<st.framed/1.3)){st.camera.position.copy(centre).add(new THREE.Vector3(reach*.55,reach*.62,reach*.8));st.controls.target.copy(centre);st.controls.update();st.framed=reach}
 },[config,obstacles,scene,design,photo])
 const sun=scene?.sun
 return <div className="roof-3d">
  <div ref={host} className="roof-3d-view" role="img" aria-label="Phối cảnh 3D mái nhà, vật cản, tấm pin và bóng theo giờ"/>
  <button type="button" className="roof-3d-sun" onClick={()=>state.current?.sunView?.()}>☀ Toàn cảnh mặt trời</button>
  <div className="roof-3d-info">{photo?'Mái dùng ảnh chụp thật · ':''}Kéo để xoay · cuộn để phóng · chuột phải để dịch{sun?` · nắng ${sun.altitude_deg.toFixed(0)}°, hướng ${sun.azimuth_deg.toFixed(0)}°`:''}</div>
 </div>
}
