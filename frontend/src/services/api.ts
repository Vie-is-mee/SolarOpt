import type { DesignResult, Obstacle, PanelSpec, ProjectConfig, RepairResult, StressResult, SunPosition, VerifyResult, VisionResult, UncertaintyResult } from '../types'

const API = import.meta.env.VITE_API_BASE || ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init)
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      const data = await response.json()
      message = data.detail || message
    } catch {}
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{status:string; gemini_configured:boolean; gemini_model:string}>('/api/health'),

  analyze: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<VisionResult>('/api/vision/analyze', { method: 'POST', body })
  },

  sunPosition: (latitude:number, longitude:number, date:string, hour_local:number) =>
    request<SunPosition>('/api/solar/sun-position', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({latitude, longitude, date, hour_local, timezone:'Asia/Ho_Chi_Minh'})
    }),

  irradiance: (lat:number, lon:number, tilt:number, azimuth:number) =>
    request<{source:'PVGIS'|'fallback'; annual_irradiance_kwh_m2:number; specific_yield_kwh_kwp:number; detail:string}>(
      `/api/solar/irradiance?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&tilt=${encodeURIComponent(tilt)}&azimuth=${encodeURIComponent(azimuth)}`
    ),

  design: (config:ProjectConfig, panel:PanelSpec, obstacles:Obstacle[], sun:SunPosition|null, objective:string, previous_panels:any[] = [], minimal_repair_weight=0) =>
    request<DesignResult>('/api/design/generate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({config, panel, obstacles, sun, objective, previous_panels, minimal_repair_weight})
    }),

  verify: (config:ProjectConfig, panel:PanelSpec, obstacles:Obstacle[], design:DesignResult, sun:SunPosition|null) =>
    request<VerifyResult>('/api/design/verify', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({config, panel, obstacles, design, sun})
    }),

  stress: (config:ProjectConfig, panel:PanelSpec, obstacles:Obstacle[], design:DesignResult, sun:SunPosition|null) =>
    request<StressResult>('/api/design/stress-test', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({config, panel, obstacles, design, sun})
    }),

  uncertainty: (config:ProjectConfig, panel:PanelSpec, obstacles:Obstacle[], obstacle_id:string, low_height_m:number, high_height_m:number, objective='balanced') =>
    request<UncertaintyResult>('/api/uncertainty/evaluate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({config,panel,obstacles,obstacle_id,low_height_m,high_height_m,objective})
    }),

  repair: (config:ProjectConfig, panel:PanelSpec, before:Obstacle[], after:Obstacle[], previous_design:DesignResult, sun:SunPosition|null, objective='balanced') =>
    request<RepairResult>('/api/design/repair', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({config, panel, obstacles_before:before, obstacles_after:after, previous_design, sun, objective, minimal_repair_weight:250})
    }),

  versions: (projectName:string) => request<any[]>(`/api/projects/${encodeURIComponent(projectName)}/versions`),
}
