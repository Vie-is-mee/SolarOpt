export type Point = { x:number; y:number }
export type RoofFace = {id:string;label:string;polygon:Point[];elevation_m:number;tilt_deg:number;azimuth_deg:number;installable:boolean}
export type Obstacle = {
  id:string; label:string; x:number; y:number; width_m:number; depth_m:number; height_m:number;
  scope:'roof'|'neighbor'; source:'manual'|'groq'|'ollama'|'gemini'|'demo'; confidence:number;
  confirmed:boolean; floors?:number|null;
  shape?:'rect'|'ellipse'|'polygon';rotation_deg?:number;points?:Point[];base_elevation_m?:number|null;
}
export type Config = {
  target_energy_kwh_year?:number|null;
  layout_edge_reserve_m?:number;
  layout_angle_deg?:number|null;
  dimensions_source?: 'assumed'|'reference'|'measured'; dimensions_verified?: boolean; calibration_reference_m?: number|null;
  measurement_image_width_px?: number|null; measurement_image_height_px?: number|null;
  project_name:string; latitude:number; longitude:number; roof_width_m:number; roof_height_m:number;
  roof_azimuth_deg:number; roof_tilt_deg:number; north_rotation_deg:number; roof_elevation_m:number;
  roof_polygon:Point[]; geometry_confirmed:boolean; setback_m:number; panel_gap_m:number;
  roof_faces:RoofFace[];roof_openings:Point[][];
  obstacle_clearance_m:number; annual_irradiance_kwh_m2:number; performance_ratio:number; budget_vnd:number;
}
export type Panel = {manufacturer:string;model:string;width_m:number;height_m:number;power_w:number;price_vnd:number;voc_v:number;vmp_v:number;imp_a:number}
export type Sun = {altitude_deg:number;azimuth_deg:number;zenith_deg:number;source:string}
export type Scene = {
  sun:Sun;shadows:{id:string;label:string;polygons:number[][][]}[];
  cells:{x:number;y:number;width_m:number;height_m:number;irradiance_w_m2:number;shade_fraction:number}[];
  roof_polygons:number[][][];usable_polygons:number[][][];shaded_area_m2:number;shaded_pct:number;
  plane_irradiance_w_m2:number;irradiance_source:string;notes:string[];
  faces?:{id:string;label:string;polygons:number[][][];elevation_m:number;tilt_deg:number;irradiance_w_m2:number;area_m2:number;installable:boolean}[];
}
export type PlacedPanel = {rotation_deg?:number;id:string;x:number;y:number;width_m:number;height_m:number;annual_energy_kwh:number;shading_loss_pct:number;preserved:boolean}
export type LayoutTrial={search_stage?:'coarse'|'refined';angle_deg:number;offset_x_m:number;offset_y_m:number;candidate_count:number;geometry_candidate_count?:number;shading_rejected_count?:number;robustness_rejected_count?:number;target_met?:boolean|null;panel_count:number;annual_energy_kwh:number;objective_score:number;selected:boolean}
export type Design = {objective?:Objective;target_energy_kwh_year?:number|null;target_met?:boolean|null;robustness_checks?:{id:string;name:string;status:"PASS"|"FAIL";detail:string}[];layout_trials?:LayoutTrial[];panels:PlacedPanel[]; metrics:{panel_count:number;peak_power_kwp:number;annual_energy_kwh:number;annual_energy_mwh:number;estimated_cost_vnd:number;average_shading_loss_pct:number;maximum_shading_loss_pct?:number;roof_utilization_pct:number;preserved_panel_count:number;layout_preservation_rate_pct:number}; warnings:string[];solver_status:string}
export type Verification = {valid:boolean;checks:{id:string;label:string;status:'PASS'|'FAIL'|'WARN';detail:string}[]}
export type Stress = {passed:number;total:number;scenarios:{id:string;name:string;status:'PASS'|'FAIL';panel_count:number;annual_energy_kwh:number;detail:string;failed_checks?:{id:string;label:string;detail:string}[];recommendations?:string[];affected_panel_ids?:string[]}[]}
export type Repair = {impact:{changed_input:string;affected_nodes:string[];reused_nodes:string[];recomputation_ratio_pct:number};design:Design;verification:Verification}
export type Vision = {
  mode:'groq'|'ollama'|'gemini'|'manual';model:string;roof_width_m:number|null;roof_height_m:number|null;roof_confidence:number;
  obstacles:{id:string;label:string;x_pct:number;y_pct:number;width_pct:number;depth_pct:number;height_m:number|null;confidence:number;observation:string;requires_placement:boolean}[];
  roof_polygon_pct:Point[];extracted_text:string[];notes:string[];events:{stage:string;status:string;detail:string}[];cached:boolean;elapsed_ms:number;preview_data_url:string|null;
  roof_polygon_image_pct?:Point[];roof_aspect_ratio?:number|null;roof_crop_data_url?:string|null;coordinate_version?:number;
}
export type TraceResult={algorithm:string;polygon_image_pct:Point[];roof_polygon_pct:Point[];roof_bbox_image_pct:number[];roof_aspect_ratio:number;roof_width_px:number;roof_height_px:number;image_width_px:number;image_height_px:number;roof_crop_data_url:string;overlay_data_url:string;elapsed_ms:number;notes:string[];rectified?:boolean;image_data_url?:string;width_px?:number;height_px?:number}
export type Health = {status:string;ai:{provider:string;model:string;configured:boolean;local:boolean;status_detail:string}}
export type Version = {id:number;version_label:string;reason:string;created_at:string;payload:{config:Config;panel:Panel;obstacles:Obstacle[];design:Design;verification?:Verification}}
export type Objective = 'balanced'|'max_energy'|'durability'|'min_cost'|'robust'
