export type Obstacle = {
  id: string
  label: string
  x: number
  y: number
  width_m: number
  depth_m: number
  height_m: number
  confidence: number
  source: 'manual' | 'gemini' | 'demo'
}

export type PanelSpec = {
  manufacturer: string
  model: string
  width_m: number
  height_m: number
  power_w: number
  price_vnd: number
  voc_v: number
  vmp_v: number
  imp_a: number
}

export type ProjectConfig = {
  project_name: string
  latitude: number
  longitude: number
  roof_width_m: number
  roof_height_m: number
  roof_azimuth_deg: number
  roof_tilt_deg: number
  setback_m: number
  panel_gap_m: number
  obstacle_clearance_m: number
  annual_irradiance_kwh_m2: number
  performance_ratio: number
  budget_vnd: number
}

export type SunPosition = {
  altitude_deg: number
  azimuth_deg: number
  zenith_deg: number
}

export type CandidatePanel = {
  id: string
  x: number
  y: number
  width_m: number
  height_m: number
  annual_energy_kwh: number
  shading_loss_pct: number
  preserved: boolean
}

export type DesignResult = {
  panels: CandidatePanel[]
  metrics: {
    panel_count: number
    peak_power_kwp: number
    annual_energy_kwh: number
    annual_energy_mwh: number
    estimated_cost_vnd: number
    average_shading_loss_pct: number
    roof_utilization_pct: number
    preserved_panel_count: number
    layout_preservation_rate_pct: number
  }
  warnings: string[]
  solver_status: string
}

export type VerifyResult = {
  valid: boolean
  checks: { id: string; label: string; status: 'PASS' | 'FAIL' | 'WARN'; detail: string }[]
}

export type StressResult = {
  passed: number
  total: number
  scenarios: { id: string; name: string; status: 'PASS' | 'FAIL'; panel_count: number; annual_energy_kwh: number; detail: string }[]
}

export type RepairResult = {
  impact: {
    changed_input: string
    affected_nodes: string[]
    reused_nodes: string[]
    recomputation_ratio_pct: number
  }
  design: DesignResult
  verification: VerifyResult
}

export type VisionResult = {
  mode: 'gemini' | 'demo'
  roof_width_m: number
  roof_height_m: number
  roof_confidence: number
  obstacles: {
    id: string
    label: string
    x_pct: number
    y_pct: number
    width_pct: number
    depth_pct: number
    height_m: number
    confidence: number
  }[]
  extracted_text: string[]
  notes: string[]
}

export type UncertaintyResult = {
  obstacle_id: string
  low_design: DesignResult
  high_design: DesignResult
  layout_difference_pct: number
  energy_difference_pct: number
  validity_changed: boolean
  impact_score: number
  action: 'AUTO_CONTINUE' | 'ASK_ENGINEER'
  explanation: string
}
