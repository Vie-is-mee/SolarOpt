import type {Scene} from '../studioTypes'
const range=(lo:number,hi:number)=>Math.abs(hi-lo)<.005?`${lo.toFixed(2)} m`:`${lo.toFixed(2)}–${hi.toFixed(2)} m`
const direction=(angle:number)=>['Bắc','Đông Bắc','Đông','Đông Nam','Nam','Tây Nam','Tây','Tây Bắc'][Math.round(((angle%360)+360)%360/45)%8]
export function ShadowInspector({scene,selected,onSelect,loading}:{scene:Scene|null;selected:string|null;onSelect:(id:string|null)=>void;loading:boolean}){
 if(!scene)return null
 const record=scene.obstacle_elevations?.find(o=>o.id===selected),day=scene.sun.altitude_deg>0
 const visible=scene.shadows.filter(s=>(s.area_m2??0)>.0005)
 return <section className="card shadow-inspector" aria-label="Giải thích bóng và cao độ">
  <h3>Đọc bóng che và cao độ</h3>
  <p>{loading?'Đang tính lại theo đầu vào mới…':day?`Nắng đến từ ${direction(scene.sun.azimuth_deg)}; bóng kéo về ${direction(scene.sun.azimuth_deg+180)} trên mặt bằng.`:'Mặt trời dưới chân trời: mái không có nắng trực tiếp. Vùng tối lúc này không quy cho riêng một vật cản.'}</p>
  <p className="muted-note">Bắc trên bản vẽ có thể đã xoay; dùng la bàn để đối chiếu. Chiều dài bóng phụ thuộc chênh cao với mặt mái nhận bóng, không chỉ chiều cao vật cản.</p>
  <label className="field"><span>Vật cản cần kiểm tra cao độ</span><select aria-label="Vật cản cần kiểm tra cao độ" value={selected&&scene.obstacle_elevations?.some(o=>o.id===selected)?selected:''} onChange={e=>onSelect(e.target.value||null)}><option value="">Chọn vật cản</option>{scene.obstacle_elevations?.map(o=><option value={o.id} key={o.id}>{o.label}</option>)}</select></label>
  {record&&<div className="object-elevation-summary" data-elevation-object={record.id}><p><strong>{record.label}</strong> · {record.source_label}</p><dl><div><dt>Cao độ chân từ mặt đất</dt><dd>{range(record.base_min_m,record.base_max_m)}</dd></div><div><dt>Chiều cao vật thể</dt><dd>{record.height_m.toFixed(2)} m</dd></div><div><dt>Cao độ đỉnh từ mặt đất</dt><dd>{range(record.top_min_m,record.top_max_m)}</dd></div></dl>{record.warnings.map((warning,i)=><p className="tracer-error" role="status" key={i}>{warning}</p>)}<p className="muted-note">Đổi chiều cao và cao độ chân ở bảng chỉnh hình học. Các giá trị này là dữ liệu mô phỏng đã nhập, chưa phải số đo được kiểm chứng tự động.</p></div>}
  {visible.length>0&&<><h4>Nguồn tạo bóng trên mái</h4><div className="shadow-source-list">{visible.map(s=><div key={s.id}><span>{s.label}</span><strong>{s.area_m2?.toFixed(2)} m²</strong></div>)}</div><p className="muted-note">Các bóng có thể chồng nhau; không cộng các dòng để suy ra tổng diện tích chịu bóng.</p></>}
  {scene.faces?.some(f=>f.direct_sunlight===false)&&day&&<p className="muted-note">Phần mái không nhận nắng trực tiếp: {scene.faces.filter(f=>f.direct_sunlight===false).map(f=>f.label).join(', ')}. Ánh sáng tán xạ vẫn có thể tới mái.</p>}
  {scene.notes.filter(n=>(n.includes('cao độ mặc định')||n.includes('bắc qua')||n.includes('thấp hơn mặt đất'))&&!(record&&n.startsWith(record.label+':'))).map((note,i)=><p key={i} className="tracer-error" role="status">{note}</p>)}
 </section>
}
