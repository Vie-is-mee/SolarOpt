import {useEffect,useRef} from 'react'
import * as THREE from 'three'
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js'
import type {Config,Design,Obstacle,Scene} from '../studioTypes'
import {footprint} from '../editorGeometry'
import {panelCorners} from '../layoutMeasurements'

type Face=NonNullable<Scene['faces']>[number]&{azimuth_deg?:number;origin?:number[];regions?:{boundary:number[][];openings:number[][][]}[];mount?:string|null;mount_tilt?:number;mount_azimuth?:number}
const D=Math.PI/180
// Drawing (x right, y up the page) -> three (X right, Y up in the air, Z towards the viewer).
const v3=(x:number,y:number,z:number)=>new THREE.Vector3(x,z,-y)
/** Downhill unit vector in drawing coordinates for a compass azimuth, given the drawing's north rotation. */
const downhill=(azimuth:number,rot:number)=>{const b=(azimuth-rot)*D;return [Math.sin(b),Math.cos(b)]}
/** Same plane equation as the backend (geometry.surface_z): elevation at the face origin plus slope. */
function zOn(face:Face,x:number,y:number,rot:number){
 const [ux,uy]=downhill(face.azimuth_deg??180,rot),g=-Math.tan((face.tilt_deg||0)*D),[ox,oy]=face.origin||[0,0]
 return face.elevation_m+g*ux*(x-ox)+g*uy*(y-oy)
}
const inside=(pt:number[],ring:number[][])=>{let c=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const [xi,yi]=ring[i],[xj,yj]=ring[j];if((yi>pt[1])!==(yj>pt[1])&&pt[0]<(xj-xi)*(pt[1]-yi)/(yj-yi)+xi)c=!c}return c}

function faceMesh(face:Face,rot:number,material:THREE.Material){
 const group=new THREE.Group()
 for(const region of face.regions||face.polygons.map(p=>({boundary:p,openings:[]}))){
  const shape=new THREE.Shape(region.boundary.map(([x,y])=>new THREE.Vector2(x,y)))
  region.openings.forEach(h=>shape.holes.push(new THREE.Path(h.map(([x,y])=>new THREE.Vector2(x,y)))))
  const geo=new THREE.ShapeGeometry(shape),pos=geo.attributes.position as THREE.BufferAttribute
  for(let i=0;i<pos.count;i++){const x=pos.getX(i),y=pos.getY(i);pos.setXYZ(i,x,zOn(face,x,y,rot),-y)}
  geo.computeVertexNormals()
  const mesh=new THREE.Mesh(geo,material);mesh.receiveShadow=true;mesh.castShadow=true;group.add(mesh)
  // Walls from each face edge down to the ground: building sides and steps between roof levels.
  const ring=region.boundary,wall:number[]=[]
  for(let i=0;i<ring.length-1;i++){const [ax,ay]=ring[i],[bx,by]=ring[i+1],za=zOn(face,ax,ay,rot),zb=zOn(face,bx,by,rot)
   wall.push(ax,0,-ay,bx,0,-by,bx,zb,-by,ax,0,-ay,bx,zb,-by,ax,za,-ay)}
  const wg=new THREE.BufferGeometry();wg.setAttribute('position',new THREE.Float32BufferAttribute(wall,3));wg.computeVertexNormals()
  const wm=new THREE.Mesh(wg,new THREE.MeshStandardMaterial({color:0xe9e4d8,side:THREE.DoubleSide,roughness:.95}));wm.receiveShadow=true;wm.castShadow=true;group.add(wm)
 }
 return group
}

function prism(points:{x:number;y:number}[],base:number,height:number,color:number,opacity=1){
 const shape=new THREE.Shape(points.map(p=>new THREE.Vector2(p.x,p.y)))
 const geo=new THREE.ExtrudeGeometry(shape,{depth:Math.max(.02,height),bevelEnabled:false})
 geo.rotateX(-Math.PI/2);geo.translate(0,base,0)
 const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color,roughness:.85,transparent:opacity<1,opacity}))
 mesh.castShadow=true;mesh.receiveShadow=true;return mesh
}

/** Tracker rotation about a N-S axis: ideal angle tan(theta)=tan(zenith)*sin(az-180), clamped. */
function trackerAngle(sunAz:number,sunAlt:number,max:number){
 if(sunAlt<=0)return 0
 const theta=Math.atan(Math.tan((90-sunAlt)*D)*Math.sin((sunAz-180)*D))/D
 return Math.max(-max,Math.min(max,theta))
}

function panelMesh(p:Design['panels'][number],face:Face|undefined,cfg:Config,scene:Scene|null,material:THREE.Material){
 const rot=cfg.north_rotation_deg,corners=panelCorners(p).map(c=>[c.x,c.y]),cx=p.x+p.width_m/2,cy=p.y+p.height_m/2
 const base=face?zOn(face,cx,cy,rot):cfg.roof_elevation_m
 let pts:THREE.Vector3[]
 if(face?.mount==='tilted_rack'||face?.mount==='tracker'){
  let tilt:number,facing:number,lift:number,offsets=corners.map(([x,y])=>[x-cx,y-cy])
  if(face.mount==='tilted_rack'){tilt=face.mount_tilt??15;facing=face.mount_azimuth??180
   const [ux,uy]=downhill(facing,rot),along=Math.max(...offsets.map(([dx,dy])=>dx*ux+dy*uy))*2   // plan length down the slope
   lift=.25+along*Math.tan(tilt*D)/2
  }else{const theta=trackerAngle(scene?.sun.azimuth_deg??180,scene?.sun.altitude_deg??0,cfg.tracker_max_angle_deg??55)
   tilt=Math.abs(theta);facing=theta<0?90:270;lift=1
   // Footprint is the flat panel; rotating it shortens the east-west side by cos(theta).
   const [ex,ey]=downhill(90,rot);offsets=offsets.map(([dx,dy])=>{const e=dx*ex+dy*ey,k=e*(1-Math.cos(tilt*D));return [dx-ex*k,dy-ey*k]})}
  const [ux,uy]=downhill(facing,rot),g=-Math.tan(tilt*D)
  pts=offsets.map(([dx,dy])=>v3(cx+dx,cy+dy,base+lift+g*(ux*dx+uy*dy)))
 }else pts=corners.map(([x,y])=>v3(x,y,(face?zOn(face,x,y,rot):base)+.06))
 const geo=new THREE.BufferGeometry().setFromPoints([pts[0],pts[1],pts[2],pts[0],pts[2],pts[3]]);geo.computeVertexNormals()
 const mesh=new THREE.Mesh(geo,material);mesh.castShadow=true;mesh.receiveShadow=true
 const edge=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0xcfe0ea}))
 const group=new THREE.Group();group.add(mesh,edge);return group
}

export default function Roof3D({config,obstacles,scene,design}:{config:Config;obstacles:Obstacle[];scene:Scene|null;design:Design|null}){
 const host=useRef<HTMLDivElement>(null),state=useRef<{renderer:THREE.WebGLRenderer;camera:THREE.PerspectiveCamera;controls:OrbitControls;scene:THREE.Scene;content:THREE.Group;sun:THREE.DirectionalLight;ambient:THREE.HemisphereLight;framed:number}|null>(null)
 useEffect(()=>{
  const el=host.current!,renderer=new THREE.WebGLRenderer({antialias:true})
  renderer.setPixelRatio(Math.min(2,window.devicePixelRatio));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap
  el.appendChild(renderer.domElement)
  const s=new THREE.Scene();s.background=new THREE.Color(0xdfeaf2)
  const camera=new THREE.PerspectiveCamera(45,1,.1,2000),controls=new OrbitControls(camera,renderer.domElement)
  controls.enableDamping=true;controls.maxPolarAngle=Math.PI*.49
  const ambient=new THREE.HemisphereLight(0xffffff,0xb7c2a8,1.0),sun=new THREE.DirectionalLight(0xfff4dc,2.6)
  // normalBias keeps surfaces from shadowing themselves (acne) without detaching contact shadows.
  sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.bias=-.0002;sun.shadow.normalBias=.04;s.add(ambient,sun,sun.target)
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(600,600),new THREE.MeshStandardMaterial({color:0xcfdcc4,roughness:1}))
  ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;s.add(ground)
  const content=new THREE.Group();s.add(content)
  state.current={renderer,camera,controls,scene:s,content,sun,ambient,framed:0}
  const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix()}
  const ro=new ResizeObserver(resize);ro.observe(el);resize()
  let frame=0;const loop=()=>{frame=requestAnimationFrame(loop);controls.update();renderer.render(s,camera)};loop()
  return()=>{cancelAnimationFrame(frame);ro.disconnect();controls.dispose();renderer.dispose();el.removeChild(renderer.domElement);state.current=null}
 },[])
 useEffect(()=>{
  const st=state.current;if(!st)return
  st.content.traverse(o=>{if(o instanceof THREE.Mesh||o instanceof THREE.Line){o.geometry.dispose()}});st.content.clear()
  const rot=config.north_rotation_deg,faces=(scene?.faces||[]) as Face[]
  const roofMat=new THREE.MeshStandardMaterial({color:0xb9c3b4,roughness:.9}),panelMat=new THREE.MeshStandardMaterial({color:0x234f73,roughness:.35,metalness:.25,side:THREE.DoubleSide})
  faces.forEach(f=>st.content.add(faceMesh(f,rot,roofMat)))
  const levels=new Map((scene?.obstacle_elevations||[]).map(e=>[e.id,e]))
  for(const o of obstacles){
   const lv=levels.get(o.id),base=lv?lv.base_min_m:o.scope==='neighbor'?0:config.roof_elevation_m
   st.content.add(prism(footprint(o),base,o.height_m,o.scope==='neighbor'?0xa9b5ae:o.top_installable?0xd9cfa9:0xcabfaa,o.scope==='neighbor'?.92:1))
  }
  const faceById=new Map(faces.map(f=>[f.id,f]))
  const faceAt=(x:number,y:number)=>faces.find(f=>(f.regions||[]).some(r=>inside([x,y],r.boundary)&&!r.openings.some(h=>inside([x,y],h))))
  for(const p of design?.panels||[]){const id=(p as {face_id?:string}).face_id;st.content.add(panelMesh(p,(id&&faceById.get(id))||faceAt(p.x+p.width_m/2,p.y+p.height_m/2),config,scene,panelMat))}
  // Sun: direction from compass azimuth/altitude, drawn relative to the drawing's north.
  const box=new THREE.Box3().setFromObject(st.content),size=box.getSize(new THREE.Vector3()),centre=box.getCenter(new THREE.Vector3())
  const reach=Math.max(8,size.length())
  const alt=scene?.sun.altitude_deg??45,az=scene?.sun.azimuth_deg??180,[bx,by]=downhill(az,rot)
  const dir=new THREE.Vector3(bx*Math.cos(alt*D),Math.sin(Math.max(alt,0)*D),-by*Math.cos(alt*D)).normalize()
  st.sun.position.copy(centre).addScaledVector(dir,reach*2);st.sun.target.position.copy(centre);st.sun.intensity=alt>0?2.6:0;st.ambient.intensity=alt>0?1.0:.5
  const cam=st.sun.shadow.camera;cam.left=-reach;cam.right=reach;cam.top=reach;cam.bottom=-reach;cam.near=.1;cam.far=reach*5;cam.updateProjectionMatrix()
  // Frame from the south-east, above the roof; reframe only when the model size changes a lot
  // (e.g. roof faces arrive after obstacles), so user orbiting is kept on ordinary updates.
  if(!box.isEmpty()&&(st.framed===0||reach>st.framed*1.3||reach<st.framed/1.3)){st.camera.position.copy(centre).add(new THREE.Vector3(reach*.5,reach*.75,reach*.8));st.controls.target.copy(centre);st.controls.update();st.framed=reach}
 },[config,obstacles,scene,design])
 const sun=scene?.sun
 return <div className="roof-3d">
  <div ref={host} className="roof-3d-view" role="img" aria-label="Phối cảnh 3D mái nhà, vật cản, tấm pin và bóng theo giờ"/>
  <div className="roof-3d-info">3D · kéo để xoay, cuộn để phóng, chuột phải để dịch{sun?` · mặt trời cao ${sun.altitude_deg.toFixed(0)}°, phương vị ${sun.azimuth_deg.toFixed(0)}°`:''}</div>
 </div>
}
