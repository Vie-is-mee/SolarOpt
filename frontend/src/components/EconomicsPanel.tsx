import {CAPEX_LABEL,CUSTOMER,DEFAULT_SPREAD,SPREAD_FIELDS,calculateScenarios,economicFields,prepareEconomics,type CustomerType,type Economics,type Spread} from '../economics'
import {LOAD_PROFILES,consumptionOf,defaultProfile,type LoadProfileId} from '../loadProfiles'
import {TARIFF_SOURCE,type Voltage} from '../tariff'
import {SelfUseChart} from './SelfUseChart'
import type {Design} from '../studioTypes'
import {grouped,vnd} from '../format'
import {MoneyInput} from './MoneyInput'
import {CardHead,MissingList} from './CardHead'
import {ScenarioTable} from './ScenarioTable'
const money=(n:number)=>vnd(n)
// Cash-flow table in millions so nine columns of figures stay comparable at a glance.
const tr=(n:number)=>(n/1e6).toLocaleString('vi-VN',{minimumFractionDigits:1,maximumFractionDigits:1})
const dec=(v:number,d=1)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
// Fields an engineer rarely knows up front; they stay folded away with their market reference shown.
const GROUPS:{title:string;keys:(keyof Economics)[]}[]=[
 {title:'Giá bán và thuế (khi tính theo hạng mục)',keys:['contingency_pct','markup_pct','vat_pct']},
 {title:'Điện năng và giá điện',keys:['degradation_pct','price_growth_pct']},
 {title:'Vận hành và tài chính',keys:['maintenance_year','replacement_cost','replacement_year','discount_pct','loan_amount','loan_rate_pct','loan_years']},
]
const EXTRA:Partial<Record<keyof Economics,[string,string]>>={years:['Số năm phân tích','năm'],replacement_year:['Năm thay thiết bị','năm'],loan_years:['Kỳ hạn vay','năm']}

export function EconomicsPanel({value,onChange,design,latitude,print=false}:{value:Economics;onChange?:(v:Economics)=>void;design:Design;latitude:number;print?:boolean}){
 const kwp=design.metrics.peak_power_kwp,perKwp=value.cost_mode==='per_kwp',type:CustomerType=value.customer_type??'residential'
 // The layout's hour-by-hour output lets self-use follow the customer's own demand (loadProfiles.ts).
 const site={profile:design.month_hour_kwh,latitude}
 const scenarios=calculateScenarios(value,design.metrics.estimated_cost_vnd,design.metrics.annual_energy_kwh,kwp,site)
 const prep=prepareEconomics(value,design.metrics.annual_energy_kwh,kwp,site)
 const r=scenarios[1].result,R=r.resolved,auto=new Set(prep.auto),fromHourly=new Set(prep.fromHourly),hourly=r.hourly
 const consumption=consumptionOf(value,latitude),profileId:LoadProfileId=consumption?.profile??(value.load_profile&&LOAD_PROFILES.find(p=>p.id===value.load_profile)?.kinds.includes(type)?value.load_profile:defaultProfile(type))
 const meta=(k:keyof Economics):[string,string]=>{const f=economicFields.find(([key])=>key===k);return f?[f[1],f[2]]:EXTRA[k]!}
 function set(k:keyof Economics,v:unknown){onChange?.({...value,[k]:v})}
 const shown=(k:keyof Economics)=>{const v=R[k] as number;return typeof v==='number'?(meta(k)[1].startsWith('đ')?grouped(Math.round(v)):dec(v,2)):''}
 function input(k:keyof Economics,labelOverride?:string){const [label0,unit]=meta(k),label=labelOverride??label0,v=value[k] as number|null,placeholder=fromHourly.has(k)?`Theo giờ: ${shown(k)}`:auto.has(k)?`Tham khảo: ${shown(k)}`:'Chưa nhập'
  if(unit.startsWith('đ'))return <MoneyInput key={k} label={label} unit={unit} value={v} placeholder={placeholder} onChange={n=>set(k,n)}/>
  return <label className="field" key={k}><span>{label}</span><div className="input-wrap"><input aria-label={label} type="number" min="0" value={v??''} placeholder={placeholder} onChange={e=>set(k,e.target.value===''?(k in EXTRA?value[k]:null):Number(e.target.value))}/><small>{unit}</small></div></label>}
 function spread(which:'spread_low'|'spread_high',k:keyof Spread,v:number){const base=value[which]??DEFAULT_SPREAD[which==='spread_low'?'low':'high'];set(which,{...base,[k]:v})}
 const share=(n:number)=>r.total>0?Math.max(0,n/r.total):0
 const row=(label:string,n:number|null,kind='',key?:string)=><tr key={key??label} className={kind}><td>{label}</td><td className="num" title={n===null?undefined:grouped(n)+' đ'}>{n===null?<span className="pending">Chưa nhập</span>:money(n)}</td><td className="share">{n!==null&&kind!=='total'&&<><i style={{width:`${Math.min(100,share(n)*100)}%`}}/><span>{(share(n)*100).toLocaleString('vi-VN',{maximumFractionDigits:1})}%</span></>}</td></tr>
 const payback=r.rows.findIndex((x,i)=>i>0&&x.cumulative>=0&&r.rows[i-1].cumulative<0)
 return <section className="card economics-panel">
  <CardHead icon="chart" title="Hiệu quả kinh tế · ba kịch bản" sub="Ô để trống dùng giá tham khảo thị trường có ghi nguồn; chỉ sửa những số bạn đã biết (báo giá, hóa đơn)"/>
  {!print&&<>
   <div className="field-grid three">
    <label className="field"><span>Khách hàng</span><select aria-label="Loại khách hàng" value={type} onChange={e=>{const t=e.target.value as CustomerType;onChange?.({...value,customer_type:t,load_profile:defaultProfile(t)})}}>{(Object.keys(CUSTOMER) as CustomerType[]).map(t=><option key={t} value={t}>{CUSTOMER[t].label}</option>)}</select></label>
    <label className="field"><span>Kiểu dùng điện</span><select aria-label="Kiểu dùng điện" value={profileId} onChange={e=>set('load_profile',e.target.value as LoadProfileId)}>{LOAD_PROFILES.filter(p=>p.kinds.includes(type)).map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</select><em>{LOAD_PROFILES.find(p=>p.id===profileId)?.hint}</em></label>
    <label className="field"><span>Điện tiêu thụ trung bình</span><div className="input-wrap"><input aria-label="Điện tiêu thụ mỗi tháng" type="number" min="0" value={value.monthly_use_kwh??''} placeholder={consumption&&value.monthly_use_kwh==null?`Từ hóa đơn ≈ ${dec(consumption.monthlyKwh,0)}`:'Chưa biết'} onChange={e=>set('monthly_use_kwh',e.target.value===''?null:Math.max(0,Number(e.target.value)))}/><small>kWh/tháng</small></div></label>
    <MoneyInput label="hoặc tiền điện mỗi tháng (gồm VAT)" value={value.monthly_bill_vnd??null} placeholder="Chưa biết" onChange={v=>set('monthly_bill_vnd',v)}/>
    <label className="field"><span>Tải thêm ban ngày (xe điện, bơm nhiệt…)</span><div className="input-wrap"><input aria-label="Tải thêm ban ngày" type="number" min="0" value={value.extra_daytime_kwh_month??''} placeholder="Không có" onChange={e=>set('extra_daytime_kwh_month',e.target.value===''?null:Math.max(0,Number(e.target.value)))}/><small>kWh/tháng</small></div><em>Dùng từ 9h đến 17h, chưa có trong hóa đơn hiện tại.</em></label>
    {type!=='residential'&&<label className="field"><span>Cấp điện áp</span><select aria-label="Cấp điện áp" value={value.voltage??'low'} onChange={e=>set('voltage',e.target.value as Voltage)}><option value="low">Hạ áp (≤ 1 kV)</option><option value="medium">Trung áp (1–35 kV)</option></select></label>}
    {perKwp?<label className="field"><span>{CAPEX_LABEL} (EPC, gồm thuế)</span><div className="input-wrap"><input aria-label={CAPEX_LABEL} type="number" min="0" max="200" step="0.1" value={value.capex_million_per_kwp??''} placeholder={`Tham khảo: ${dec(R.capex_million_per_kwp??0)}`} onChange={e=>set('capex_million_per_kwp',e.target.value===''?null:Number(e.target.value))}/><small>tr đ/kWp</small></div></label>
     :<div className="field"><span>Vốn đầu tư</span><p className="muted-note">Theo từng hạng mục báo giá (mở phần chi tiết bên dưới).</p></div>}
    {input('buy_price','Giá điện tránh mua (gồm VAT)')}
    {input('self_use_pct','Tỷ lệ điện dùng tại chỗ')}
    <label className="field"><span>Điện dư</span><select aria-label="Điện dư" value={value.sell_surplus===false?'no':'yes'} onChange={e=>onChange?.({...value,sell_surplus:e.target.value==='no'?false:null})}><option value="yes">Bán lên lưới (tối đa 50% sản lượng)</option><option value="no">Không bán, lắp chống phát ngược</option></select><em>Quyết định thủ tục (NĐ 58/2025) và thiết bị trong bảng vật tư.</em></label>
    {value.sell_surplus!==false&&input('sell_price','Giá điện dư được trả')}
    {input('years')}
   </div>
   <p className="muted-note">{hourly?<>Tự dùng tính theo từng giờ: sản lượng của phương án theo giờ trong ngày điển hình mỗi tháng so với nhu cầu {dec(consumption!.monthlyKwh,0)} kWh/tháng kiểu “{LOAD_PROFILES.find(p=>p.id===consumption!.profile)?.label}”. Tiền tiết kiệm tính theo {type==='residential'?'đúng bậc thang mà điện mặt trời cắt bớt':'giá từng khung giờ'} ({TARIFF_SOURCE}).</>:<>Chưa có điện tiêu thụ nên tỷ lệ tự dùng {dec(R.self_use_pct??0,0)}% và giá điện {dec(R.buy_price??0,0)} đ/kWh là giá trị tham khảo ({CUSTOMER[type].note}). Nhập số kWh hoặc tiền điện trên hóa đơn để tính theo giờ.</>} Điện dư chỉ được trả tối đa 50% sản lượng.</p>
  </>}
  {hourly&&<div className="kpi-tiles selfuse-tiles">
   <div><span>Tự dùng tại chỗ</span><strong>{dec(hourly.selfPct,0)}% sản lượng</strong><small>{dec(hourly.selfKwh,0)} / {dec(hourly.productionKwh,0)} kWh năm đầu</small></div>
   <div><span>Đáp ứng nhu cầu</span><strong>{dec(hourly.coveragePct,0)}%</strong><small>của {dec(hourly.loadKwh,0)} kWh/năm</small></div>
   <div><span>Giá trị mỗi kWh tự dùng</span><strong>{dec(hourly.buyPrice,0)} đ</strong><small>tiết kiệm năm đầu {money(hourly.avoidedVnd)}</small></div>
   <div><span>Điện dư phát lên lưới</span><strong>{dec(hourly.exportKwh,0)} kWh</strong><small>được trả tối đa 50% sản lượng</small></div>
  </div>}
  {hourly&&!print&&<SelfUseChart hourly={hourly}/>}
  {r.missing.length>0&&<MissingList title="Dự toán theo hạng mục còn thiếu giá: các tổng dưới đây chưa dùng để chốt giá." items={r.missing}/>}
  <ScenarioTable scenarios={scenarios} years={R.years} compact={print}/>
  {!r.missing.length&&<div className="kpi-tiles">
   <div><span>Hoàn vốn (cơ sở)</span><strong>{r.total<=(R.loan_amount??0)?'Không có vốn tự có':r.payback===null?'Chưa hoàn vốn':dec(r.payback)+' năm'}</strong><small>khoảng {scenarios[2].result.payback!=null?dec(scenarios[2].result.payback):'—'}–{scenarios[0].result.payback!=null?dec(scenarios[0].result.payback):`>${R.years}`} năm</small></div>
   <div><span>IRR (cơ sở)</span><strong>{r.irr!=null?dec(r.irr*100)+'%':'—'}</strong><small>so với chiết khấu {dec(R.discount_pct??0)}%</small></div>
   <div><span>Giá thành điện mặt trời</span><strong>{r.lcoe!=null?dec(r.lcoe,0)+' đ/kWh':'—'}</strong><small>giá mua EVN {dec(R.buy_price??0,0)} đ/kWh</small></div>
   <div><span>NPV (cơ sở)</span><strong className={r.npv<0?'neg':''}>{money(r.npv)}</strong><small>từ {money(scenarios[0].result.npv)} đến {money(scenarios[2].result.npv)}</small></div>
  </div>}
  {!print&&<details className="economics-detail"><summary>Giả định chi tiết, dự toán theo hạng mục và biên độ kịch bản</summary>
   <h4 className="form-group-title">Cách tính vốn đầu tư</h4>
   <div className="segmented cost-mode" role="group" aria-label="Cách tính vốn đầu tư">{([['per_kwp','Theo suất đầu tư (ước tính nhanh)'],['itemized','Theo từng hạng mục (báo giá)']] as const).map(([id,label])=><button key={id} type="button" className={(value.cost_mode??'itemized')===id?'active':''} aria-pressed={(value.cost_mode??'itemized')===id} onClick={()=>set('cost_mode',id)}>{label}</button>)}</div>
   {!perKwp&&<><h4 className="form-group-title">Chi phí thiết bị và thi công</h4><div className="field-grid three">{value.costs.map((c,i)=><MoneyInput key={i} label={c.name} value={c.amount} onChange={v=>onChange?.({...value,costs:value.costs.map((x,j)=>j===i?{...x,amount:v}:x)})}/>)}</div></>}
   {GROUPS.filter(g=>!perKwp||!g.title.startsWith('Giá bán')).map(g=><div key={g.title}><h4 className="form-group-title">{g.title}</h4><div className="field-grid three">{g.keys.map(k=>input(k))}</div></div>)}
   <h4 className="form-group-title">Biên độ so với kịch bản cơ sở</h4>
   <div className="table-scroll"><table className="data-table spread-table"><thead><tr><th>Giả định</th><th className="num">Thận trọng</th><th className="num">Thuận lợi</th></tr></thead>
    <tbody>{SPREAD_FIELDS.map(([k,label,unit])=><tr key={k}><td>{label} <small>({unit})</small></td>{(['spread_low','spread_high'] as const).map(w=><td key={w} className="num"><input aria-label={`${label} ${w==='spread_low'?'thận trọng':'thuận lợi'}`} type="number" step="0.5" value={(value[w]??DEFAULT_SPREAD[w==='spread_low'?'low':'high'])[k]} onChange={e=>e.target.value!==''&&spread(w,k,Number(e.target.value))}/></td>)}</tr>)}</tbody></table></div>
   <label className="field"><span>Nguồn báo giá và phạm vi đã bao gồm / chưa bao gồm</span><textarea aria-label="Nguồn báo giá" value={value.source} placeholder={R.source} onChange={e=>set('source',e.target.value)}/></label>
   <div className="table-scroll"><table className="data-table cost-table"><caption>Dự toán kịch bản cơ sở</caption>
    <thead><tr><th>Khoản mục</th><th className="num">Giá trị</th><th className="share">Tỷ trọng</th></tr></thead>
    <tbody>{perKwp?<>
     {row(`${CAPEX_LABEL} ${dec(R.capex_million_per_kwp??0)} triệu đ/kWp × ${dec(kwp,2)} kWp`,r.total)}
     {row('Tổng đầu tư khách hàng',r.total,'total')}
    </>:<>
     {row(`Tấm pin (${design.metrics.panel_count} tấm)`,design.metrics.estimated_cost_vnd)}
     {value.costs.map((c,i)=>row(c.name,c.amount,'',`c${i}`))}
     {row('Chi phí trực tiếp',r.direct,'subtotal')}
     {row('Dự phòng chi phí',r.contingency)}
     {row('Lãi gộp đơn vị lắp đặt',r.profit)}
     {row('Thuế',r.tax)}
     {row('Tổng đầu tư khách hàng',r.total,'total')}
    </>}</tbody></table></div>
  </details>}
  {!r.missing.length&&<details open={print}><summary>Dòng tiền từng năm, kịch bản cơ sở (đã trừ bảo trì, thay thiết bị và trả nợ)</summary><div className="table-scroll"><table className="data-table cashflow-table"><caption>Đơn vị: triệu đồng · sản lượng kWh · dòng tô vàng là năm hoàn vốn</caption>
   <thead><tr><th className="num">Năm</th><th className="num">Sản lượng</th><th className="num">Tiết kiệm điện mua</th><th className="num">Thu điện dư</th><th className="num">Bảo trì</th><th className="num">Thay thiết bị</th><th className="num">Trả nợ</th><th className="num">Ròng</th><th className="num">Lũy kế</th></tr></thead>
   <tbody>{r.rows.map((x,i)=><tr key={x.year} className={i===payback?'payback':i===0?'year-zero':''}><td className="num">{x.year}</td><td className="num">{x.energy?Math.round(x.energy).toLocaleString('vi-VN'):'—'}</td>{[x.saving,x.exportRevenue].map((v,j)=><td key={j} className="num pos">{v?tr(v):'—'}</td>)}{[x.maintenance,x.replacement,x.debt].map((v,j)=><td key={j} className="num cost">{v?'−'+tr(v):'—'}</td>)}<td className={`num strong ${x.net<0?'neg':'pos'}`}>{tr(x.net)}</td><td className={`num strong ${x.cumulative<0?'neg':'pos'}`}>{tr(x.cumulative)}</td></tr>)}</tbody></table></div></details>}
  <p className="muted-note">Nguồn giả định: {R.source} {fromHourly.has('self_use_pct')?(hourly?'Tỷ lệ tự dùng tính theo từng giờ từ điện tiêu thụ và kiểu tải đã nhập.':'Tỷ lệ tự dùng giới hạn theo điện dùng ban ngày đã nhập, chưa tính theo từng giờ.'):value.self_use_pct!=null?'Tỷ lệ tự dùng do kỹ sư nhập.':'Tỷ lệ tự dùng là giá trị tham khảo theo loại khách, chưa tính theo từng giờ vì chưa có điện tiêu thụ.'} Hoàn vốn là lần đầu dòng tiền lũy kế không âm. Đây là ước tính sơ bộ, không phải cam kết lợi nhuận.</p></section>
}
