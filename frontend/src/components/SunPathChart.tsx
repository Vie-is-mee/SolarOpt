import {useMemo} from 'react'
import type {Config} from '../studioTypes'
import {DIRECTIONS,dayPath,directionName,northSunSpan,sideFacing} from '../orientation'
import {solarPosition} from '../solarPosition'

const n=(v:number,d=0)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
const day=(s:string)=>{const [,m,d]=s.split('-');return `${Number(d)}/${Number(m)}`}
const C=170,R=140
const at=(alt:number,az:number)=>{const r=R*(90-Math.max(0,alt))/90,a=az*Math.PI/180;return [C+r*Math.sin(a),C-r*Math.cos(a)]}

/** The house on the compass and the sun's daily paths over it at this latitude and longitude:
 * the June and December solstices, the March equinox and the day being simulated. */
export function SunPathChart({config,date,hour,onRotate}:{config:Config;date:string;hour:number;onRotate:(deg:number)=>void}){
 const year=Number(date.slice(0,4))||new Date().getFullYear()
 const lat=config.latitude,lon=config.longitude,rot=config.north_rotation_deg
 const paths=useMemo(()=>[[`${year}-06-21`,'#e0832f','Hạ chí 21/6'],[`${year}-03-20`,'#7f9c45','Xuân phân 20/3'],[`${year}-12-21`,'#2f7ed8','Đông chí 21/12']].map(([d,c,l])=>({p:dayPath(lat,lon,d),c,l})),[lat,lon,year])
 const today=useMemo(()=>dayPath(lat,lon,date),[lat,lon,date])
 const north=useMemo(()=>Math.abs(lat)<23.44?northSunSpan(lat,lon,year):null,[lat,lon,year])
 const sun=solarPosition(lat,lon,date,hour)
 // House outline, scaled into the inner circle and turned like the real building.
 const roof=config.roof_polygon.length?config.roof_polygon:[{x:0,y:0},{x:config.roof_width_m,y:0},{x:config.roof_width_m,y:config.roof_height_m},{x:0,y:config.roof_height_m}]
 const cx=config.roof_width_m/2,cy=config.roof_height_m/2,s=R*.42/Math.max(config.roof_width_m,config.roof_height_m)
 const t=rot*Math.PI/180,plan=(x:number,y:number)=>{const dx=x-cx,dy=y-cy,E=dx*Math.cos(t)+dy*Math.sin(t),N=-dx*Math.sin(t)+dy*Math.cos(t);return [C+E*s,C-N*s]}
 const top=plan(cx,config.roof_height_m),line=(pts:{alt:number;az:number}[])=>pts.map(p=>at(p.alt,p.az).map(v=>v.toFixed(1)).join(',')).join(' ')
 const sides=sideFacing(rot),equator=lat>=0?180:0
 const best=(Object.entries(sides) as [keyof typeof sides,number][]).reduce((b,c)=>Math.abs(((c[1]-equator+540)%360)-180)<Math.abs(((b[1]-equator+540)%360)-180)?c:b)
 const SIDE={top:'Cạnh trên',right:'Cạnh phải',bottom:'Cạnh dưới',left:'Cạnh trái'}
 return <section className="card sun-path-card">
  <div className="card-heading"><div className="card-title"><div><h3>Hướng nhà và quỹ đạo mặt trời tại vị trí này</h3><p>{n(Math.abs(lat),2)}° {lat>=0?'B':'N'}, {n(Math.abs(lon),2)}° {lon>=0?'Đ':'T'}: quỹ đạo đổi theo vĩ độ và mùa; xoay nhà để khớp thực tế.</p></div></div></div>
  <div className="sun-path-body">
   <svg viewBox="0 0 340 340" className="sun-path-svg" role="img" aria-label="Biểu đồ quỹ đạo mặt trời">
    {[0,30,60].map(a=><circle key={a} cx={C} cy={C} r={R*(90-a)/90} fill="none" stroke="#d7ddd6" strokeDasharray={a?'3 4':undefined}/>)}
    {[30,60].map(a=><text key={a} x={C+3} y={C-R*(90-a)/90+11} className="sp-ring">{a}°</text>)}
    {DIRECTIONS.map(([az,,short])=>{const [x,y]=at(-6,az);return <text key={az} x={x} y={y+4} textAnchor="middle" className={az===0?'sp-dir north':'sp-dir'}>{short}</text>})}
    <polygon points={roof.map(p=>plan(p.x,p.y).map(v=>v.toFixed(1)).join(',')).join(' ')} fill="#dfe9df" stroke="#2b6a51" strokeWidth="1.5"/>
    <line x1={C} y1={C} x2={top[0]} y2={top[1]} stroke="#2b6a51" strokeWidth="1.2" markerEnd="url(#sp-arrow)"/>
    <defs><marker id="sp-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#2b6a51"/></marker></defs>
    {paths.map(({p,c})=><polyline key={p.date} points={line(p.points)} fill="none" stroke={c} strokeWidth="2"/>)}
    <polyline points={line(today.points)} fill="none" stroke="#c4455a" strokeWidth="1.6" strokeDasharray="5 4"/>
    {today.points.filter(p=>Math.abs(p.hour-Math.round(p.hour))<.026&&Math.round(p.hour)%3===0).map(p=>{const [x,y]=at(p.alt,p.az);return <g key={p.hour}><circle cx={x} cy={y} r="2.4" fill="#c4455a"/><text x={x+4} y={y-4} className="sp-hour">{Math.round(p.hour)}h</text></g>})}
    {sun.alt>0&&(()=>{const [x,y]=at(sun.alt,sun.az);return <circle cx={x} cy={y} r="7" fill="#ffd75e" stroke="#e0a400"/>})()}
   </svg>
   <div className="sun-path-side">
    <ul className="sun-path-legend">{paths.map(({p,c,l})=><li key={p.date}><i style={{background:c}}/>{l}: trưa cao {n(p.noon.alt)}° ở phía {p.north?'Bắc':'Nam'}; mọc {p.rise!=null?directionName(p.rise):'—'}, lặn {p.set!=null?directionName(p.set):'—'}</li>)}
     <li><i className="dash"/>Ngày đang mô phỏng {day(date)}: trưa cao {n(today.noon.alt)}° ở phía {today.north?'Bắc':'Nam'}</li></ul>
    <p className="muted-note">{north?<>Ở vĩ độ này, khoảng <strong>{day(north.first)}–{day(north.last)}</strong> buổi trưa mặt trời ở <strong>phía Bắc</strong> nhà: mái dốc về phía Bắc vẫn có nắng tốt mùa hè, còn mùa đông nắng xiên thấp từ phía Nam.</>:<>Ở vĩ độ này mặt trời buổi trưa luôn ở phía {lat>=0?'Nam':'Bắc'} nhà; mùa đông nắng thấp nên bóng vật cản dài hơn nhiều.</>}</p>
    <p className="muted-note">Cạnh trên bản vẽ (mũi tên) quay về <strong>{directionName(rot)}</strong>. {SIDE[best[0]]} quay về {directionName(best[1])}, gần hướng {lat>=0?'Nam':'Bắc'} nhất: mặt mái dốc về phía này nhận nhiều nắng nhất cả năm.</p>
    <div className="orientation-picker" role="group" aria-label="Chọn hướng của cạnh trên bản vẽ">
     <span>Cạnh trên bản vẽ hướng về</span>
     <div className="orientation-grid">{DIRECTIONS.map(([az,name])=><button key={az} type="button" className={Math.abs(((rot-az+540)%360)-180)<.5?'active':''} onClick={()=>onRotate(az)} title={`${name} (${az}°)`}>{name}</button>)}</div>
     <div className="orientation-fine">{[-15,-5,5,15].map(d=><button key={d} type="button" onClick={()=>onRotate(rot+d)}>{d>0?'+':'−'}{Math.abs(d)}°</button>)}<button type="button" onClick={()=>onRotate(rot+90)}>Xoay 90°</button></div>
    </div>
   </div>
  </div>
 </section>
}
