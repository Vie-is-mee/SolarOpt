// Site survey answers (stored in the project evidence) and the screening the server returns for them.
// Mirrors backend/app/site_evidence.py and backend/app/services/site.py.
import type {Panel} from './studioTypes'
import {panelKey} from './panelLibrary'

export type WindZone='I'|'II'|'III'|'IV'|'V'
export type SiteSurvey={
 roof_material:'metal'|'concrete'|'tile'|'combustible'|'unknown';roof_age_years:number|null;purlin:'steel'|'wood'|'concrete'|'unknown';roof_defects:boolean
 wind_zone:WindZone|null;terrain:'A'|'B'|'C';coast_km:number|null;industrial_air:boolean;foot_capacity_kn:number|null
 grid_connected:boolean;pccc_listed:boolean;public_property:boolean
 image_source:'satellite'|'drone'|'drawing'|'site'|null;image_date:string|null;tilt_measured:boolean;site_visit:boolean
}
export const emptySurvey=():SiteSurvey=>({roof_material:'unknown',roof_age_years:null,purlin:'unknown',roof_defects:false,wind_zone:null,terrain:'B',coast_km:null,industrial_air:false,foot_capacity_kn:null,
 grid_connected:true,pccc_listed:false,public_property:false,image_source:null,image_date:null,tilt_measured:false,site_visit:false})

export type ReviewStatus='PASS'|'WARN'|'FAIL'|'INFO'
export type ReviewItem={id:string;label:string;status:ReviewStatus;detail:string;source:string}
export type ReviewSection={id:'structure'|'wind'|'corrosion'|'fire'|'legal'|'data';title:string;items:ReviewItem[]}
export type MountingPlan={surveyed:boolean;wind_zone:WindZone;zone_assumed:boolean;w0_kpa:number;k_z:number;q_center_kpa:number;q_edge_kpa:number;edge_zone_m:number;foot_capacity_kn:number;
 foot_spacing_center_m:number;foot_spacing_edge_m:number;panel_design_load_pa:number;recommended_setback_m:number;corrosion_class:'C2'|'C3'|'C4'|'C5';corrosion_assumed:boolean;price_factor:number;rail_spec:string;fastener_spec:string;notes:string[]}
export type SiteReview={sections:ReviewSection[];mounting:MountingPlan;dead_load_kg_m2:number;array_mass_kg:number;legal_path:string;counts:Record<ReviewStatus,number>}

/** Datasheet figures beyond the electrical ones: mass, rear (uplift) test load, warranty, degradation.
 * Reference values from the makers' datasheets; check the revision of the batch bought. */
export type PanelDatasheet={mass_kg:number;rear_load_pa:number;product_years:number;power_years:number;first_year_pct:number;yearly_pct:number;source:string}
export const PANEL_DATASHEETS:Record<string,PanelDatasheet>={
 'LONGi|Hi-MO 6 · 580 W':{mass_kg:27.5,rear_load_pa:2400,product_years:12,power_years:25,first_year_pct:1.5,yearly_pct:.4,source:'LONGi, datasheet LR5-72HTH 565–585M (bảo hành sản phẩm 12–15 năm tùy phiên bản, kiểm tra phiếu bảo hành)'},
 'JA Solar|JAM72S30 · 550 W':{mass_kg:28.6,rear_load_pa:2400,product_years:12,power_years:25,first_year_pct:2,yearly_pct:.55,source:'JA Solar, datasheet JAM72S30 525–550/MR'},
 'Canadian Solar|HiKu6 CS6R · 410 W':{mass_kg:21.3,rear_load_pa:2400,product_years:12,power_years:25,first_year_pct:2,yearly_pct:.55,source:'Canadian Solar, datasheet HiKu6 CS6R-MS'},
}
export const datasheetOf=(p:Panel):PanelDatasheet|null=>PANEL_DATASHEETS[panelKey(p)]??null
/** Power left at the end of the power warranty, % of nameplate. */
export const warrantedEnd=(d:PanelDatasheet)=>100-d.first_year_pct-d.yearly_pct*(d.power_years-1)
/** Datasheet figures the site review needs, sent beside the survey (they belong to the panel, not the site). */
export function panelFigures(p:Panel){const d=datasheetOf(p);return {panel_mass_kg:d?.mass_kg??null,panel_rear_load_pa:d?.rear_load_pa??null}}

export const ROOF_MATERIALS:[SiteSurvey['roof_material'],string][]=[['unknown','Chưa khảo sát'],['metal','Tôn (mái kim loại)'],['concrete','Bê tông (mái bằng)'],['tile','Ngói'],['combustible','Vật liệu cháy được (nhựa, gỗ, tấm lợp hữu cơ)']]
export const PURLINS:[SiteSurvey['purlin'],string][]=[['unknown','Chưa rõ'],['steel','Thép (C, Z, hộp)'],['wood','Gỗ'],['concrete','Bê tông']]
export const TERRAINS:[SiteSurvey['terrain'],string][]=[['A','A · trống trải, ven biển, ven hồ'],['B','B · ngoại ô, thị trấn, nhà thấp'],['C','C · nội đô dày nhà cao']]
export const IMAGE_SOURCES:[NonNullable<SiteSurvey['image_source']>,string][]=[['satellite','Ảnh vệ tinh'],['drone','Ảnh drone'],['drawing','Bản vẽ'],['site','Đo tại chỗ']]
export const SECTION_ICONS:Record<ReviewSection['id'],string>={structure:'roof',wind:'compass',corrosion:'layers',fire:'alert',legal:'file',data:'help'}
