import type {Config,Panel,Obstacle,Design,Verification,Scene,Health,Vision,Stress,Repair,Version,Objective,Sun,ProjectEvidence} from '../studioTypes'
import {accountIdentity} from '../draftOwner'
const base = import.meta.env.VITE_API_BASE || ''
async function request<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T> {
  const identity=accountIdentity()
  const headers={'X-SolarOpt-Request':'1','X-SolarOpt-User':identity}
  const timeout = AbortSignal.timeout(120_000)
  let response:Response
  try {response = await fetch(base+path,{credentials:'include',headers,method:body===undefined?'GET':'POST',...(body===undefined?{}:body instanceof FormData?{body}:{headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(body)}),signal:signal ? AbortSignal.any([signal, timeout]) : timeout})}
  catch(error){
    if(timeout.aborted&&!signal?.aborted)throw new Error('Máy chủ tính quá thời gian chờ. Các phương án đã hoàn tất vẫn được giữ lại. Với mái lớn, chọn góc xếp thủ công hoặc giảm phạm vi mái rồi tính lại.')
    throw error
  }
  if(response.status===401&&typeof window!=='undefined')window.dispatchEvent(new CustomEvent('solaropt-auth-required',{detail:identity}))
  // Quota: 402 opens the plan dialog; billable calls refresh the usage meter.
  if(typeof window!=='undefined'){if(response.status===402)window.dispatchEvent(new Event('solaropt-quota'));else if(response.ok&&/^\/api\/(design\/(generate|repair)|vision\/analyze)/.test(path))window.dispatchEvent(new Event('solaropt-usage'))}
  if(!response.ok){let detail='';try{const data=await response.json();detail=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)}catch{}throw new Error(detail||`Yêu cầu chưa thành công (${response.status}).`)}
  return response.json()
}
export const studioApi={
  prepare:(file:File)=>{const data=new FormData();data.append('file',file);return request<{image_data_url:string;width_px:number;height_px:number}>('/api/roof/prepare',data)},
  trace:(body:unknown)=>request<import('../studioTypes').TraceResult>('/api/roof/trace',body),
  roofTemplate:(body:unknown)=>request<{roof_faces:import('../studioTypes').RoofFace[];notes:string[]}>('/api/roof/template',body),
  validateProject:(config:Config,panel:Panel,obstacles:Obstacle[],evidence?:ProjectEvidence|null)=>request<{valid:boolean}>('/api/projects/validate',{config,panel,obstacles,evidence}),
  health:()=>request<Health>('/api/health'),
  scene:(config:Config,obstacles:Obstacle[],date:string,hour_local:number,signal?:AbortSignal)=>request<Scene>('/api/solar/scene',{config,obstacles,date,hour_local},signal),
  analyze:(file:File,context:File[],kind:string,config:Config)=>{const data=new FormData();data.append('file',file);context.forEach(f=>data.append('context_files',f));data.append('input_kind',kind);// Unknown sizes are omitted, e.g. when the drawing itself is read for its dimensions.
  if(config.roof_width_m>0)data.append('roof_width_m',String(config.roof_width_m));if(config.roof_height_m>0)data.append('roof_height_m',String(config.roof_height_m));return request<Vision>('/api/vision/analyze',data)},
  mountingCompare:(config:Config,panel:Panel,obstacles:Obstacle[])=>request<{options:{label:string;settings:Partial<Config>&{mounting:'flush'|'tilted_rack'|'tracker'};panels:number;kwp:number;annual_kwh:number;kwh_per_panel:number;vs_flush_pct:number|null}[];best:string|null;notes:string[]}>('/api/design/mounting-compare',{config,panel,obstacles,objective:'max_energy'}),
  design:(config:Config,panel:Panel,obstacles:Obstacle[],objective:Objective,evidence?:ProjectEvidence|null)=>request<Design>('/api/design/generate',{config,panel,obstacles,objective,evidence}),
  verify:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,sun:Sun|null)=>request<Verification>('/api/design/verify',{config,panel,obstacles,design,sun}),
  stress:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,sun:Sun|null)=>request<Stress>('/api/design/stress-test',{config,panel,obstacles,design,sun}),
  stressPreview:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,scenario_id:string,date:string,hour_local:number,signal?:AbortSignal)=>request<import('../studioTypes').StressPreviewData>('/api/design/stress-preview',{config,panel,obstacles,design,scenario_id,date,hour_local},signal),
  repair:(config:Config,panel:Panel,before:Obstacle[],after:Obstacle[],previous_design:Design,objective:Objective,previous_config:Config,previous_panel:Panel,evidence?:ProjectEvidence|null)=>request<Repair>('/api/design/repair',{config,panel,previous_config,previous_panel,evidence,obstacles_before:before,obstacles_after:after,previous_design,objective,minimal_repair_weight:250}),
  history:()=>request<Version[]>('/api/history'),
  versions:(name:string)=>request<Version[]>(`/api/projects/${encodeURIComponent(name)}/versions`),
  version:(name:string,id:number)=>request<Version>(`/api/projects/${encodeURIComponent(name)}/versions/${id}`),
  approve:(config:Config,panel:Panel,obstacles:Obstacle[],design:Design,sun:Sun|null,evidence?:ProjectEvidence|null)=>request<{version_id:number;scope:string}>('/api/projects/approve',{config,panel,obstacles,design,sun,evidence}),
  irradiance:(config:Config)=>request<{source:string;annual_irradiance_kwh_m2:number;detail:string;reference_tilt_deg:number;reference_azimuth_deg:number}>(`/api/solar/irradiance?lat=${config.latitude}&lon=${config.longitude}&tilt=0&azimuth=180`),
  uncertainty:(config:Config,panel:Panel,obstacles:Obstacle[],obstacle_id:string,low_height_m:number,high_height_m:number)=>request<{layout_difference_pct:number;energy_difference_pct:number;action:string;explanation:string}>('/api/uncertainty/evaluate',{config,panel,obstacles,obstacle_id,low_height_m,high_height_m}),
}
