import type {Panel} from './studioTypes'

// Built-in entries are reference values; engineers must check the datasheet of the batch they buy.
// Prices are planning assumptions at the same VND/W as the default panel, not quotes.
export const BUILTIN_PANELS:Panel[]=[
 {manufacturer:'LONGi',model:'Hi-MO 6 · 580 W',width_m:1.134,height_m:2.278,power_w:580,price_vnd:4_200_000,voc_v:52.1,vmp_v:43.6,imp_a:13.3},
 {manufacturer:'JA Solar',model:'JAM72S30 · 550 W',width_m:1.134,height_m:2.279,power_w:550,price_vnd:3_980_000,voc_v:49.9,vmp_v:41.96,imp_a:13.11},
 {manufacturer:'Canadian Solar',model:'HiKu6 CS6R · 410 W',width_m:1.134,height_m:1.722,power_w:410,price_vnd:2_970_000,voc_v:37.4,vmp_v:31.4,imp_a:13.06},
]
const STORAGE_KEY='solaropt-panel-library'
export const panelKey=(p:Panel)=>`${p.manufacturer}|${p.model}`

export function readCustomPanels():Panel[]{
 try{const v=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(v)?v.filter(p=>p&&typeof p.model==='string'&&!panelErrors(p).length):[]}catch{return []}
}
export function writeCustomPanels(list:Panel[]){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(list))}catch{}}

export function panelErrors(p:Panel){
 const errors:string[]=[],ok=(v:unknown)=>typeof v==='number'&&Number.isFinite(v)&&v>0
 if(!p.manufacturer?.trim())errors.push('Thiếu hãng sản xuất')
 if(!p.model?.trim())errors.push('Thiếu tên model')
 for(const [k,label] of [['power_w','Công suất'],['width_m','Rộng'],['height_m','Dài'],['price_vnd','Giá'],['voc_v','Voc'],['vmp_v','Vmp'],['imp_a','Imp']] as [keyof Panel,string][])
  if(!ok(p[k]))errors.push(`${label} phải là số dương`)
 if(errors.length)return errors
 if(p.width_m<.3||p.width_m>3||p.height_m<.3||p.height_m>3)errors.push('Kích thước tấm nên trong khoảng 0,3–3 m')
 if(p.power_w>1500)errors.push('Công suất tấm vượt 1.500 W')
 if(p.vmp_v>=p.voc_v)errors.push('Vmp phải nhỏ hơn Voc')
 if(Math.abs(p.vmp_v*p.imp_a-p.power_w)/p.power_w>.1)errors.push(`Vmp × Imp = ${Math.round(p.vmp_v*p.imp_a)} W lệch hơn 10% so với công suất`)
 return errors
}
