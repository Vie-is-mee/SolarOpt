import type {ProjectEvidence} from '../studioTypes'
export function EvidencePanel({evidence}:{evidence:ProjectEvidence}){
 const record=evidence.calibration
 if(!evidence.source_image&&!evidence.reference_image&&!record)return null
 return <details className="card evidence-panel"><summary>Ảnh và hồ sơ số đo · {evidence.source_name||'Ảnh dự án'}</summary>
  <p className="muted-note">Ảnh lưu trong gói dự án là ảnh đã chuẩn hóa hoặc hiệu chỉnh để trích biên. Tệp ảnh/PDF gốc và ảnh bổ sung cần được giữ riêng.</p>
  {record&&<><p>Ghi nhận lúc trích biên: {new Date(record.captured_at).toLocaleString('vi-VN')} · {record.method==='manual_image_trace'?'Biên kỹ sư chỉnh':'Biên từ công cụ xử lý ảnh'}.</p><p>Số đo khung bao đã nhập: {record.measured_width_m??'—'} × {record.measured_length_m??'—'} m. Khung suy từ ảnh: {record.result_width_m.toFixed(3)} × {record.result_height_m.toFixed(3)} m.</p><p>Đoạn tham chiếu: {record.reference_m??'chưa có'}{record.reference_m?' m':''} · đoạn kiểm tra: {record.check_m??'chưa có'}{record.check_m?' m':''}. Chênh khung: {record.frame_error_pct.toFixed(2)}%{record.check_error_pct!=null?` · chênh đoạn kiểm tra: ${record.check_error_pct.toFixed(2)}%`:''}.</p>
  {evidence.source_image&&<svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{width:'100%',maxWidth:640,aspectRatio:`${record.image_width_px}/${record.image_height_px}`}} aria-label="Ảnh và vị trí đoạn đo đã lưu"><image href={evidence.source_image} width="100" height="100" preserveAspectRatio="none"/>{[[record.reference_points,'#24d5ed'],[record.check_points,'#f09bef']].map(([points,color],i)=>{const pair=points as {x:number;y:number}[];return pair.length===2?<g key={i}><line x1={pair[0].x} y1={pair[0].y} x2={pair[1].x} y2={pair[1].y} stroke={String(color)} strokeWidth=".6"/>{pair.map((p,j)=><circle key={j} cx={p.x} cy={p.y} r=".8" fill={String(color)}/>)}</g>:null})}</svg>}
  <p className="muted-note">Xanh: đoạn tham chiếu; tím: đoạn kiểm tra. Hồ sơ ghi lại thời điểm trích ảnh; các thay đổi hình học sau đó vẫn cần đối chiếu và xác nhận lại.</p></>}
 </details>
}
