// Mirrors backend app/schemas.py YieldLosses: the performance ratio is the product of the itemised losses.
export type YieldLosses={temperature_pct:number;soiling_pct:number;iam_pct:number;module_pct:number;mismatch_pct:number;dc_cable_pct:number;inverter_pct:number;ac_cable_pct:number;availability_pct:number;temp_coeff_pct:number}
export type WeatherYear={source:string;latitude:number;longitude:number;ghi:number[];dni:number[];dhi:number[];temp_air:number[];wind:number[];annual_ghi_kwh_m2:number}
export type LossKey=Exclude<keyof YieldLosses,'temp_coeff_pct'>
export const LOSS_ITEMS:{key:LossKey;label:string;hint:string;max:number}[]=[
 {key:'temperature_pct',label:'Nhiệt độ tấm',hint:'tính từ thời tiết khi tải PVGIS; lắp sát mái nóng hơn giá nghiêng thoáng',max:30},
 {key:'soiling_pct',label:'Bụi bẩn',hint:'mưa rửa một phần trong mùa mưa; vệ sinh định kỳ giảm còn 1–2%',max:30},
 {key:'iam_pct',label:'Phản xạ góc tới',hint:'ánh sáng xiên buổi sáng/chiều bị kính phản xạ',max:10},
 {key:'module_pct',label:'Suy giảm năm đầu, sai số công suất',hint:'LID/LeTID và dung sai nhà sản xuất',max:10},
 {key:'mismatch_pct',label:'Lệch thông số giữa các tấm',hint:'chuỗi chạy theo tấm yếu nhất',max:10},
 {key:'dc_cable_pct',label:'Cáp DC',hint:'',max:10},
 {key:'inverter_pct',label:'Inverter',hint:'1 − hiệu suất châu Âu (≈ 97,5%)',max:15},
 {key:'ac_cable_pct',label:'Cáp AC',hint:'',max:10},
 {key:'availability_pct',label:'Ngừng hoạt động, nhảy do quá áp lưới',hint:'cuối tuyến hạ thế buổi trưa điện áp cao làm inverter tự ngắt',max:30},
]
export const defaultLosses=():YieldLosses=>({temperature_pct:8,soiling_pct:4,iam_pct:2.5,module_pct:2,mismatch_pct:1.5,dc_cable_pct:1.5,inverter_pct:2.5,ac_cable_pct:1,availability_pct:2,temp_coeff_pct:-.32})
export function performanceRatio(l:YieldLosses){
 let ratio=1
 for(const {key} of LOSS_ITEMS)ratio*=1-l[key]/100
 return Math.round(ratio*1e4)/1e4
}
/** Days per month on the 12 × 24 grid (index month*24 + local hour), as the backend weights them. */
export const DAYS=[31,28,31,30,31,30,31,31,30,31,30,31]
