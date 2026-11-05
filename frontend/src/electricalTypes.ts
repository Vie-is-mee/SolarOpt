// Mirrors backend/app/services/electrical.py.
export type Inverter={id:string;manufacturer:string;model:string;phase:'single'|'three';ac_rated_w:number;max_dc_power_w:number;max_dc_voltage_v:number;mppt_min_v:number;mppt_max_v:number;start_voltage_v:number;mppt_count:number;strings_per_mppt:number;max_current_per_mppt_a:number;max_short_circuit_per_mppt_a:number;price_vnd:number;source:string}
export type ElectricalSettings={inverter_id:string|null;custom_inverter:Inverter|null;grid_phase:'auto'|'single'|'three';min_ambient_c:number|null;max_ambient_c:number;cell_rise_c:number;voc_coeff_pct:number;vmp_coeff_pct:number;isc_a:number|null;home_run_m:number;ac_run_m:number;max_ac_kw:number|null}
export type StringPlan={id:string;inverter:number;mppt:number;face_id:string;orientation:string;panel_ids:string[];length:number;voc_cold_v:number;vmp_hot_v:number;vmp_cold_v:number;imp_a:number;shading_spread_pct:number;cable_m:number}
export type BomGroup='panel'|'inverter'|'dc'|'ac'|'earthing'|'mounting'
export type BomItem={group:BomGroup;name:string;spec:string;quantity:number;unit:string;unit_price_vnd:number;amount_vnd:number}
export type Electrical={valid:boolean;inverter:Inverter;inverter_count:number;phase:'single'|'three';dc_kwp:number;ac_kw:number;dc_ac_ratio:number;string_min:number;string_max:number;strings:StringPlan[];mppts:{inverter:number;mppt:number;strings:string[];current_a:number;short_circuit_a:number}[];unassigned_panel_ids:string[];checks:{id:string;label:string;status:'PASS'|'WARN'|'FAIL';detail:string}[];bom:BomItem[];cost_by_group:Partial<Record<BomGroup,number>>;options:{inverter_id:string;label:string;phase:'single'|'three';ac_kw:number;count:number;dc_ac_ratio:number;feasible:boolean;price_vnd:number;note:string}[];assumptions:string[];summary:string}

export const defaultElectricalSettings=():ElectricalSettings=>({inverter_id:null,custom_inverter:null,grid_phase:'auto',min_ambient_c:null,max_ambient_c:40,cell_rise_c:30,voc_coeff_pct:-0.27,vmp_coeff_pct:-0.35,isc_a:null,home_run_m:15,ac_run_m:20,max_ac_kw:null})
export const BOM_GROUPS:Record<BomGroup,string>={panel:'Tấm pin',inverter:'Inverter',dc:'Phía DC',ac:'Phía AC',earthing:'Tiếp địa',mounting:'Khung giá đỡ'}

/** Estimate line items the electrical bill of materials can price, keyed by the economics cost names. */
export const ESTIMATE_ITEMS:{name:string;groups:BomGroup[]}[]=[
 {name:'Bộ biến đổi điện (inverter)',groups:['inverter']},
 {name:'Dây điện, bảo vệ và tiếp địa',groups:['dc','ac','earthing']},
 {name:'Khung, ray và phụ kiện',groups:['mounting']},
]
export function estimateFromBom(e:Electrical){
 return ESTIMATE_ITEMS.map(i=>({name:i.name,amount:Math.round(i.groups.reduce((s,g)=>s+(e.cost_by_group[g]||0),0))}))
}

/** Twelve distinguishable string colours; strings past twelve reuse them in order. */
export const STRING_COLOURS=['#2f7ed8','#e0832f','#3aa66a','#c4455a','#8a5cc2','#1f9fa6','#c79a1e','#6b7f2a','#d0609e','#4d6bb3','#9a5b34','#3c8d8f']
