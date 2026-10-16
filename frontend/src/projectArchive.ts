import type {Config,Panel,Obstacle,Objective,ProjectEvidence} from './studioTypes'
export type ProjectArchive={format:'solaropt-project-v2'|'solaropt-project-v3';config:Config;panel:Panel;obstacles:Obstacle[];sample:boolean;objective?:Objective;evidence?:ProjectEvidence|null}
export const MAX_ARCHIVE_BYTES=10_000_000
export function parseArchive(text:string):ProjectArchive{
 if(new TextEncoder().encode(text).length>MAX_ARCHIVE_BYTES)throw new Error('Gói dự án tối đa 10 MB.')
 const data=JSON.parse(text)
 if(!['solaropt-project-v2','solaropt-project-v3'].includes(data?.format)||!data.config||!data.panel||!Array.isArray(data.obstacles)||data.obstacles.length>100)throw new Error('Không đúng định dạng dự án SolarOpt.')
 if(data.evidence){
  for(const name of ['source_image','reference_image']){
   const value=data.evidence[name]
   if(value!=null&&(typeof value!=='string'||value.length>4_000_000||!/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(value)))throw new Error('Ảnh dự án phải là ảnh PNG/JPEG/WEBP nhúng, tối đa 4 MB mỗi ảnh.')
  }
 }
 if(data.objective&&!['max_energy','min_cost','robust','balanced','durability'].includes(data.objective))throw new Error('Mục tiêu dự án không hợp lệ.')
 return data
}
export function inputFingerprint(value:unknown):string{
 return JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v)
}
