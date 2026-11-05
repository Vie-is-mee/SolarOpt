// House orientation on the compass and the sun's paths at the site.
// The drawing's +Y axis points to compass azimuth config.north_rotation_deg (clockwise from north).
import type {Config} from './studioTypes'
import {solarPosition} from './solarPosition'

export const DIRECTIONS:[number,string,string][]=[[0,'Bắc','B'],[45,'Đông Bắc','ĐB'],[90,'Đông','Đ'],[135,'Đông Nam','ĐN'],[180,'Nam','N'],[225,'Tây Nam','TN'],[270,'Tây','T'],[315,'Tây Bắc','TB']]
const norm=(a:number)=>((a%360)+360)%360
/** Nearest of the eight compass names, with the exact bearing when it is off by more than a degree. */
export function directionName(az:number){
 const a=norm(az),[d,name]=DIRECTIONS.reduce((best,cur)=>Math.min(Math.abs(cur[0]-a),360-Math.abs(cur[0]-a))<Math.min(Math.abs(best[0]-a),360-Math.abs(best[0]-a))?cur:best)
 const off=Math.min(Math.abs(d-a),360-Math.abs(d-a))
 return off<1?name:`${name} (${a.toLocaleString('vi-VN',{maximumFractionDigits:1})}°)`
}
/** Turn the house on the compass. Roof faces keep their shape on the drawing, so their compass azimuths
 * (and the single roof plane's) turn by the same angle; tilted racks keep their own compass direction. */
export function rotateHouse(c:Config,rotation:number):Config{
 const next=Math.round(norm(rotation)*10)/10,delta=next-c.north_rotation_deg
 if(Math.abs(delta)<1e-9)return c
 return {...c,north_rotation_deg:next,roof_azimuth_deg:Math.round(norm(c.roof_azimuth_deg+delta)*1000)/1000,
  roof_faces:(c.roof_faces||[]).map(f=>({...f,azimuth_deg:Math.round(norm(f.azimuth_deg+delta)*1000)/1000})),geometry_confirmed:false}
}
/** Compass direction each side of the drawing faces. */
export const sideFacing=(rot:number)=>({top:norm(rot),right:norm(rot+90),bottom:norm(rot+180),left:norm(rot+270)})

export const CITIES:[string,number,number][]=[
 ['Hà Nội',21.0285,105.8542],['TP. Hồ Chí Minh',10.7769,106.7009],['Hải Phòng',20.8449,106.6881],['Hạ Long',20.9599,107.0425],['Lạng Sơn',21.8537,106.7615],
 ['Sa Pa',22.3364,103.8438],['Điện Biên Phủ',21.386,103.023],['Vinh',18.6796,105.6813],['Huế',16.4637,107.5909],['Đà Nẵng',16.0544,108.2022],
 ['Quy Nhơn',13.782,109.2197],['Nha Trang',12.2388,109.1967],['Buôn Ma Thuột',12.6667,108.05],['Đà Lạt',11.9404,108.4583],['Vũng Tàu',10.346,107.0843],
 ['Cần Thơ',10.0452,105.7469],['Phú Quốc',10.227,103.964],['Cà Mau',9.1769,105.1524],
]

export type DayPath={date:string;points:{hour:number;alt:number;az:number}[];noon:{hour:number;alt:number;az:number};rise:number|null;set:number|null;north:boolean}
export function dayPath(lat:number,lon:number,date:string):DayPath{
 const points=[];let rise:number|null=null,set:number|null=null,prev:{alt:number;az:number}|null=null
 for(let h=4;h<=20.001;h+=.05){const p=solarPosition(lat,lon,date,h);if(prev&&prev.alt<=0&&p.alt>0)rise=p.az;if(prev&&prev.alt>0&&p.alt<=0)set=prev.az;if(p.alt>0)points.push({hour:h,...p});prev=p}
 const noon=points.reduce((b,p)=>p.alt>b.alt?p:b,points[0]??{hour:12,alt:0,az:180})
 // Side of the midday sun from its declination: the sampled azimuth is meaningless near the zenith.
 const north=solarPosition(lat,lon,date,12).decl>lat
 return {date,points,noon,rise,set,north}
}
/** Days of the year when the midday sun stands north of the zenith (only between the tropics). */
export function northSunSpan(lat:number,lon:number,year:number){
 let first:string|null=null,last:string|null=null
 for(let d=0;d<365;d++){const s=new Date(Date.UTC(year,0,1+d)).toISOString().slice(0,10)
  if(solarPosition(lat,lon,s,12).decl>lat){first??=s;last=s}}
 return first&&last?{first,last}:null
}
