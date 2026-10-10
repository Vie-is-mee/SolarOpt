import type {Design} from '../studioTypes'

export function LayoutComparison({design}:{design:Design}){
 const trials=design.layout_trials||[],chosen=trials.find(t=>t.selected)
 if(!chosen)return null
 const coarse=trials.filter(t=>t.search_stage!=='refined').sort((a,b)=>b.objective_score-a.objective_score)[0]
 const refinedAngles=new Set(trials.filter(t=>t.search_stage==='refined').map(t=>t.angle_deg)).size>1
 const ordered=[...trials].sort((a,b)=>Number(b.selected)-Number(a.selected)||b.objective_score-a.objective_score)
 return <section className="card layout-comparison">
  <h3>So sánh hướng bố trí</h3>
  <p>Đã thử {trials.length} lưới. Chọn góc <strong>{chosen.angle_deg}°</strong>, dịch lưới {chosen.offset_x_m} × {chosen.offset_y_m} m, theo điểm mục tiêu đang chọn.</p>
  {coarse&&trials.some(t=>t.search_stage==='refined')&&<p className="muted-note">Đã tinh chỉnh {refinedAngles?'góc ±1°/±2° và ':''}pha dịch ¼ bước lưới. So với lượt tìm ban đầu: {coarse.panel_count} → {chosen.panel_count} tấm, {coarse.annual_energy_kwh.toLocaleString('vi-VN')} → {chosen.annual_energy_kwh.toLocaleString('vi-VN')} kWh/năm. Chọn theo điểm mục tiêu, có xét giữ vị trí khi sửa.</p>}
  <p className="muted-note">Mỗi phương án giữ cùng một hướng hàng pin. 0° là tấm dọc theo trục bản vẽ, 90° là tấm ngang. Hướng cạnh mái được suy từ biên đã xác nhận.</p>
  <details><summary>Xem các cách xếp đã so sánh</summary><div className="layout-table-wrap"><table><thead><tr><th>Góc</th><th>Dịch lưới (m)</th><th>Tấm</th><th>kWh/năm</th><th>Kết quả</th></tr></thead><tbody>{ordered.map((t,i)=><tr key={i} className={t.selected?'chosen-layout':''}><td>{t.angle_deg}°</td><td>{t.offset_x_m} / {t.offset_y_m}</td><td>{t.panel_count}</td><td>{t.annual_energy_kwh.toLocaleString('vi-VN')}</td><td>{t.selected?'Được chọn':t.panel_count?'Đã so sánh':'Không chọn được tấm'}</td></tr>)}</tbody></table></div></details>
  <p className="muted-note">Đây là phương án tốt nhất theo điểm mục tiêu trong các lưới đã thử; chưa thử trộn nhiều hướng trong cùng bố trí hoặc mô phỏng điện theo từng giờ.</p>
 </section>
}
