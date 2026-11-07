import type {Panel} from './studioTypes'

// Built-in entries are reference values; engineers must check the datasheet of the batch they buy.
// Prices: retail lists of Vietnamese distributors read 07/11/2026 (Solar Saigon 26/05/2026, DHC, Kitawa 6/2026,
// TC Energy 11/2026): 540–720 W modules at 3 144–4 569 đ/Wp, median ≈ 3 946. Evidence: src/dataSources.ts.
export const PANEL_PRICE_RANGE={low:3100,high:4600,date:'05–11/2026'}
export const PANEL_PRICE_NOTE=`Giá bán lẻ tham khảo ${PANEL_PRICE_RANGE.date} từ bảng giá công khai của các nhà phân phối (Solar Saigon, DHC Solar, Kitawa, TC Energy, đọc 07/11/2026): tấm 540–720 W khoảng ${PANEL_PRICE_RANGE.low.toLocaleString('vi-VN')}–${PANEL_PRICE_RANGE.high.toLocaleString('vi-VN')} đ/Wp, trang không ghi rõ VAT; đơn hàng dự án thường thấp hơn. Thay bằng báo giá thật.`
export const BUILTIN_PANELS:Panel[]=[
 {manufacturer:'LONGi',model:'Hi-MO 6 · 580 W',width_m:1.134,height_m:2.278,power_w:580,price_vnd:2_650_000,voc_v:52.21,vmp_v:44.06,imp_a:13.17},
 {manufacturer:'JA Solar',model:'JAM72S30 · 550 W',width_m:1.134,height_m:2.279,power_w:550,price_vnd:2_200_000,voc_v:49.9,vmp_v:41.96,imp_a:13.11},
 {manufacturer:'Canadian Solar',model:'HiKu6 CS6R · 410 W',width_m:1.134,height_m:1.722,power_w:410,price_vnd:1_650_000,voc_v:37.4,vmp_v:31.4,imp_a:13.06},
]
/** VND per watt-peak, the unit quotes compare on; and a warning when a price sits far outside the market. */
export const pricePerWp=(p:Panel)=>p.power_w>0?p.price_vnd/p.power_w:0
export function priceWarning(p:Panel){const v=pricePerWp(p);if(!v)return ''
 if(v>PANEL_PRICE_RANGE.high*1.15)return `Giá ${Math.round(v).toLocaleString('vi-VN')} đ/Wp cao hơn mặt bằng thị trường (${PANEL_PRICE_RANGE.low.toLocaleString('vi-VN')}–${PANEL_PRICE_RANGE.high.toLocaleString('vi-VN')} đ/Wp, ${PANEL_PRICE_RANGE.date}); kiểm tra lại báo giá.`
 if(v<PANEL_PRICE_RANGE.low*.75)return `Giá ${Math.round(v).toLocaleString('vi-VN')} đ/Wp thấp bất thường so với thị trường; kiểm tra nguồn gốc và bảo hành.`
 return ''}
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
