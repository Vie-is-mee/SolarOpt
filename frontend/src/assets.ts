import type {Obstacle} from './studioTypes'

/** Typical rooftop objects and surroundings. Sizes are starting values: the engineer adjusts them to the site.
 * Shading still uses the footprint prism (trees are treated as solid, which is conservative). */
export type AssetKind='tank'|'chimney'|'ac'|'stair'|'skylight'|'tree_round'|'tree_cone'|'tree_palm'|'house'
 |'tank_flat'|'solar_heater'|'hatch'|'parapet'|'vent_turbine'|'dish'|'lightning'|'cooling'|'sign'|'drying'|'pole'|'tower'|'wall'
export type Preset={kind:AssetKind;label:string;group:'roof'|'around';scope:'roof'|'neighbor';shape:'rect'|'ellipse';w:number;d:number;h:number;floors?:number;hint:string}
const FLOOR=3.3
export const PRESETS:Preset[]=[
 {kind:'tank',label:'Bồn nước',group:'roof',scope:'roof',shape:'ellipse',w:1.2,d:1.2,h:1.6,hint:'Bồn inox đứng 1.000–1.500 L'},
 {kind:'chimney',label:'Ống khói / thông gió',group:'roof',scope:'roof',shape:'rect',w:.6,d:.6,h:1.5,hint:'Ống bếp, ống thông hơi'},
 {kind:'ac',label:'Cục nóng máy lạnh',group:'roof',scope:'roof',shape:'rect',w:.9,d:.4,h:.7,hint:'Dàn nóng điều hòa'},
 {kind:'stair',label:'Tum thang',group:'roof',scope:'roof',shape:'rect',w:3,d:2.5,h:2.7,hint:'Lồng cầu thang lên mái'},
 {kind:'skylight',label:'Giếng trời / mái kính',group:'roof',scope:'roof',shape:'rect',w:2,d:2,h:.4,hint:'Không đặt pin lên'},
 {kind:'tank_flat',label:'Bồn nước nằm',group:'roof',scope:'roof',shape:'rect',w:2.2,d:1.2,h:1.3,hint:'Bồn ngang 1.500–3.000 L trên chân đế'},
 {kind:'solar_heater',label:'Máy nước nóng mặt trời',group:'roof',scope:'roof',shape:'rect',w:2,d:1.6,h:1.4,hint:'Ống chân không + bình chứa, nghiêng về Nam'},
 {kind:'hatch',label:'Cửa sập lên mái',group:'roof',scope:'roof',shape:'rect',w:.9,d:.9,h:.4,hint:'Lối ra mái: PCCC giữ 3 m quanh'},
 {kind:'parapet',label:'Tường chắn mái / lan can',group:'roof',scope:'roof',shape:'rect',w:6,d:.2,h:1.1,hint:'Kéo dài, xoay theo mép mái; đổ bóng buổi sáng/chiều'},
 {kind:'vent_turbine',label:'Quả cầu thông gió',group:'roof',scope:'roof',shape:'ellipse',w:.6,d:.6,h:.75,hint:'Hút nhiệt mái tôn nhà xưởng'},
 {kind:'dish',label:'Chảo vệ tinh / ăng-ten',group:'roof',scope:'roof',shape:'ellipse',w:.9,d:.9,h:1.4,hint:'Chảo, cột ăng-ten'},
 {kind:'lightning',label:'Kim thu sét',group:'roof',scope:'roof',shape:'rect',w:.3,d:.3,h:3,hint:'Cột mảnh nhưng bóng dài; giữ khoảng cách an toàn'},
 {kind:'cooling',label:'Tháp giải nhiệt',group:'roof',scope:'roof',shape:'ellipse',w:2.5,d:2.5,h:3,hint:'Nhà xưởng, tòa nhà; có hơi ẩm, cần lối bảo trì'},
 {kind:'sign',label:'Biển quảng cáo',group:'roof',scope:'roof',shape:'rect',w:4,d:.4,h:3,hint:'Biển trên mái, khung thép'},
 {kind:'drying',label:'Giàn phơi đồ',group:'roof',scope:'roof',shape:'rect',w:3,d:1.5,h:1.8,hint:'Khu sân phơi giữ lại cho gia đình'},
 {kind:'tree_round',label:'Cây tán tròn',group:'around',scope:'neighbor',shape:'ellipse',w:5,d:5,h:7,hint:'Bàng, phượng, xoài…'},
 {kind:'tree_cone',label:'Cây dáng nón',group:'around',scope:'neighbor',shape:'ellipse',w:3,d:3,h:9,hint:'Thông, sao, dầu…'},
 {kind:'tree_palm',label:'Cây cau / dừa',group:'around',scope:'neighbor',shape:'ellipse',w:3.5,d:3.5,h:10,hint:'Thân cao, tán nhỏ'},
 {kind:'pole',label:'Cột điện và dây',group:'around',scope:'neighbor',shape:'ellipse',w:.4,d:.4,h:8.5,hint:'Cột bê tông 8,5 m; dây hạ thế'},
 {kind:'wall',label:'Tường cao nhà bên',group:'around',scope:'neighbor',shape:'rect',w:8,d:.2,h:7,hint:'Vách nhà liền kề cao hơn mái'},
 {kind:'tower',label:'Nhà cao tầng',group:'around',scope:'neighbor',shape:'rect',w:12,d:12,h:10*FLOOR,floors:10,hint:'10 tầng ≈ 33 m; nhập số tầng thật'},
 ...[1,2,3,4].map(n=>({kind:'house' as const,label:`Nhà ${n} tầng`,group:'around' as const,scope:'neighbor' as const,shape:'rect' as const,w:5,d:12,h:n*FLOOR,floors:n,hint:`Cao ≈ ${(n*FLOOR).toLocaleString('vi-VN',{maximumFractionDigits:1})} m`})),
]

/** New obstacle from a preset. index = how many objects of the same group already exist, so new ones
 * do not stack: roof objects step across the roof centre, surroundings go round the building
 * (right, below, left, above the drawing) 2 m from the roof edge. */
export function fromPreset(p:Preset,roofWidth:number,roofHeight:number,index=0):Obstacle{
 let x:number,y:number
 if(p.group==='roof'){x=Math.min(roofWidth-p.w,Math.max(0,roofWidth/2-p.w/2+((index%5)-2)*1.6));y=Math.min(roofHeight-p.d,Math.max(0,roofHeight/2-p.d/2+(Math.floor(index/5)%3-1)*1.6))}
 else{const side=index%4,slot=Math.floor(index/4)*7
  ;[x,y]=side===0?[roofWidth+2,roofHeight/2-p.d/2-slot]:side===1?[roofWidth/2-p.w/2+slot,-2-p.d]:side===2?[-2-p.w,roofHeight/2-p.d/2+slot]:[roofWidth/2-p.w/2-slot,roofHeight+2]}
 return {id:crypto.randomUUID(),label:p.label,kind:p.kind,x,y,
  width_m:p.w,depth_m:p.d,height_m:p.h,scope:p.scope,shape:p.shape,floors:p.floors??null,source:'manual',confidence:1,confirmed:false}
}
