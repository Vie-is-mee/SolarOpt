import {useEffect,useState} from 'react'
import type {Config,Design,Obstacle,Panel} from '../studioTypes'
import type {Economics} from '../economics'
import type {Electrical} from '../electricalTypes'
import {studioApi as api} from '../services/studioApi'
import {IMAGE_SOURCES,PURLINS,ROOF_MATERIALS,SECTION_ICONS,TERRAINS,datasheetOf,emptySurvey,panelFigures,warrantedEnd,type SiteReview as Review,type SiteSurvey,type WindZone} from '../siteSurvey'
import {CardHead} from './CardHead'
import {Icon} from './Icon'

const n=(v:number,d=1)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
const TONE={PASS:'green',WARN:'amber',FAIL:'red',INFO:''} as const
const WORD={PASS:'Đạt',WARN:'Lưu ý',FAIL:'Chưa đạt',INFO:'Việc cần làm'} as const
const month=()=>new Date().toISOString().slice(0,7)

type Props={config:Config;panel:Panel;obstacles:Obstacle[];design:Design;stale:boolean;survey:SiteSurvey|null;onSurvey:(s:SiteSurvey|null)=>void
 economics:Economics;onEconomics:(e:Economics)=>void;electrical:Electrical|null;inputKind:'drone'|'plan'|'partial';onConfig:(patch:Partial<Config>,note:string)=>void
 review:Review|null;onReview:(r:Review|null)=>void;disabled:boolean}

/** Site survey and the screening built on it: roof structure, wind, corrosion, fire safety, legal path, data quality.
 * The answers live in the project evidence; the electrical bill of materials and the economics follow them. */
export function SiteReview({config,panel,obstacles,design,stale,survey,onSurvey,economics,onEconomics,electrical,inputKind,onConfig,review,onReview,disabled}:Props){
 const [error,setError]=useState(''),[busy,setBusy]=useState(false)
 const s=survey??emptySurvey()
 const set=(patch:Partial<SiteSurvey>)=>onSurvey({...s,...patch})
 const sell=economics.sell_surplus!==false
 useEffect(()=>{
  if(disabled||stale){return}
  let live=true;setBusy(true)
  const id=setTimeout(()=>api.siteReview({config,panel,obstacles,design,survey,...panelFigures(panel),customer_type:economics.customer_type??'residential',sell_surplus:sell,ac_kw:electrical?.ac_kw??null,input_kind:inputKind,today:month()})
   .then(r=>{if(live){onReview(r);setError('')}}).catch(e=>{if(live)setError(e instanceof Error?e.message:'Chưa đánh giá được hiện trường.')}).finally(()=>{if(live)setBusy(false)}),300)
  return()=>{live=false;clearTimeout(id)}
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[config,panel,obstacles,design,survey,economics.customer_type,sell,electrical?.ac_kw,inputKind,stale,disabled])
 const m=review?.mounting
 const sheet=datasheetOf(panel)
 const sheetDegradation=sheet?(sheet.first_year_pct+sheet.yearly_pct*(sheet.power_years-1))/sheet.power_years:null
 const fireIssue=review?.sections.find(x=>x.id==='fire')?.items.some(i=>['exits','blocks','parapet'].includes(i.id)&&i.status!=='PASS')
 const num=(label:string,key:'roof_age_years'|'coast_km'|'foot_capacity_kn',unit:string,placeholder:string,step=1)=><label className="field"><span>{label}</span><div className="input-wrap"><input aria-label={label} type="number" min="0" step={step} value={s[key]??''} placeholder={placeholder} onChange={e=>set({[key]:e.target.value===''?null:Math.max(0,Number(e.target.value))})}/><small>{unit}</small></div></label>
 const check=(label:string,key:'roof_defects'|'industrial_air'|'pccc_listed'|'public_property'|'tilt_measured'|'site_visit',hint?:string)=><label className="check-line"><input type="checkbox" checked={!!s[key]} onChange={e=>set({[key]:e.target.checked})}/>{label}{hint&&<small className="muted-note"> · {hint}</small>}</label>
 return <section className="card site-review" aria-busy={busy}>
  <CardHead icon="building" title="Khảo sát hiện trường, an toàn và pháp lý" sub="Kết cấu mái, gió bão, ăn mòn, phòng cháy, thủ tục theo NĐ 58/2025 và độ tin cậy dữ liệu. Là bước sàng lọc; kỹ sư có chứng chỉ vẫn phải xác nhận tại chỗ."
   action={survey?<button type="button" className="text-button" onClick={()=>{onSurvey(null)}}>Bỏ khảo sát</button>:<button type="button" className="button secondary small" onClick={()=>onSurvey({...emptySurvey(),image_source:inputKind==='plan'?'drawing':null})}>Nhập khảo sát</button>}/>
  {!survey&&<p className="muted-note">Chưa có khảo sát: bảng vật tư dùng giả định chuẩn (chân đỡ 1,2 m, vật tư thường) và các mục dưới đây coi câu trả lời là “chưa biết”.</p>}
  {survey&&<details className="site-form" open>
   <summary>Câu trả lời khảo sát</summary>
   <h4 className="form-group-title">Mái</h4>
   <div className="field-grid three">
    <label className="field"><span>Vật liệu mái</span><select aria-label="Vật liệu mái" value={s.roof_material} onChange={e=>set({roof_material:e.target.value as SiteSurvey['roof_material']})}>{ROOF_MATERIALS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
    <label className="field"><span>Xà gồ</span><select aria-label="Xà gồ" value={s.purlin} onChange={e=>set({purlin:e.target.value as SiteSurvey['purlin']})}>{PURLINS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
    {num('Tuổi mái','roof_age_years','năm','Chưa biết')}
   </div>
   {check('Mái có rỉ sét, dột, võng hoặc nứt','roof_defects')}
   <h4 className="form-group-title">Gió bão và ăn mòn</h4>
   <div className="field-grid three">
    <label className="field"><span>Vùng áp lực gió (TCVN 2737:2023)</span><select aria-label="Vùng áp lực gió" value={s.wind_zone??''} onChange={e=>set({wind_zone:(e.target.value||null) as WindZone|null})}><option value="">Chưa tra{m?.zone_assumed?` (tạm vùng ${m.wind_zone})`:''}</option>{(['I','II','III','IV','V'] as WindZone[]).map(z=><option key={z} value={z}>Vùng {z}</option>)}</select><em>Tra theo xã/phường trong bảng phân vùng gió theo địa danh hành chính.</em></label>
    <label className="field"><span>Dạng địa hình</span><select aria-label="Dạng địa hình" value={s.terrain} onChange={e=>set({terrain:e.target.value as SiteSurvey['terrain']})}>{TERRAINS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
    {num('Khoảng cách tới biển','coast_km','km','Chưa biết',.1)}
    {num('Sức chịu kéo mỗi chân đỡ','foot_capacity_kn','kN',m?`Giả định ${n(m.foot_capacity_kn)}`:'Theo loại mái',.1)}
   </div>
   {check('Gần khu công nghiệp, nhà máy hóa chất hoặc đường xe tải lớn','industrial_air')}
   <h4 className="form-group-title">Pháp lý và phòng cháy</h4>
   {check('Công trình thuộc diện thẩm duyệt thiết kế PCCC','pccc_listed','khu công nghiệp, trường đại học, cảng hàng không…')}
   {check('Lắp trên tài sản công','public_property')}
   <label className="check-line"><input type="checkbox" checked={!s.grid_connected} onChange={e=>set({grid_connected:!e.target.checked})}/>Không đấu nối lưới điện quốc gia (độc lập)</label>
   <h4 className="form-group-title">Dữ liệu đầu vào</h4>
   <div className="field-grid three">
    <label className="field"><span>Nguồn ảnh mái</span><select aria-label="Nguồn ảnh mái" value={s.image_source??''} onChange={e=>set({image_source:(e.target.value||null) as SiteSurvey['image_source']})}><option value="">Theo loại tệp đã nạp</option>{IMAGE_SOURCES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
    <label className="field"><span>Tháng chụp ảnh</span><input aria-label="Tháng chụp ảnh" type="month" value={s.image_date??''} max={month()} onChange={e=>set({image_date:e.target.value||null})}/></label>
   </div>
   {check('Độ dốc mái đã đo tại chỗ (thước nghiêng trên điện thoại)','tilt_measured')}
   {check('Đã khảo sát hiện trường','site_visit')}
  </details>}
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {review&&m&&<>
   <div className="advisor-kpis site-kpis">
    <div><span>Tải thêm lên mái</span><strong>{n(review.dead_load_kg_m2)} kg/m²</strong><small>tổng {n(review.array_mass_kg,0)} kg</small></div>
    <div><span>Gió</span><strong>Vùng {m.wind_zone}{m.zone_assumed?' (tạm)':''}</strong><small>hút ở mép {n(m.q_edge_kpa*1000,0)} Pa</small></div>
    <div><span>Chân đỡ</span><strong>{n(m.foot_spacing_center_m)} / {n(m.foot_spacing_edge_m)} m</strong><small>giữa mái / vùng mép {n(m.edge_zone_m,2)} m</small></div>
    <div><span>Ăn mòn</span><strong>{m.corrosion_class}{m.corrosion_assumed?' (tạm)':''}</strong><small>{m.price_factor>1?`khung +${n((m.price_factor-1)*100,0)}%`:'vật tư thường'}</small></div>
    <div className="accent"><span>Thủ tục</span><strong>{review.legal_path.split(':')[0]}</strong><small>{review.legal_path.split(':')[1]?.trim()}</small></div>
   </div>
   {(m.recommended_setback_m>config.setback_m+1e-6||(fireIssue&&!config.fire_code))&&<div className="site-actions">
    {m.recommended_setback_m>config.setback_m+1e-6&&<button type="button" className="button secondary small" onClick={()=>onConfig({setback_m:m.recommended_setback_m},`Đã đặt lùi mép ${n(m.recommended_setback_m,2)} m theo vùng gió; tính lại phương án.`)}>Lùi mép {n(m.recommended_setback_m,2)} m theo vùng gió</button>}
    {fireIssue&&!config.fire_code&&<button type="button" className="button secondary small" onClick={()=>onConfig({fire_code:true},'Đã bật bố trí theo khuyến cáo PCCC (cách lối ra mái 3 m, nhóm ≤ 40 × 40 m); tính lại phương án.')}>Bố trí theo khuyến cáo PCCC</button>}
    <small className="muted-note">Đổi bố trí cần tính lại phương án ở bước 4.</small>
   </div>}
   {review.sections.map(sec=><details key={sec.id} className="site-section" open={sec.items.some(i=>i.status==='FAIL'||i.status==='WARN')}>
    <summary><Icon name={SECTION_ICONS[sec.id]} size={15}/>{sec.title}<span className="site-counts">{(['FAIL','WARN'] as const).map(k=>{const c=sec.items.filter(i=>i.status===k).length;return c?<span key={k} className={`badge ${TONE[k]}`}>{c} {WORD[k].toLowerCase()}</span>:null})}{sec.items.every(i=>i.status==='PASS'||i.status==='INFO')&&<span className="badge green">Ổn</span>}</span></summary>
    <div className="check-results">{sec.items.map(i=><div key={i.id}><span className={`check-symbol ${i.status==='INFO'?'pass':i.status.toLowerCase()}`}><Icon name={i.status==='PASS'?'check':i.status==='INFO'?'info':'alert'} size={14}/></span><div><strong>{i.label}</strong><p>{i.detail}</p>{i.source&&<small className="muted-note">Căn cứ: {i.source}</small>}</div><span className={`badge ${TONE[i.status]}`}>{WORD[i.status]}</span></div>)}</div>
   </details>)}
  </>}
  <details className="site-section">
   <summary><Icon name="shield" size={15}/>Bảo hành và tuổi thọ thiết bị</summary>
   <ul className="site-warranty">
    {sheet?<li>Tấm {panel.manufacturer} {panel.model}: bảo hành sản phẩm {sheet.product_years} năm; bảo hành công suất {sheet.power_years} năm, còn ≥ {n(warrantedEnd(sheet))}% (năm đầu giảm {n(sheet.first_year_pct)}%, sau đó {n(sheet.yearly_pct,2)}%/năm). <small className="muted-note">{sheet.source}.</small></li>
     :<li>Tấm {panel.manufacturer} {panel.model}: chưa có datasheet trong thư viện; nhập bảo hành theo phiếu của nhà phân phối.</li>}
    {sheetDegradation!=null&&<li>Dự toán đang tính suy giảm {economics.degradation_pct!=null?`${n(economics.degradation_pct,2)}%/năm (kỹ sư nhập)`:'0,55%/năm (tham khảo thị trường)'}; theo bảo hành tấm này bình quân {n(sheetDegradation,2)}%/năm.
     {economics.degradation_pct==null||Math.abs(economics.degradation_pct-sheetDegradation)>.005?<> <button type="button" className="text-button" onClick={()=>onEconomics({...economics,degradation_pct:Math.round(sheetDegradation*100)/100})}>Dùng theo bảo hành tấm</button></>:null}</li>}
    <li>Inverter: bảo hành tiêu chuẩn thường 5–10 năm tùy hãng và nhà phân phối; dự toán đã tính thay inverter năm {economics.replacement_year}.</li>
    <li>Ray, kẹp nhôm: thường 10–15 năm theo nhà cung cấp; vùng ven biển chọn vật tư theo cấp ăn mòn ở trên.</li>
   </ul>
  </details>
 </section>
}
