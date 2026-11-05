import {useId} from 'react'
import type {CalibrationRecord,Config,Design,Obstacle,Objective,Panel,Point,Scene,Stress,Verification} from '../studioTypes'
import {CAPEX_LABEL,calculateEconomics,type Economics} from '../economics'
import {ScenarioTable,scenarioSummary} from './ScenarioTable'
import {LOSS_ITEMS} from '../yieldLosses'
import {LOAD_PROFILES} from '../loadProfiles'
import {footprint,outerRoof} from '../editorGeometry'
import {panelCorners,panelLabel} from '../layoutMeasurements'
import {faceSummary,lossBreakdown,lossColor,niceStep,shadingHistogram} from '../reportData'
import {vnd} from '../format'
import {OBJECTIVES} from './DesignOptions'
import {InstallationGuide,type Datum} from './InstallationGuide'
import type {Electrical} from '../electricalTypes'
import {datasheetOf,warrantedEnd,type SiteReview,type SiteSurvey} from '../siteSurvey'
import '../report.css'

export type ReportProps={config:Config;panel:Panel;obstacles:Obstacle[];design:Design|null;options:Partial<Record<Objective,Design>>;objective:Objective;
 verification:Verification|null;stress:Stress|null;economics:Economics;datum:Datum;scene:Scene|null;approved:number|null;sample:boolean;stale:boolean;confirmed:boolean;
 irradianceSource:string;aiNote:string;calibration:CalibrationRecord|null;electrical?:Electrical|null;siteReview?:SiteReview|null;siteSurvey?:SiteSurvey|null}

const num=(n:number,d=0)=>n.toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d})
const kwhText=(n:number)=>n>=10000?`${num(n/1000,1)} MWh`:`${num(n)} kWh`
const MONTHS=['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12']
const MOUNT:Record<string,string>={flush:'Áp sát mặt mái',tilted_rack:'Giá nghiêng trên mái bằng',tracker:'Giá xoay một trục'}
const STATUS:Record<string,[string,string]>={PASS:['Đạt','pass'],WARN:['Cảnh báo','warn'],FAIL:['Không đạt','fail'],INFO:['Việc cần làm','pass']}
const ring=(points:Point[])=>points.reduce((s,p,i)=>{const q=points[(i+1)%points.length];return s+p.x*q.y-q.x*p.y},0)/2
const objectiveName=(id:Objective)=>OBJECTIVES.find(o=>o.id===id)?.name??id

function Sheet({title,eyebrow,project,children,className=''}:{title:string;eyebrow:string;project:string;children:React.ReactNode;className?:string}){
 return <section className={'rp-sheet '+className}>
  <header className="rp-running"><img src="/solaropt-mark.svg" alt=""/><span>SolarOpt</span><span>{project}</span></header>
  <p className="rp-eyebrow">{eyebrow}</p><h2 className="rp-title">{title}</h2>{children}
 </section>
}
const Kpi=({label,value,unit,note}:{label:string;value:string;unit?:string;note?:string})=><div className="rp-kpi"><span>{label}</span><strong>{value}{unit&&<small> {unit}</small>}</strong>{note&&<em>{note}</em>}</div>
const Chip=({status}:{status:string})=>{const [text,kind]=STATUS[status]??[status,'warn'];return <span className={'rp-chip '+kind}>{text}</span>}

/** Plan of the roof with every panel coloured by its annual shading loss. */
export function PanelMap({config,obstacles,design,labels=true}:{config:Config;obstacles:Obstacle[];design:Design;labels?:boolean}){
 const roof=outerRoof(config),onRoof=obstacles.filter(o=>o.scope!=='neighbor').map(o=>({o,pts:footprint(o)}))
 const all=[...roof,...onRoof.flatMap(v=>v.pts)],xs=all.map(p=>p.x),ys=all.map(p=>p.y)
 const span=Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys),1),pad=span*.07
 const minx=Math.min(...xs)-pad,maxx=Math.max(...xs)+pad,miny=Math.min(...ys)-pad,maxy=Math.max(...ys)+pad
 const W=1000,s=W/(maxx-minx),H=(maxy-miny)*s,X=(x:number)=>(x-minx)*s,Y=(y:number)=>(maxy-y)*s
 const path=(pts:Point[])=>'M'+pts.map(p=>`${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join('L')+'Z'
 const bar=niceStep((maxx-minx)/4,1),font=Math.max(9,Math.min(16,s*.32))
 // The report renders twice (print copy and preview), so the hatch pattern id must be unique.
 const hatch='rp-hatch'+useId().replace(/:/g,'')
 const panels=design.panels.map((p,i)=>({p,i,c:panelCorners(p)})),showLabels=labels&&panels.length<=160&&s*Math.min(design.panels[0]?.width_m??1,design.panels[0]?.height_m??1)>=22
 return <svg className="rp-map" viewBox={`0 0 ${W} ${H.toFixed(1)}`} role="img" aria-label="Mặt bằng bố trí tấm pin tô màu theo tổn thất bóng">
  <defs><pattern id={hatch}width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#e4dfd3"/><line x1="0" y1="0" x2="0" y2="8" stroke="#b9b0a0" strokeWidth="2"/></pattern></defs>
  <path d={path(roof)+(config.roof_openings||[]).map(path).join('')} fill="#f4f6f1" fillRule="evenodd" stroke="#153e30" strokeWidth="2.5"/>
  {(config.roof_faces||[]).map(f=><path key={f.id} d={path(f.polygon)} fill="none" stroke="#9fb3a8" strokeWidth="1.2" strokeDasharray="6 4"/>)}
  {onRoof.map(({o,pts})=><g key={o.id}><path d={path(pts)} fill={`url(#${hatch})`} stroke="#8a8273" strokeWidth="1.5"/>
   {o.width_m*s>70&&<text x={X(o.x+o.width_m/2)} y={Y(o.y+o.depth_m/2)+4} className="rp-map-obstacle">{o.label}</text>}</g>)}
  {panels.map(({p,i,c})=><g key={p.id}><path d={path(c)} fill={lossColor(p.shading_loss_pct)} stroke="#fff" strokeWidth="1.2"/>
   {showLabels&&<text x={X(p.x+p.width_m/2)} y={Y(p.y+p.height_m/2)+font/3} fontSize={font} className="rp-map-label">{panelLabel(i).slice(1)}</text>}</g>)}
  <g transform={`translate(${W-46},44) rotate(${-config.north_rotation_deg})`}><circle r="26" fill="#fff" stroke="#c9d3cc"/><path d="M0,-20L8,8L0,3L-8,8Z" fill="#153e30"/><text y="-28" className="rp-map-north" transform={`rotate(${config.north_rotation_deg},0,-31)`}>B</text></g>
  <g transform={`translate(24,${(H-22).toFixed(1)})`}><rect width={bar*s} height="7" fill="#153e30"/><rect width={bar*s/2} height="7" fill="#fff" stroke="#153e30"/><text x={bar*s+8} y="8" className="rp-map-scale">{num(bar,bar<1?1:0)} m</text></g>
 </svg>
}

function LossLegend(){return <div className="rp-legend"><span>Tổn thất bóng cả năm của từng tấm</span>{[0,2.5,5,7.5,10].map(v=><i key={v} style={{background:lossColor(v)}}>{v===10?'≥ 10%':num(v,v%1?1:0)+'%'}</i>)}</div>}

function MonthlyChart({values}:{values:number[]}){
 const W=640,H=230,L=48,B=28,T=30,max=Math.max(...values,1),step=niceStep(max),top=Math.ceil(max/step)*step,bw=(W-L-8)/12
 const y=(v:number)=>T+(H-T-B)*(1-v/top)
 return <svg className="rp-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Điện năng theo tháng">
  {Array.from({length:Math.round(top/step)+1},(_,i)=>i*step).map(v=><g key={v}><line x1={L} x2={W-4} y1={y(v)} y2={y(v)} className="rp-grid"/><text x={L-6} y={y(v)+4} className="rp-axis end">{num(v)}</text></g>)}
  {values.map((v,i)=><g key={i}><rect x={L+i*bw+5} y={y(v)} width={bw-10} height={Math.max(0,y(0)-y(v))} rx="3" className="rp-bar"/>
   <text x={L+i*bw+bw/2} y={y(v)-5} className="rp-value">{num(v)}</text><text x={L+i*bw+bw/2} y={H-8} className="rp-axis mid">{MONTHS[i]}</text></g>)}
  <text x={4} y={12} className="rp-axis">kWh</text>
 </svg>
}

function Waterfall({ideal,shading,system,delivered}:{ideal:number;shading:number;system:number;delivered:number}){
 const W=640,H=210,T=26,B=40,L=12,top=ideal*1.06||1,y=(v:number)=>T+(H-T-B)*(1-v/top),cw=(W-L*2)/4
 const steps=[{label:'Bức xạ trên mặt tấm × kWp',a:0,b:ideal,kind:'base'},{label:'Bóng che',a:ideal-shading,b:ideal,kind:'loss'},{label:'Hệ thống (1 − PR)',a:delivered,b:ideal-shading,kind:'loss'},{label:'Điện năng phát',a:0,b:delivered,kind:'result'}]
 const pct=(v:number)=>ideal?` (${num(v/ideal*100,1)}%)`:''
 return <svg className="rp-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Sơ đồ tổn thất điện năng">
  <line x1={L} x2={W-L} y1={y(0)} y2={y(0)} className="rp-grid"/>
  {steps.map((s,i)=>{const x=L+i*cw+cw*.18,w=cw*.64,v=s.b-s.a;return <g key={s.label}>
   <rect x={x} y={y(s.b)} width={w} height={Math.max(1.5,y(s.a)-y(s.b))} rx="3" className={'rp-wf '+s.kind}/>
   {i<3&&<line x1={x+w} x2={x+cw} y1={y(i===0?s.b:s.a)} y2={y(i===0?s.b:s.a)} className="rp-wf-link"/>}
   <text x={x+w/2} y={y(s.b)-7} className="rp-value">{s.kind==='loss'?'− ':''}{kwhText(v)}{s.kind==='loss'?pct(v):''}</text>
   <text x={x+w/2} y={H-18} className="rp-axis mid">{s.label}</text></g>})}
 </svg>
}

function CashflowChart({rows,payback}:{rows:{year:number;net:number;cumulative:number}[];payback:number|null}){
 const W=640,H=240,L=58,B=26,T=28,vals=rows.flatMap(r=>[r.net,r.cumulative,0]),lo=Math.min(...vals),hi=Math.max(...vals)
 const step=niceStep(Math.max(hi-lo,1),5),bottom=Math.floor(lo/step)*step,top=Math.ceil(hi/step)*step||step
 const y=(v:number)=>T+(H-T-B)*(top-v)/(top-bottom),bw=(W-L-8)/rows.length,x=(i:number)=>L+i*bw+bw/2
 return <svg className="rp-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Dòng tiền theo năm và lũy kế">
  {Array.from({length:Math.round((top-bottom)/step)+1},(_,i)=>bottom+i*step).map(v=><g key={v}><line x1={L} x2={W-4} y1={y(v)} y2={y(v)} className={v===0?'rp-zero':'rp-grid'}/><text x={L-6} y={y(v)+4} className="rp-axis end">{num(v/1e6)}</text></g>)}
  {rows.map((r,i)=><rect key={r.year} x={x(i)-bw*.32} width={bw*.64} y={Math.min(y(r.net),y(0))} height={Math.max(1,Math.abs(y(r.net)-y(0)))} className={r.net>=0?'rp-bar':'rp-bar neg'}/>)}
  <path d={'M'+rows.map((r,i)=>`${x(i).toFixed(1)},${y(r.cumulative).toFixed(1)}`).join('L')} className="rp-line"/>
  {payback!==null&&<g><line x1={x(0)+payback*bw} x2={x(0)+payback*bw} y1={T} y2={H-B} className="rp-marker"/><text x={x(0)+payback*bw+5} y={T+10} className="rp-axis">Hoàn vốn ≈ {num(payback,1)} năm</text></g>}
  {rows.filter(r=>r.year%5===0).map(r=><text key={r.year} x={x(r.year)} y={H-8} className="rp-axis mid">Năm {r.year}</text>)}
  <text x={4} y={12} className="rp-axis">triệu đ</text>
 </svg>
}

export function ProjectReport(p:ReportProps){
 const {config,panel,design,economics}=p,project=config.project_name||'Dự án SolarOpt',today=new Date().toLocaleDateString('vi-VN')
 const roof=outerRoof(config),area=Math.abs(ring(roof))-(config.roof_openings||[]).reduce((s,h)=>s+Math.abs(ring(h)),0)
 const faceLabels=Object.fromEntries([...(config.roof_faces||[]).map(f=>[f.id,f.label]),...(p.scene?.faces||[]).map(f=>[f.id,f.label])])
 const m=design?.metrics,specific=m&&m.peak_power_kwp?m.annual_energy_kwh/m.peak_power_kwp:0
 const site=design?{profile:design.month_hour_kwh,latitude:config.latitude}:null
 const econ=design?calculateEconomics(economics,m!.estimated_cost_vnd,m!.annual_energy_kwh,m!.peak_power_kwp,site):null,perKwp=economics.cost_mode==='per_kwp',econReady=!!econ&&!econ.missing.length
 const E=econ?.resolved??economics,range=design&&econReady?scenarioSummary(economics,m!.estimated_cost_vnd,m!.annual_energy_kwh,m!.peak_power_kwp,site):null
 const losses=design?lossBreakdown(design.panels,config.performance_ratio):null,faces=design?faceSummary(design.panels,panel.power_w,faceLabels):[]
 const efficiency=panel.power_w/(panel.width_m*panel.height_m*1000)*100
 const status=p.stale?'Kết quả cũ: đầu vào đã thay đổi sau lần tính':p.approved?`Kỹ sư đã duyệt · bản #${p.approved}`:p.confirmed?'Đầu vào đã xác nhận · chưa lưu bản duyệt':'Đầu vào chưa xác nhận'
 const checks=p.verification?.checks??[],passed=checks.filter(c=>c.status==='PASS').length
 const summary=design&&m?[
  `Phương án “${objectiveName(design.objective??p.objective)}” đặt ${num(m.panel_count)} tấm ${panel.manufacturer} ${panel.model} (${num(m.peak_power_kwp,2)} kWp) trên mái khoảng ${num(area,1)} m².`,
  `Điện năng sơ bộ ${num(m.annual_energy_kwh)} kWh/năm, tương đương ${num(specific)} kWh cho mỗi kWp.`,
  `Bóng che làm giảm trung bình ${num(m.average_shading_loss_pct,1)}% sản lượng mỗi tấm; tấm bị che nhiều nhất mất ${num(m.maximum_shading_loss_pct??0,1)}%.`,
  econReady&&range?`Kinh tế theo ba kịch bản (thuận lợi – thận trọng): ${range.text}`:'Phần kinh tế chưa đủ số liệu đầu vào nên chưa tính hoàn vốn.',
  checks.length?`Kiểm tra tự động: ${passed}/${checks.length} điều kiện đạt.`:'Chưa chạy kiểm tra tự động.',
 ].join(' '):'Chưa có phương án bố trí. Báo cáo chỉ gồm dữ liệu đầu vào.'
 const rows=econ?econ.rows.filter(r=>r.year<=3||r.year%5===0||r.year===economics.replacement_year||r.year===econ.rows.length-1):[]

 return <div className="project-report">
  <section className="rp-sheet rp-cover">
   <div className="rp-brand"><img src="/solaropt-mark.svg" alt=""/><div><strong>SolarOpt</strong><span>Báo cáo thiết kế điện mặt trời mái nhà</span></div></div>
   <p className="rp-eyebrow">Báo cáo thiết kế sơ bộ · {today}</p>
   <h1>{project}</h1>
   <p className="rp-meta">{num(config.latitude,4)}° B, {num(config.longitude,4)}° Đ · khung mái {num(config.roof_width_m,2)} × {num(config.roof_height_m,2)} m</p>
   <div className="rp-badges"><span className={p.approved&&!p.stale?'ok':p.stale?'bad':''}>{status}</span>{p.sample&&<span className="bad">Dữ liệu mẫu minh họa</span>}</div>
   {design&&m?<>
    <div className="rp-kpis">
     <Kpi label="Công suất lắp đặt" value={num(m.peak_power_kwp,2)} unit="kWp" note={`${num(m.panel_count)} tấm × ${num(panel.power_w)} W`}/>
     <Kpi label="Điện năng năm đầu" value={num(m.annual_energy_kwh)} unit="kWh" note="sơ bộ, trời quang quy đổi"/>
     <Kpi label="Sản lượng riêng" value={num(specific)} unit="kWh/kWp"/>
     <Kpi label="Tổn thất bóng TB" value={num(m.average_shading_loss_pct,1)} unit="%" note={`cao nhất ${num(m.maximum_shading_loss_pct??0,1)}%`}/>
     <Kpi label="Tổng đầu tư" value={econReady?vnd(econ!.total):'—'} note={econReady&&econ!.costPerKwp!==null?`${num(econ!.costPerKwp/1e6,1)} triệu đ/kWp`:'chưa nhập đủ chi phí'}/>
     <Kpi label="Hoàn vốn (cơ sở)" value={econReady&&econ!.payback!==null?num(econ!.payback,1):'—'} unit={econReady&&econ!.payback!==null?'năm':undefined} note={econReady&&range?`khoảng ${range.scenarios[2].result.payback!=null?num(range.scenarios[2].result.payback!,1):'—'}–${range.scenarios[0].result.payback!=null?num(range.scenarios[0].result.payback!,1):`>${economics.years}`} năm`:undefined}/>
    </div>
    <figure className="rp-cover-map"><PanelMap config={config} obstacles={p.obstacles} design={design} labels={false}/><LossLegend/></figure>
   </>:null}
   <div className="rp-summary"><h3>Tóm tắt</h3><p>{summary}</p></div>
   <p className="rp-disclaimer">Bản sơ bộ phục vụ đánh giá phương án. Cần kỹ sư có chuyên môn kiểm tra kết cấu, đấu nối điện và phòng cháy trước khi thi công.</p>
  </section>

  <Sheet title="Dữ liệu đầu vào và phương án" eyebrow="01 · Công trình" project={project}>
   <div className="rp-two">
    <table className="rp-table"><caption>Công trình</caption><tbody>
     <tr><th>Vị trí</th><td>{num(config.latitude,4)}° B, {num(config.longitude,4)}° Đ</td></tr>
     <tr><th>Khung mái</th><td>{num(config.roof_width_m,2)} × {num(config.roof_height_m,2)} m · diện tích mái {num(area,1)} m²</td></tr>
     <tr><th>Mặt mái</th><td>{config.roof_faces?.length?`${config.roof_faces.length} mặt mái khai báo riêng`:`Một mặt, dốc ${num(config.roof_tilt_deg,1)}°, hướng ${num(config.roof_azimuth_deg)}°`}</td></tr>
     <tr><th>Cao độ mái</th><td>{num(config.roof_elevation_m,2)} m so với mặt đất</td></tr>
     {(config.roof_faces||[]).some(f=>f.tilt_deg>1)&&<tr><th>Diện tích mái thật (theo độ dốc)</th><td>{num((config.roof_faces||[]).reduce((t,f)=>t+Math.abs(ring(f.polygon))/Math.cos(f.tilt_deg*Math.PI/180),0),1)} m² trên mặt mái, so với {num((config.roof_faces||[]).reduce((t,f)=>t+Math.abs(ring(f.polygon)),0),1)} m² mặt bằng; tấm, khe và khoảng lùi trên mặt dốc được đo theo chiều dài thật trên mái</td></tr>}<tr><th>Hướng bản vẽ</th><td>Trục +Y lệch {num(config.north_rotation_deg,1)}° so với hướng Bắc (theo chiều kim đồng hồ)</td></tr>
     <tr><th>Cách lắp</th><td>{MOUNT[config.mounting??'flush']}{config.mounting==='tilted_rack'?` · nghiêng ${num(config.rack_tilt_deg??0)}°, hướng ${num(config.rack_azimuth_deg??180)}°`:''}</td></tr>
     <tr><th>Khoảng cách</th><td>Lùi mép {num(config.setback_m,2)} m · khe tấm {num(config.panel_gap_m,2)} m · cách vật cản {num(config.obstacle_clearance_m,2)} m</td></tr>
     <tr><th>Nguồn kích thước</th><td>{config.dimensions_source==='reference'?'Hiệu chuẩn theo đoạn tham chiếu':config.dimensions_source==='measured'?'Số đo thực tế do người dùng nhập':'Giả định, chưa đối chiếu'}{p.calibration?` · chênh khung ${num(p.calibration.frame_error_pct,1)}%`:''}{config.dimensions_verified?' · kỹ sư đã đối chiếu':''}</td></tr>
     <tr><th>Dữ liệu nắng</th><td>{config.weather?`${config.weather.source} · ${num(config.weather.annual_ghi_kwh_m2)} kWh/m²/năm mặt ngang, mây và nhiệt độ theo từng giờ`:`${num(config.annual_irradiance_kwh_m2)} kWh/m²/năm · ${p.irradianceSource} · mô hình trời quang`}</td></tr>
     <tr><th>Hệ số hiệu năng (PR)</th><td>{num(config.performance_ratio*100)}%{config.yield_losses?` = tích các tổn thất: ${LOSS_ITEMS.map(i=>`${i.label.toLowerCase()} ${num(config.yield_losses![i.key],1)}%`).join(', ')}`:' (một hệ số chung)'}</td></tr>
    </tbody></table>
    <table className="rp-table"><caption>Tấm pin</caption><tbody>
     <tr><th>Hãng / mẫu</th><td>{panel.manufacturer} {panel.model}</td></tr>
     <tr><th>Kích thước</th><td>{num(panel.width_m,3)} × {num(panel.height_m,3)} m</td></tr>
     <tr><th>Công suất</th><td>{num(panel.power_w)} Wp · hiệu suất {num(efficiency,1)}%</td></tr>
     <tr><th>Voc / Vmp</th><td>{num(panel.voc_v,1)} V / {num(panel.vmp_v,1)} V</td></tr>
     <tr><th>Imp</th><td>{num(panel.imp_a,2)} A</td></tr>
     <tr><th>Đơn giá tấm</th><td>{vnd(panel.price_vnd)}</td></tr>
     <tr><th>Ngân sách tấm pin</th><td>{vnd(config.budget_vnd)}</td></tr>
    </tbody></table>
   </div>
   {Object.keys(p.options).length>0&&<table className="rp-table rp-data"><caption>So sánh các phương án đã tính</caption>
    <thead><tr><th>Phương án</th><th className="num">Số tấm</th><th className="num">kWp</th><th className="num">kWh/năm</th><th className="num">kWh/kWp</th><th className="num">Bóng TB</th><th className="num">Chi phí tấm pin</th></tr></thead>
    <tbody>{OBJECTIVES.filter(o=>p.options[o.id]).map(o=>{const d=p.options[o.id]!,mm=d.metrics;return <tr key={o.id} className={o.id===(design?.objective??p.objective)?'rp-selected':''}>
     <td>{o.name}{o.id===(design?.objective??p.objective)?' · đã chọn':''}{o.id==='min_cost'&&d.target_met===false?' · chưa đạt mục tiêu':''}</td><td className="num">{num(mm.panel_count)}</td><td className="num">{num(mm.peak_power_kwp,2)}</td><td className="num">{num(mm.annual_energy_kwh)}</td><td className="num">{mm.peak_power_kwp?num(mm.annual_energy_kwh/mm.peak_power_kwp):'—'}</td><td className="num">{num(mm.average_shading_loss_pct,1)}%</td><td className="num">{vnd(mm.estimated_cost_vnd)}</td></tr>})}</tbody></table>}
   {p.obstacles.length>0&&<table className="rp-table rp-data"><caption>Vật cản và công trình lân cận</caption>
    <thead><tr><th>Tên</th><th className="num">X / Y (m)</th><th className="num">Rộng × sâu (m)</th><th className="num">Cao (m)</th><th>Xác nhận</th></tr></thead>
    <tbody>{p.obstacles.map(o=><tr key={o.id}><td>{o.label}</td><td className="num">{num(o.x,2)} / {num(o.y,2)}</td><td className="num">{num(o.width_m,2)} × {num(o.depth_m,2)}</td><td className="num">{num(o.height_m,2)} {o.scope==='neighbor'?'từ đất':'trên mái'}</td><td>{o.confirmed?'Có':'Chưa'}</td></tr>)}</tbody></table>}
  </Sheet>

  {design&&m&&losses&&<>
   <Sheet title="Bố trí tấm pin và bóng che" eyebrow="02 · Mặt bằng" project={project}>
    <figure className="rp-figure"><PanelMap config={config} obstacles={p.obstacles} design={design}/><LossLegend/>
     <figcaption>Số trên tấm là mã tấm (P001…). Màu là tổn thất bóng cả năm của tấm đó; vùng gạch chéo là vật cản trên mái, nét đứt là ranh giới các mặt mái.</figcaption></figure>
    <table className="rp-table rp-data"><caption>Theo mặt mái</caption>
     <thead><tr><th>Mặt mái</th><th className="num">Số tấm</th><th className="num">kWp</th><th className="num">kWh/năm</th><th className="num">kWh/kWp</th><th className="num">Bóng TB</th></tr></thead>
     <tbody>{faces.map(f=><tr key={f.id}><td>{f.label}</td><td className="num">{num(f.count)}</td><td className="num">{num(f.kwp,2)}</td><td className="num">{num(f.kwh)}</td><td className="num">{f.kwp?num(f.kwh/f.kwp):'—'}</td><td className="num">{num(f.loss,1)}%</td></tr>)}</tbody>
     {faces.length>1&&<tfoot><tr><td>Tổng</td><td className="num">{num(m.panel_count)}</td><td className="num">{num(m.peak_power_kwp,2)}</td><td className="num">{num(m.annual_energy_kwh)}</td><td className="num">{num(specific)}</td><td className="num">{num(m.average_shading_loss_pct,1)}%</td></tr></tfoot>}</table>
    <p className="rp-note">Bố trí được chọn trong {num(design.layout_trials?.length??0)} lưới đã thử{design.layout_trials?.find(t=>t.selected)?`, góc ${num(design.layout_trials.find(t=>t.selected)!.angle_deg,1)}° trên bản vẽ`:''}; tận dụng {num(m.roof_utilization_pct,1)}% diện tích khung mái. Đây là tối ưu trong các lưới đã thử, không phải mọi cách xếp có thể.</p>
   </Sheet>

   <Sheet title="Sản lượng và tổn thất" eyebrow="03 · Điện năng" project={project}>
    {design.monthly_energy_kwh?.length===12?<figure className="rp-figure"><h3>Điện năng theo tháng</h3><MonthlyChart values={design.monthly_energy_kwh}/>
     <figcaption>Tổng năm chia theo tháng bằng bức xạ trời quang của từng mặt mái; tổn thất bóng tính theo năm. Cho thấy tính mùa vụ, không phải dự báo thời tiết từng tháng.</figcaption></figure>
     :<p className="rp-note">Tính lại phương án để có điện năng theo tháng.</p>}
    <figure className="rp-figure"><h3>Từ bức xạ đến điện năng</h3><Waterfall {...losses}/>
     <figcaption>Hệ thống gồm nhiệt độ tấm, dây dẫn, bộ biến đổi điện và bụi bẩn, gộp trong hệ số PR {num(config.performance_ratio*100)}%{config.yield_losses?' (tách từng khoản ở bảng thông số)':''}.</figcaption></figure>
    <div className="rp-two">
     <table className="rp-table rp-data rp-hist"><caption>Phân bố tổn thất bóng theo tấm</caption><thead><tr><th>Tổn thất</th><th className="num">Số tấm</th><th></th></tr></thead>
      <tbody>{shadingHistogram(design.panels).map((b,i)=><tr key={b.label}><td>{b.label}</td><td className="num">{num(b.count)}</td><td><i style={{width:`${m.panel_count?b.count/m.panel_count*100:0}%`,background:lossColor([0,2,4,7.5,10][i])}}/></td></tr>)}</tbody></table>
     <table className="rp-table"><caption>Chỉ số điện năng</caption><tbody>
      <tr><th>Điện năng năm đầu</th><td>{num(m.annual_energy_kwh)} kWh</td></tr>
      <tr><th>Sản lượng riêng</th><td>{num(specific)} kWh/kWp</td></tr>
      <tr><th>Bức xạ trên mặt tấm</th><td>{m.peak_power_kwp?num(losses.ideal/m.peak_power_kwp):'—'} kWh/kWp</td></tr>
      <tr><th>Tổn thất bóng</th><td>{num(losses.ideal?losses.shading/losses.ideal*100:0,1)}% điện năng · {num(m.average_shading_loss_pct,1)}% TB mỗi tấm</td></tr>
      <tr><th>Tháng cao / thấp nhất</th><td>{design.monthly_energy_kwh?.length===12?(()=>{const v=design.monthly_energy_kwh!,hi=v.indexOf(Math.max(...v)),lo=v.indexOf(Math.min(...v));return `${MONTHS[hi]} ${num(v[hi])} · ${MONTHS[lo]} ${num(v[lo])} kWh`})():'—'}</td></tr>
     </tbody></table>
    </div>
   </Sheet>

   <Sheet title="Hiệu quả kinh tế" eyebrow="04 · Kinh tế" project={project}>
    {econReady&&econ?<>
     {econ.hourly&&<p className="rp-note">Tự dùng tính theo từng giờ: nhu cầu {num(econ.hourly.loadKwh/12)} kWh/tháng kiểu “{LOAD_PROFILES.find(x=>x.id===(economics.load_profile??''))?.label??'mặc định theo loại khách'}”; dùng tại chỗ {num(econ.hourly.selfPct)}% sản lượng, đáp ứng {num(econ.hourly.coveragePct)}% nhu cầu, mỗi kWh tự dùng tiết kiệm {num(econ.hourly.buyPrice)} đ (theo biểu giá EVN QĐ 2892/QĐ-BCT, cao điểm 17h30–22h30).</p>}
     {range&&<><h3>Ba kịch bản: thận trọng · cơ sở · thuận lợi</h3><ScenarioTable scenarios={range.scenarios} years={economics.years} compact/><p className="rp-note">Thận trọng: vốn +15%, sản lượng −12%, tự dùng −15 điểm, không được trả tiền điện dư, giá điện không tăng thêm. Thuận lợi: vốn −10%, sản lượng +5%, tự dùng +10 điểm. Các số dưới đây theo kịch bản cơ sở.</p></>}
     <div className="rp-kpis small">
      <Kpi label="Tổng đầu tư" value={vnd(econ.total)} note={econ.costPerKwp!==null?`${num(econ.costPerKwp/1e6,1)} triệu đ/kWp · ≈ ${num(econ.costPerKwp/1e6,1)} tỷ đ/MWp`:undefined}/>
      <Kpi label="Hoàn vốn" value={econ.payback!==null?num(econ.payback,1)+' năm':'Chưa hoàn vốn'}/>
      <Kpi label={`NPV (${num(E.discount_pct??0,1)}%)`} value={vnd(econ.npv)}/>
      <Kpi label={`Lợi ích ròng ${economics.years} năm`} value={vnd(econ.netBenefit)}/>
     </div>
     <figure className="rp-figure"><h3>Dòng tiền {economics.years} năm</h3><CashflowChart rows={econ.rows} payback={econ.payback}/><figcaption>Cột: dòng tiền ròng từng năm (đỏ là năm âm). Đường cam: lũy kế từ năm 0.</figcaption></figure>
     <div className="rp-two">
      <table className="rp-table rp-data"><caption>Chi phí đầu tư</caption><tbody>{perKwp?<>
       <tr><td>{CAPEX_LABEL} (EPC, đã gồm thuế)</td><td className="num">{num(E.capex_million_per_kwp??0,1)} triệu đ/kWp</td></tr>
       <tr><td>Công suất hệ</td><td className="num">{num(m.peak_power_kwp,2)} kWp</td></tr>
       <tr className="sub"><td colSpan={2}>Ước tính theo suất đầu tư trọn gói; chưa tách thiết bị, thi công, lãi nhà thầu và thuế.</td></tr>
      </>:<>
       <tr><td>Tấm pin ({num(m.panel_count)} tấm)</td><td className="num">{vnd(m.estimated_cost_vnd)}</td></tr>
       {economics.costs.map(c=><tr key={c.name}><td>{c.name}</td><td className="num">{vnd(c.amount??0)}</td></tr>)}
       <tr className="sub"><td>Dự phòng {num(E.contingency_pct??0,1)}%</td><td className="num">{vnd(econ.contingency)}</td></tr>
       <tr className="sub"><td>Lãi đơn vị lắp đặt {num(E.markup_pct??0,1)}%</td><td className="num">{vnd(econ.profit)}</td></tr>
       <tr className="sub"><td>Thuế {num(E.vat_pct??0,1)}%</td><td className="num">{vnd(econ.tax)}</td></tr>
      </>}</tbody><tfoot><tr><td>Tổng đầu tư</td><td className="num">{vnd(econ.total)}</td></tr></tfoot></table>
      <table className="rp-table"><caption>Giả định kinh tế</caption><tbody>
       <tr><th>Giá điện tránh mua</th><td>{num(E.buy_price??0)} đ/kWh · tăng {num(E.price_growth_pct??0,1)}%/năm</td></tr>
       <tr><th>Dùng tại chỗ</th><td>{num(E.self_use_pct??0)}% · điện dư {num(E.sell_price??0)} đ/kWh</td></tr>
       <tr><th>Suy giảm sản lượng</th><td>{num(E.degradation_pct??0,1)}%/năm</td></tr>
       <tr><th>Vận hành, bảo trì</th><td>{vnd(E.maintenance_year??0)}/năm</td></tr>
       <tr><th>Thay thiết bị</th><td>{vnd(E.replacement_cost??0)} ở năm {economics.replacement_year}</td></tr>
       <tr><th>Vay</th><td>{(E.loan_amount??0)>0?`${vnd(E.loan_amount!)} · ${num(E.loan_rate_pct??0,1)}%/năm · ${economics.loan_years} năm`:'Không vay'}</td></tr>
       <tr><th>Chiết khấu</th><td>{num(E.discount_pct??0,1)}%/năm · {economics.years} năm</td></tr>
       <tr><th>Nguồn giá</th><td>{E.source}</td></tr>
      </tbody></table>
     </div>
     <table className="rp-table rp-data rp-keep"><caption>Dòng tiền rút gọn (triệu đồng)</caption>
      <thead><tr><th>Năm</th><th className="num">Điện năng (kWh)</th><th className="num">Tiết kiệm</th><th className="num">Bán điện dư</th><th className="num">Vận hành</th><th className="num">Trả nợ</th><th className="num">Ròng</th><th className="num">Lũy kế</th></tr></thead>
      <tbody>{rows.map(r=><tr key={r.year}><td>{r.year}</td><td className="num">{num(r.energy)}</td><td className="num">{num(r.saving/1e6,1)}</td><td className="num">{num(r.exportRevenue/1e6,1)}</td><td className="num">{num((r.maintenance+r.replacement)/1e6,1)}</td><td className="num">{num(r.debt/1e6,1)}</td><td className={'num'+(r.net<0?' neg':'')}>{num(r.net/1e6,1)}</td><td className={'num'+(r.cumulative<0?' neg':'')}>{num(r.cumulative/1e6,1)}</td></tr>)}</tbody></table>
    </>:<div className="rp-empty"><h3>Chưa đủ số liệu để tính hiệu quả kinh tế</h3><p>Nhập ở bước Phương án các mục còn thiếu: {econ?.missing.join(', ')}. Báo cáo không tự giả định giá thiết bị hay giá điện.</p></div>}
   </Sheet>

   {p.electrical&&<Sheet title="Thiết kế điện sơ bộ" eyebrow="05 · Điện" project={project}>
    <div className="rp-kpis"><Kpi label="Inverter" value={`${p.electrical.inverter_count} × ${num(p.electrical.inverter.ac_rated_w/1000,1)}`} unit="kW" note={`${p.electrical.inverter.manufacturer} ${p.electrical.inverter.model}`}/><Kpi label="DC/AC" value={num(p.electrical.dc_ac_ratio,2)} note={`${num(p.electrical.dc_kwp,2)} kWp`}/><Kpi label="Số chuỗi" value={num(p.electrical.strings.length)} note={`${p.electrical.string_min}–${p.electrical.string_max} tấm/chuỗi`}/></div>
    <table className="rp-table rp-data"><caption>Chuỗi pin</caption><thead><tr><th>Chuỗi</th><th>Inverter / MPPT</th><th className="num">Tấm</th><th className="num">Voc lạnh</th><th className="num">Vmp nóng</th><th>Tấm trong chuỗi</th></tr></thead>
     <tbody>{p.electrical.strings.map(s=><tr key={s.id}><td>{s.id}</td><td>INV{s.inverter+1} · MPPT{s.mppt+1}</td><td className="num">{s.length}</td><td className="num">{num(s.voc_cold_v)} V</td><td className="num">{num(s.vmp_hot_v)} V</td><td>{s.panel_ids.map(id=>panelLabel(design.panels.findIndex(x=>x.id===id))).join(' → ')}</td></tr>)}</tbody></table>
    <table className="rp-table rp-data"><caption>Kiểm tra giới hạn điện</caption><thead><tr><th>Điều kiện</th><th>Kết quả</th><th>Chi tiết</th></tr></thead>
     <tbody>{p.electrical.checks.map(c=><tr key={c.id}><td>{c.label}</td><td><Chip status={c.status}/></td><td>{c.detail}</td></tr>)}</tbody></table>
    <table className="rp-table rp-data"><caption>Vật tư điện và khung (đơn giá tham khảo)</caption><thead><tr><th>Hạng mục</th><th>Quy cách</th><th className="num">SL</th><th className="num">Thành tiền (triệu đ)</th></tr></thead>
     <tbody>{p.electrical.bom.filter(b=>b.group!=='panel').map(b=><tr key={b.group+b.name}><td>{b.name}</td><td>{b.spec}</td><td className="num">{num(b.quantity,1)} {b.unit}</td><td className="num">{num(b.amount_vnd/1e6,2)}</td></tr>)}</tbody></table>
    <ul className="rp-list">{p.electrical.assumptions.map((a,i)=><li key={i}>{a}</li>)}</ul>
   </Sheet>}

   {p.siteReview&&<Sheet title="Hiện trường, an toàn và pháp lý" eyebrow="Sàng lọc trước khảo sát chi tiết" project={project}>
    <div className="rp-kpis"><Kpi label="Tải thêm lên mái" value={num(p.siteReview.dead_load_kg_m2,1)} unit="kg/m²" note={`tổng ${num(p.siteReview.array_mass_kg)} kg`}/><Kpi label="Vùng gió" value={p.siteReview.mounting.wind_zone+(p.siteReview.mounting.zone_assumed?' (tạm)':'')} note={`chân đỡ ${num(p.siteReview.mounting.foot_spacing_center_m,1)} / ${num(p.siteReview.mounting.foot_spacing_edge_m,1)} m`}/><Kpi label="Ăn mòn" value={p.siteReview.mounting.corrosion_class} note={p.siteReview.mounting.rail_spec}/></div>
    <p className="rp-note"><strong>Thủ tục:</strong> {p.siteReview.legal_path}.{p.siteSurvey?'':' Chưa nhập khảo sát hiện trường: các mục dưới coi câu trả lời là chưa biết.'}</p>
    {p.siteReview.sections.map(sec=><table key={sec.id} className="rp-table rp-data"><caption>{sec.title}</caption><thead><tr><th>Hạng mục</th><th>Kết quả</th><th>Chi tiết và căn cứ</th></tr></thead>
     <tbody>{sec.items.map(i=><tr key={i.id}><td>{i.label}</td><td><Chip status={i.status}/></td><td>{i.detail}{i.source&&<em className="rp-source"> Căn cứ: {i.source}.</em>}</td></tr>)}</tbody></table>)}
    {(()=>{const d=datasheetOf(p.panel);return <ul className="rp-list"><li>Bảo hành tấm {p.panel.manufacturer} {p.panel.model}: {d?`sản phẩm ${d.product_years} năm; công suất ${d.power_years} năm, còn ≥ ${num(warrantedEnd(d),1)}% (${d.source})`:'chưa có datasheet trong thư viện, ghi theo phiếu bảo hành'}.</li><li>Inverter: bảo hành tiêu chuẩn thường 5–10 năm; dòng tiền đã tính thay inverter năm {economics.replacement_year}.</li></ul>})()}
   </Sheet>}

   <Sheet title="Kiểm tra và độ tin cậy" eyebrow={p.electrical?'06 · Kiểm chứng':'05 · Kiểm chứng'} project={project}>
    {checks.length?<table className="rp-table rp-data"><caption>Điều kiện kiểm tra tự động ({passed}/{checks.length} đạt)</caption>
     <thead><tr><th>Điều kiện</th><th>Kết quả</th><th>Chi tiết</th></tr></thead>
     <tbody>{checks.map(c=><tr key={c.id}><td>{c.label}</td><td><Chip status={c.status}/></td><td>{c.detail}</td></tr>)}</tbody></table>:<p className="rp-note">Chưa chạy kiểm tra tự động cho phương án này.</p>}
    {p.stress?<table className="rp-table rp-data"><caption>Thử sai số trên bố trí đã chọn ({p.stress.passed}/{p.stress.total} đạt)</caption>
     <thead><tr><th>Tình huống</th><th>Kết quả</th><th className="num">Số tấm</th><th className="num">kWh/năm</th><th>Ghi chú</th></tr></thead>
     <tbody>{p.stress.scenarios.map(s=><tr key={s.id}><td>{s.name}</td><td><Chip status={s.status}/></td><td className="num">{num(s.panel_count)}</td><td className="num">{num(s.annual_energy_kwh)}</td><td>{s.detail}</td></tr>)}</tbody></table>:<p className="rp-note">Chưa chạy thử sai số.</p>}
    {design.warnings.length>0&&<div className="rp-warnings"><h3>Lưu ý từ bộ tính</h3><ul>{design.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></div>}
   </Sheet>
  </>}

  <Sheet title="Giả định, giới hạn và xác nhận" eyebrow={p.electrical&&design?'07 · Phạm vi':'06 · Phạm vi'} project={project}>
   <ul className="rp-list">
    <li>Bức xạ năm quy đổi riêng cho từng mặt mái bằng pvlib với 12 ngày trời quang đại diện; bóng che tính cho mọi giờ có nắng của 12 ngày đó (khoảng 140 thời điểm), trên lưới khoảng 10 cm. Mỗi tấm được xét theo 3 chuỗi cell có diode bypass: chuỗi bị che 1/3 diện tích thì mất toàn bộ phần trực xạ; tổn thất được tính theo trực xạ từng giờ, ánh sáng tán xạ coi như không bị che. Chưa phải mô phỏng 8.760 giờ với thời tiết thực.</li>
    <li>Tổn thất ngoài bóng che (nhiệt độ, dây dẫn, bộ biến đổi điện, bụi) gộp trong hệ số hiệu năng PR {num(config.performance_ratio*100)}%{config.yield_losses?'; tổn thất nhiệt tính từ thời tiết năm điển hình cho mặt mái chính':''}.</li>
    <li>{config.weather?'Bức xạ, mây và nhiệt độ lấy từ năm khí tượng điển hình PVGIS, gộp thành ngày trung bình của từng tháng; năm thực tế có thể cao hoặc thấp hơn vài phần trăm.':'Bức xạ theo mô hình trời quang và giá trị năm nhập tay; chưa có mùa mưa, mây và nhiệt độ thật.'}</li>
    <li>Vật cản là khối đứng theo mặt bằng; chưa xét cây có tán, kính phản xạ, địa hình.</li>
    <li>{p.electrical?'Thiết kế điện là sơ bộ (chia chuỗi, chọn inverter, giới hạn điện áp, dòng và sụt áp cáp); chưa tính phối hợp bảo vệ.':'Chưa thiết kế đấu chuỗi và chọn bộ biến đổi điện.'} {p.siteReview?'Tải trọng mái, gió bão, ăn mòn, phòng cháy và thủ tục mới ở mức sàng lọc theo câu trả lời khảo sát; kỹ sư kết cấu và kỹ sư điện xác nhận tại hiện trường.':'Chưa kiểm tra tải trọng mái, tải gió và phòng cháy.'}</li>
    <li>Chi phí và giá điện do kỹ sư nhập; ô để trống dùng giá tham khảo SolarOpt có ghi nguồn ({E.source}). Ba kịch bản cho thấy khoảng dao động, không phải cam kết.</li>
    <li>{p.aiNote}</li>
   </ul>
   <div className="rp-signatures">{['Người lập','Kỹ sư kiểm tra','Đại diện chủ đầu tư'].map(r=><div key={r}><strong>{r}</strong><span>Ký, ghi rõ họ tên</span><i/><small>Ngày ……/……/…………</small></div>)}</div>
  </Sheet>

  {design&&<section className="rp-sheet rp-appendix"><header className="rp-running"><img src="/solaropt-mark.svg" alt=""/><span>SolarOpt</span><span>{project}</span></header>
   <p className="rp-eyebrow">Phụ lục A</p><h2 className="rp-title">Tọa độ tấm pin để định vị ngoài hiện trường</h2>
   <InstallationGuide config={config} design={design} datum={p.datum} print/></section>}
 </div>
}
