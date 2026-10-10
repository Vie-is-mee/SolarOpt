import type {Config,Panel,Obstacle,Design,Verification,Scene,Health,Vision,Stress,Repair,Version,Objective,Sun} from '../studioTypes'
const base = import.meta.env.VITE_API_BASE || ''
async function request<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T> {
  const response = await fetch(base+path,{method:body===undefined?'GET':'POST',...(body===undefined?{}:body instanceof FormData?{body}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),signal})
  if(!response.ok){let detail='';try{const data=await response.json();detail=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)}catch{}throw new Error(detail||`Yêu cầu chưa thành công (${response.status}).`)}
  return response.json()
}
export const studioApi={
  prepare:(file:File)=>{const data=new FormData();data.append('file',file);return request<{image_data_url:string;width_px:number;height_px:number}>('/api/roof/prepare',data)},
  trace:(body:unknown)=>request<import('../studioTypes').TraceResult>('/api/roof/trace',body),
  validateProject:(config:Config,panel:Panel,obstacles:Obstacle[])=>request<{valid:boolean}>('/api/projects/validate',{config,panel,obstacles}),
  health:()=>request<Health>('/api/health'),
  scene:(config:Config,obstacles:Obstacle[],date:string,hour_local:number,signal?:AbortSignal)=>request<Scene>('/api/solar/scene',{config,obstacles,date,hour_local},signal),
  analyze:(file:File,context:File[],kind:string,config:Config)=>{const data=new FormData();data.append('file',file);context.forEach(f=>data.append('context_files',f));data.append('input_kind',kind);data.append('roof_width_m',String(config.roof_width_m));data.append('roof_height_m',String(config.roof_height_m));return request<Vision>('/api/vision/analyze',data)},
  design:(config:Config,panel:Panel,obstacles:Obstacle[],objective:Objective)=>request<Design>('/api/design/generate',{config,panel,obstacles,objective}),
  verify:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,sun:Sun|null)=>request<Verification>('/api/design/verify',{config,panel,obstacles,design,sun}),
  stress:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,sun:Sun|null)=>request<Stress>('/api/design/stress-test',{config,panel,obstacles,design,sun}),
  repair:(config:Config,panel:Panel,before:Obstacle[],after:Obstacle[],previous_design:Design,objective:Objective,previous_config:Config,previous_panel:Panel)=>request<Repair>('/api/design/repair',{config,panel,previous_config,previous_panel,obstacles_before:before,obstacles_after:after,previous_design,objective,minimal_repair_weight:250}),
  versions:(name:string)=>request<Version[]>(`/api/projects/${encodeURIComponent(name)}/versions`),
  approve:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,sun:Sun|null)=>request<{version_id:number;scope:string}>('/api/projects/approve',{config,panel,obstacles,design,sun}),
  irradiance:(config:Config)=>request<{source:string;annual_irradiance_kwh_m2:number;detail:string}>(`/api/solar/irradiance?lat=${config.latitude}&lon=${config.longitude}&tilt=${config.roof_tilt_deg}&azimuth=${config.roof_azimuth_deg}`),
  uncertainty:(config:Config,panel:Panel,obstacles:Obstacle[],obstacle_id:string,low_height_m:number,high_height_m:number)=>request<{layout_difference_pct:number;energy_difference_pct:number;action:string;explanation:string}>('/api/uncertainty/evaluate',{config,panel,obstacles,obstacle_id,low_height_m,high_height_m}),
}
