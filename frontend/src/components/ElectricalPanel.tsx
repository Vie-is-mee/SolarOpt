import {Fragment, useEffect, useMemo, useRef, useState} from 'react'
import {BOM_GROUPS, STRING_COLOURS, estimateFromBom, type BomGroup, type Electrical, type ElectricalSettings, type Inverter} from '../electricalTypes'
import type {Economics} from '../economics'
import type {Config, Design, Obstacle, Panel} from '../studioTypes'
import {footprint} from '../editorGeometry'
import {studioApi as api} from '../services/studioApi'
import {withReferenceCosts} from '../sizing'
import {CardHead} from './CardHead'
import type {SiteSurvey} from '../siteSurvey'
import {Icon} from './Icon'

const n=(v:number,d=1)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
const money=(v:number)=>Math.round(v).toLocaleString('vi-VN')+' đ'
const million=(v:number)=>n(v/1e6,1)+' triệu đ'
const STATUS={PASS:['Đạt','green'],WARN:['Lưu ý','amber'],FAIL:['Chưa đạt','red']} as const
const INVERTER_FIELDS:[keyof Inverter,string,string][]=[['ac_rated_w','Công suất AC','W'],['max_dc_power_w','Công suất DC tối đa','W'],['max_dc_voltage_v','Điện áp DC tối đa','V'],['mppt_min_v','MPPT thấp nhất','V'],['mppt_max_v','MPPT cao nhất','V'],['start_voltage_v','Điện áp khởi động','V'],['mppt_count','Số MPPT',''],['strings_per_mppt','Chuỗi mỗi MPPT',''],['max_current_per_mppt_a','Dòng tối đa mỗi MPPT','A'],['max_short_circuit_per_mppt_a','Dòng ngắn mạch mỗi MPPT','A'],['price_vnd','Giá','đ']]

/** String map: panels coloured by string, the wiring order drawn through panel centres, + and − at the ends. */
function StringMap({config,design,obstacles,result}:{config:Config;design:Design;obstacles:Obstacle[];result:Electrical}){
 const roof=config.roof_polygon.length?config.roof_polygon:[{x:0,y:0},{x:config.roof_width_m,y:0},{x:config.roof_width_m,y:config.roof_height_m},{x:0,y:config.roof_height_m}]
 const xs=[...roof.map(p=>p.x),...design.panels.flatMap(p=>[p.x,p.x+p.width_m])],ys=[...roof.map(p=>p.y),...design.panels.flatMap(p=>[p.y,p.y+p.height_m])]
 const [x0,x1,y0,y1]=[Math.min(...xs),Math.max(...xs),Math.min(...ys),Math.max(...ys)],pad=.6
 const byId=new Map(design.panels.map(p=>[p.id,p])),colourOf=new Map<string,string>()
 result.strings.forEach((s,i)=>s.panel_ids.forEach(id=>colourOf.set(id,STRING_COLOURS[i%STRING_COLOURS.length])))
 const centre=(id:string)=>{const p=byId.get(id)!;return [p.x+p.width_m/2,p.y+p.height_m/2]}
 const font=Math.max(.35,Math.min(x1-x0,y1-y0)/20)
 return <svg className="string-map" viewBox={`${x0-pad} ${y0-pad} ${x1-x0+2*pad} ${y1-y0+2*pad}`} role="img" aria-label="Sơ đồ đấu chuỗi">
  <polygon points={roof.map(p=>`${p.x},${p.y}`).join(' ')} fill="#f4f1ea" stroke="#9aa79f" strokeWidth={font*.12}/>
  {config.roof_faces.map(f=><polygon key={f.id} points={f.polygon.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke="#c3c9bf" strokeWidth={font*.08} strokeDasharray={`${font*.4} ${font*.25}`}/>)}
  {obstacles.filter(o=>o.scope==='roof').map(o=>{const pts=footprint(o);return <g key={o.id}><polygon points={pts.map(p=>`${p.x},${p.y}`).join(' ')} fill="#c4bcae" fillOpacity=".55" stroke="#8f8676" strokeWidth={font*.06}/><text x={pts.reduce((s,p)=>s+p.x,0)/pts.length} y={pts.reduce((s,p)=>s+p.y,0)/pts.length} fontSize={font*.55} fill="#5b5346" textAnchor="middle" dominantBaseline="central">{o.label}</text></g>})}
  {design.panels.map(p=>{const c=colourOf.get(p.id);return <rect key={p.id} x={p.x} y={p.y} width={p.width_m} height={p.height_m} rx=".04" transform={`rotate(${p.rotation_deg||0} ${p.x+p.width_m/2} ${p.y+p.height_m/2})`} fill={c||'#d9dcd6'} fillOpacity={c?.28:.7} stroke={c||'#9a9f99'} strokeWidth={font*.09} strokeDasharray={c?undefined:`${font*.25} ${font*.18}`}><title>{c?result.strings.find(s=>s.panel_ids.includes(p.id))!.id:'Chưa đấu nối'}</title></rect>})}
  {result.strings.map((s,i)=>{const pts=s.panel_ids.map(centre),c=STRING_COLOURS[i%STRING_COLOURS.length],[sx,sy]=pts[0],[ex,ey]=pts[pts.length-1];return <g key={s.id} data-string={s.id}>
   <polyline points={pts.map(p=>p.join(',')).join(' ')} fill="none" stroke={c} strokeWidth={font*.16} strokeLinejoin="round" strokeLinecap="round"/>
   <circle cx={sx} cy={sy} r={font*.55} fill={c}/><text x={sx} y={sy} fill="#fff" fontSize={font*.62} fontWeight="700" textAnchor="middle" dominantBaseline="central">+</text>
   <circle cx={ex} cy={ey} r={font*.55} fill="#fff" stroke={c} strokeWidth={font*.14}/><text x={ex} y={ey} fill={c} fontSize={font*.7} fontWeight="700" textAnchor="middle" dominantBaseline="central">−</text>
   <text x={sx} y={sy-font*1.05} fill={c} fontSize={font*.8} fontWeight="700" textAnchor="middle" stroke="#fff" strokeWidth={font*.18} paintOrder="stroke">{s.id}</text>
  </g>})}
 </svg>
}

export function ElectricalPanel({config,panel,design,obstacles,stale,result,onResult,settings,onSettings,economics,onEconomics,disabled,survey=null,siteKey=''}:{config:Config;panel:Panel;design:Design;obstacles:Obstacle[];stale:boolean;result:Electrical|null;onResult:(r:Electrical|null)=>void;settings:ElectricalSettings;onSettings:(s:ElectricalSettings)=>void;economics:Economics;onEconomics:(e:Economics)=>void;disabled:boolean;survey?:SiteSurvey|null;siteKey?:string}){
 const [catalog,setCatalog]=useState<Inverter[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[pushed,setPushed]=useState(''),[rerun,setRerun]=useState(false)
 useEffect(()=>{api.inverters().then(setCatalog).catch(()=>setCatalog([]))},[])
 const set=(patch:Partial<ElectricalSettings>)=>onSettings({...settings,...patch})
 // The layout and site inputs of the last automatic attempt: retry only when they change, never in a loop on errors.
 const attempted=useRef<{design:Design;siteKey:string}|null>(null)
 async function run(){
  if(stale||!design.panels.length)return
  attempted.current={design,siteKey}
  setBusy(true);setError('');setPushed('')
  try{onResult(await api.electrical(config,panel,design,settings,{survey,zero_export:economics.sell_surplus===false}))}catch(e){setError(e instanceof Error?e.message:'Chưa thiết kế được phần điện.')}finally{setBusy(false)}
 }
 useEffect(()=>{if(rerun){setRerun(false);void run()}},[settings,rerun])
 function pick(id:string){set({inverter_id:id,custom_inverter:null});setRerun(true)}
 const dcKwp=design.metrics.peak_power_kwp
 // First visit with a fresh layout: design once with the current settings; later changes wait for the button.
 // Also after the survey or the export choice changed (the app drops the result that no longer matches them).
 useEffect(()=>{const a=attempted.current;if(!result&&!busy&&!stale&&!disabled&&design.panels.length&&(a?.design!==design||a.siteKey!==siteKey))void run()},[design,stale,disabled,siteKey,busy,result==null])
 const choice=settings.custom_inverter?'custom':settings.inverter_id||''
 function choose(v:string){
  if(v==='custom'){const base=result?.inverter||catalog[0];set({inverter_id:null,custom_inverter:base?{...base,id:'custom',manufacturer:'Tự nhập',model:base.model+' (chỉnh)',source:'Kỹ sư nhập theo datasheet'}:null})}
  else set({inverter_id:v||null,custom_inverter:null})
 }
 const groups=useMemo(()=>{const out:Partial<Record<BomGroup,Electrical['bom']>>={};result?.bom.forEach(b=>{(out[b.group]??=[]).push(b)});return out},[result])
 const perKwp=economics.cost_mode==='per_kwp'
 function push(){
  if(!result)return
  const items=estimateFromBom(result),inverterCost=result.cost_by_group.inverter||0
  // The bill of materials prices equipment line by line, so the estimate switches to itemised; lines it cannot
  // price (labour, survey, paperwork) take the reference unit prices and are labelled as such.
  onEconomics(withReferenceCosts({...economics,cost_mode:'itemized',costs:economics.costs.map(c=>items.find(i=>i.name===c.name)??c),replacement_cost:economics.replacement_cost??Math.round(inverterCost),source:economics.source||'Vật tư điện theo thiết kế điện SolarOpt (đơn giá tham khảo)'},design.metrics.peak_power_kwp))
  setPushed(`Đã đưa ${items.map(i=>`${i.name.toLowerCase()} ${million(i.amount)}`).join(', ')} vào dự toán`+(economics.replacement_cost==null?`; chi phí thay inverter năm ${economics.replacement_year} lấy bằng giá inverter.`:'.'))
 }
 // The estimate took the BOM earlier and the BOM has changed since (survey, export choice, inverter): say so.
 const outdated=!!result&&economics.cost_mode==='itemized'&&estimateFromBom(result).some(i=>{const c=economics.costs.find(c=>c.name===i.name);return c!=null&&c.amount!=null&&Math.abs(c.amount-i.amount)>=1})
 const counted=result?result.bom.filter(b=>b.group!=='panel').reduce((s,b)=>s+b.amount_vnd,0):0
 return <section className="card electrical-panel" aria-busy={busy}>
  <CardHead icon="bolt" title="Thiết kế điện" sub="Chia chuỗi, chọn inverter và kiểm tra giới hạn điện áp, dòng điện theo nhiệt độ" action={<button type="button" className="button secondary small" disabled={busy||stale||disabled} onClick={run}>{busy?'Đang tính…':result?'Tính lại':'Thiết kế điện'}</button>}/>
  {stale&&<p className="tracer-error">Bố trí đã thay đổi; tính lại phương án trước khi thiết kế điện.</p>}
  <div className="field-grid three electrical-settings">
   <label className="field"><span>Inverter</span><select aria-label="Inverter" value={choice} onChange={e=>choose(e.target.value)}><option value="">Tự chọn phù hợp nhất</option>{(['single','three'] as const).map(ph=><optgroup key={ph} label={ph==='single'?'1 pha':'3 pha'}>{catalog.filter(i=>i.phase===ph).map(i=><option key={i.id} value={i.id}>{i.manufacturer} {i.model} · {n(i.ac_rated_w/1000)} kW</option>)}</optgroup>)}<option value="custom">Nhập inverter khác…</option></select></label>
   <label className="field"><span>Lưới điện</span><select aria-label="Lưới điện" value={settings.grid_phase} onChange={e=>set({grid_phase:e.target.value as ElectricalSettings['grid_phase']})}><option value="auto">Tự động theo quy mô</option><option value="single">1 pha</option><option value="three">3 pha</option></select></label>
   <label className="field"><span>Giới hạn công suất AC đấu nối</span><div className="input-wrap"><input aria-label="Giới hạn công suất AC" type="number" min="0" step="1" value={settings.max_ac_kw??''} placeholder="Không giới hạn" onChange={e=>set({max_ac_kw:e.target.value===''?null:Number(e.target.value)})}/><small>kW</small></div><em>Theo công suất đăng ký/thỏa thuận đấu nối với điện lực hoặc công suất máy biến áp.</em></label>
   <label className="field"><span>Nhiệt độ thấp nhất tại công trình</span><div className="input-wrap"><input aria-label="Nhiệt độ thấp nhất" type="number" min="-40" max="40" step="1" value={settings.min_ambient_c??''} placeholder={Math.abs(config.latitude)>=20?'Mặc định 2':Math.abs(config.latitude)>=16?'Mặc định 8':'Mặc định 15'} onChange={e=>set({min_ambient_c:e.target.value===''?null:Number(e.target.value)})}/><small>°C</small></div></label>
  </div>
  <details className="electrical-assumptions"><summary>Thông số nhiệt, dòng ngắn mạch và chiều dài cáp</summary><div className="field-grid three">
   {([['max_ambient_c','Nhiệt độ cao nhất','°C',1],['cell_rise_c','Tấm nóng hơn môi trường','°C',1],['voc_coeff_pct','Hệ số nhiệt Voc','%/°C',.01],['vmp_coeff_pct','Hệ số nhiệt Pmax (Vmp)','%/°C',.01],['home_run_m','Cáp DC tới inverter (mỗi cực)','m',1],['ac_run_m','Cáp AC tới tủ điện chính','m',1]] as [keyof ElectricalSettings,string,string,number][]).map(([k,label,unit,step])=><label className="field" key={k}><span>{label}</span><div className="input-wrap"><input aria-label={label} type="number" step={step} value={settings[k] as number} onChange={e=>e.target.value!==''&&set({[k]:Number(e.target.value)})}/><small>{unit}</small></div></label>)}
   <label className="field"><span>Điện áp lưới đo lúc trưa</span><div className="input-wrap"><input aria-label="Điện áp lưới đo lúc trưa" type="number" min="180" max="280" step="0.1" value={settings.grid_voltage_v??''} placeholder="Chưa đo" onChange={e=>set({grid_voltage_v:e.target.value===''?null:Number(e.target.value)})}/><small>V</small></div><em>Pha–trung tính ở tủ điện, 11–13h, khi hệ chưa chạy.</em></label>
   <label className="field"><span>Isc của tấm (datasheet)</span><div className="input-wrap"><input aria-label="Isc của tấm" type="number" min="0" step=".01" value={settings.isc_a??''} placeholder={`Ước tính ${n(panel.imp_a*1.05,2)}`} onChange={e=>set({isc_a:e.target.value===''?null:Number(e.target.value)})}/><small>A</small></div></label>
  </div></details>
  {settings.custom_inverter&&<div className="electrical-custom"><h4 className="form-group-title">Inverter tự nhập (theo datasheet)</h4><div className="field-grid three">
   <label className="field"><span>Hãng và model</span><input aria-label="Model inverter" value={settings.custom_inverter.model} onChange={e=>set({custom_inverter:{...settings.custom_inverter!,model:e.target.value}})}/></label>
   <label className="field"><span>Số pha</span><select aria-label="Số pha inverter" value={settings.custom_inverter.phase} onChange={e=>set({custom_inverter:{...settings.custom_inverter!,phase:e.target.value as Inverter['phase']}})}><option value="single">1 pha</option><option value="three">3 pha</option></select></label>
   {INVERTER_FIELDS.map(([k,label,unit])=><label className="field" key={k}><span>{label}</span><div className="input-wrap"><input aria-label={label} type="number" min="0" value={settings.custom_inverter![k] as number} onChange={e=>e.target.value!==''&&set({custom_inverter:{...settings.custom_inverter!,[k]:Number(e.target.value)}})}/>{unit&&<small>{unit}</small>}</div></label>)}
  </div></div>}
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {result&&<div className="electrical-result">
   <p className={'electrical-summary '+(result.valid?'ok':'fail')}><Icon name={result.valid?'check':'alert'} size={15}/>{result.summary}</p>
   <div className="advisor-kpis">
    <div><span>Inverter</span><strong>{result.inverter_count} × {n(result.inverter.ac_rated_w/1000)} kW</strong><small>{result.inverter.manufacturer} {result.inverter.model}</small></div>
    <div><span>DC / AC</span><strong>{n(result.dc_ac_ratio,2)}</strong><small>{n(result.dc_kwp,2)} kWp / {n(result.ac_kw,1)} kW</small></div>
    <div><span>Chuỗi</span><strong>{result.strings.length} chuỗi</strong><small>cho phép {result.string_min}–{result.string_max} tấm/chuỗi</small></div>
    <div><span>Voc lúc lạnh nhất</span><strong>{result.strings.length?n(Math.max(...result.strings.map(s=>s.voc_cold_v)),0)+' V':'—'}</strong><small>giới hạn {n(result.inverter.max_dc_voltage_v,0)} V</small></div>
    <div className="accent"><span>Vật tư điện và khung</span><strong>{million(counted)}</strong><small>chưa gồm tấm pin</small></div>
   </div>
   <div className="electrical-map-wrap"><StringMap config={config} design={design} obstacles={obstacles} result={result}/>
    <ul className="string-legend">{result.strings.map((s,i)=><li key={s.id}><i style={{background:STRING_COLOURS[i%STRING_COLOURS.length]}}/><b>{s.id}</b> {s.length} tấm · INV{s.inverter+1}/MPPT{s.mppt+1}</li>)}{result.unassigned_panel_ids.length>0&&<li className="unwired"><i/>{result.unassigned_panel_ids.length} tấm chưa đấu nối</li>}<li className="map-note">Đường nối chỉ thứ tự đấu tấm, không phải tuyến đi dây thực tế.</li></ul>
   </div>
   <div className="table-scroll"><table className="data-table"><caption>Các chuỗi · điện áp tính ở nhiệt độ thấp nhất và cao nhất</caption>
    <thead><tr><th>Chuỗi</th><th>Inverter / MPPT</th><th>Mặt mái</th><th className="num">Tấm</th><th className="num">Voc lạnh</th><th className="num">Vmp nóng</th><th className="num">Vmp lạnh</th><th className="num">Imp</th><th className="num">Cáp DC</th></tr></thead>
    <tbody>{result.strings.map(s=><tr key={s.id}><td className="strong">{s.id}</td><td>INV{s.inverter+1} · MPPT{s.mppt+1}</td><td>{s.orientation}</td><td className="num">{s.length}</td><td className="num">{n(s.voc_cold_v)} V</td><td className="num">{n(s.vmp_hot_v)} V</td><td className="num">{n(s.vmp_cold_v)} V</td><td className="num">{n(s.imp_a,2)} A</td><td className="num">{n(s.cable_m,0)} m</td></tr>)}</tbody></table></div>
   <h4 className="form-group-title">Kiểm tra giới hạn điện</h4>
   <div className="check-results">{result.checks.map(c=><div key={c.id}><span className={`check-symbol ${c.status.toLowerCase()}`}><Icon name={c.status==='PASS'?'check':'alert'} size={14}/></span><div><strong>{c.label}</strong><p>{c.detail}</p></div><span className={`badge ${STATUS[c.status][1]}`}>{STATUS[c.status][0]}</span></div>)}</div>
   <h4 className="form-group-title">Bảng vật tư (BOM)</h4>
   <div className="table-scroll"><table className="data-table bom-table"><thead><tr><th>Hạng mục</th><th>Quy cách</th><th className="num">SL</th><th className="num">Đơn giá</th><th className="num">Thành tiền</th></tr></thead>
    <tbody>{(Object.keys(BOM_GROUPS) as BomGroup[]).filter(g=>groups[g]).map(g=><Fragment key={g}><tr className="bom-group"><td colSpan={4}>{BOM_GROUPS[g]}</td><td className="num">{money(result.cost_by_group[g]||0)}</td></tr>{groups[g]!.map(b=><tr key={g+b.name}><td>{b.name}</td><td>{b.spec}</td><td className="num">{n(b.quantity)} {b.unit}</td><td className="num">{money(b.unit_price_vnd)}</td><td className="num">{money(b.amount_vnd)}</td></tr>)}</Fragment>)}</tbody></table></div>
   <div className="electrical-push">
    <button type="button" className="button primary small" disabled={!result.strings.length} onClick={push}><Icon name="check" size={15}/>Đưa vật tư vào dự toán</button>
    {outdated&&!pushed&&<p className="tracer-error" role="status">Bảng vật tư đã thay đổi so với dự toán (khảo sát, chọn bán điện dư hoặc inverter); bấm để cập nhật dự toán.</p>}
    <p className="muted-note">{pushed||(perKwp?'Dự toán đang theo suất đầu tư trọn gói; bấm để chuyển sang dự toán theo hạng mục với giá vật tư này.':'')||'Điền giá inverter, dây và bảo vệ, khung ray vào các hạng mục tương ứng của dự toán. Giá là đơn giá tham khảo, thay bằng báo giá thật khi có.'}</p>
   </div>
   {result.options.length>0&&<><h4 className="form-group-title">Chọn inverter theo công suất dự án ({n(dcKwp,2)} kWp DC → nên {n(dcKwp/1.35,1)}–{n(dcKwp/0.9,1)} kW AC)</h4>
   <div className="table-scroll"><table className="data-table inverter-options"><caption>Mỗi model đã được chia chuỗi và kiểm tra giới hạn cho đúng hệ này; xếp theo mức phù hợp</caption><thead><tr><th>Inverter</th><th>Lưới</th><th className="num">Số bộ</th><th className="num">Tổng AC</th><th className="num">DC/AC</th><th className="num">Giá tham khảo</th><th>Kết quả</th><th/></tr></thead>
    <tbody>{result.options.map(o=><tr key={o.inverter_id} className={o.inverter_id===result.inverter.id?'picked':''}><td>{o.label}</td><td>{o.phase==='single'?'1 pha':'3 pha'}</td><td className="num">{o.count}</td><td className="num">{n(o.ac_kw,1)} kW</td><td className="num">{n(o.dc_ac_ratio,2)}</td><td className="num">{million(o.price_vnd)}</td><td>{o.feasible?<span className="badge green">Đạt</span>:<span className="badge red">Chưa đạt</span>} <small>{o.note}</small></td><td>{o.inverter_id===result.inverter.id?<span className="badge">Đang dùng</span>:<button type="button" className="text-button" disabled={busy||stale||disabled} onClick={()=>pick(o.inverter_id)}>Chọn</button>}</td></tr>)}</tbody></table></div></>}
   <details className="advisor-more"><summary>Giả định và nguồn thông số</summary><ul>{result.assumptions.map((a,i)=><li key={i}>{a}</li>)}<li>Nguồn inverter: {result.inverter.source}.</li></ul></details>
  </div>}
 </section>
}
