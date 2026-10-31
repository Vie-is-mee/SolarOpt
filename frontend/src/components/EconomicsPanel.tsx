import {calculateEconomics,economicFields,type Economics} from '../economics'
import type {Design} from '../studioTypes'
import {grouped,vnd} from '../format'
import {MoneyInput} from './MoneyInput'
import {CardHead,MissingList} from './CardHead'
const money=(n:number)=>vnd(n)
// Cash-flow table in millions so nine columns of figures stay comparable at a glance.
const tr=(n:number)=>(n/1e6).toLocaleString('vi-VN',{minimumFractionDigits:1,maximumFractionDigits:1})
const GROUPS:{title:string;keys:(keyof Economics)[]}[]=[
 {title:'Giá bán và thuế',keys:['contingency_pct','markup_pct','vat_pct']},
 {title:'Điện năng và giá điện',keys:['self_use_pct','buy_price','sell_price','degradation_pct','price_growth_pct']},
 {title:'Vận hành và tài chính',keys:['maintenance_year','replacement_cost','replacement_year','discount_pct','years','loan_amount','loan_rate_pct','loan_years']},
]
const EXTRA:Partial<Record<keyof Economics,[string,string]>>={years:['Số năm phân tích','năm'],replacement_year:['Năm thay thiết bị','năm'],loan_years:['Kỳ hạn vay','năm']}
export function EconomicsPanel({value,onChange,design,print=false}:{value:Economics;onChange?:(v:Economics)=>void;design:Design;print?:boolean}){
 const r=calculateEconomics(value,design.metrics.estimated_cost_vnd,design.metrics.annual_energy_kwh)
 const low=calculateEconomics(value,design.metrics.estimated_cost_vnd,design.metrics.annual_energy_kwh*.85)
 const meta=(k:keyof Economics):[string,string]=>{const f=economicFields.find(([key])=>key===k);return f?[f[1],f[2]]:EXTRA[k]!}
 function set(k:keyof Economics,v:number|null){onChange?.({...value,[k]:v})}
 function input(k:keyof Economics){const [label,unit]=meta(k),v=value[k] as number|null
  if(unit.startsWith('đ'))return <MoneyInput key={k} label={label} unit={unit} value={v} onChange={n=>set(k,n)}/>
  return <label className="field" key={k}><span>{label}</span><div className="input-wrap"><input aria-label={label} type="number" min="0" value={v??''} placeholder="Chưa nhập" onChange={e=>set(k,e.target.value===''?null:Number(e.target.value))}/><small>{unit}</small></div></label>}
 const share=(n:number)=>r.total>0?Math.max(0,n/r.total):0
 const row=(label:string,n:number|null,kind='',key?:string)=><tr key={key??label} className={kind}><td>{label}</td><td className="num" title={n===null?undefined:grouped(n)+' đ'}>{n===null?<span className="pending">Chưa nhập</span>:money(n)}</td><td className="share">{n!==null&&kind!=='total'&&<><i style={{width:`${Math.min(100,share(n)*100)}%`}}/><span>{(share(n)*100).toLocaleString('vi-VN',{maximumFractionDigits:1})}%</span></>}</td></tr>
 const payback=r.rows.findIndex((x,i)=>i>0&&x.cumulative>=0&&r.rows[i-1].cumulative<0)
 return <section className="card economics-panel">
  <CardHead icon="chart" title="Dự toán và hiệu quả kinh tế cho khách hàng" sub="Đơn giá do kỹ sư nhập từ báo giá; ô trống là chưa biết, nhập 0 khi đã xác nhận không phát sinh"/>
  {!print&&<>
   <h4 className="form-group-title">Chi phí thiết bị và thi công</h4>
   <div className="field-grid three">{value.costs.map((c,i)=><MoneyInput key={i} label={c.name} value={c.amount} onChange={v=>onChange?.({...value,costs:value.costs.map((x,j)=>j===i?{...x,amount:v}:x)})}/>)}</div>
   {GROUPS.map(g=><div key={g.title}><h4 className="form-group-title">{g.title}</h4><div className="field-grid three">{g.keys.map(input)}</div></div>)}
   <label className="field"><span>Nguồn báo giá và phạm vi đã bao gồm / chưa bao gồm</span><textarea aria-label="Nguồn báo giá" value={value.source} onChange={e=>onChange?.({...value,source:e.target.value})}/></label>
  </>}
  {r.missing.length>0?<MissingList title="Dự toán chưa đủ dữ liệu — chưa dùng các tổng tạm tính để chốt giá hoặc kết luận hoàn vốn." items={r.missing}/>:<p className="muted-note">Đã điền các giả định tính toán; kỹ sư vẫn phải đối chiếu báo giá, thuế và điều kiện hợp đồng.</p>}
  <div className="table-scroll"><table className="data-table cost-table"><caption>{r.missing.length?'Tổng tạm tính — còn thiếu dữ liệu':'Dự toán theo giả định đã nhập'}</caption>
   <thead><tr><th>Khoản mục</th><th className="num">Giá trị</th><th className="share">Tỷ trọng trên tổng đầu tư</th></tr></thead>
   <tbody>
    {row(`Tấm pin (${design.metrics.panel_count} tấm)`,design.metrics.estimated_cost_vnd)}
    {value.costs.map((c,i)=>row(c.name,c.amount,'',`c${i}`))}
    {row('Chi phí trực tiếp',r.direct,'subtotal')}
    {row('Dự phòng chi phí',r.contingency)}
    {row('Tổng giá vốn đơn vị lắp đặt',r.cost,'subtotal')}
    {row('Lãi gộp đơn vị lắp đặt (chưa trừ thuế thu nhập)',r.profit)}
    {row('Giá bán trước thuế',r.preTax,'subtotal')}
    {row('Thuế theo tỷ lệ đã nhập',r.tax)}
    {row('Tổng đầu tư khách hàng',r.total,'total')}
   </tbody></table></div>
  {print&&<><p>Nguồn: {value.source||'Chưa ghi nguồn báo giá'}.</p><ul>{economicFields.map(([k,l,u])=><li key={k}>{l}: {value[k]===null?'Chưa nhập':String(value[k])+' '+u}</li>)}</ul><p>Phân tích {value.years} năm; thay thiết bị năm {value.replacement_year}; vay {value.loan_years} năm.</p></>}
  {!r.missing.length&&<>
   <div className="kpi-tiles">
    <div><span>Lợi ích ròng năm 1</span><strong className={r.rows[1].net<0?'neg':''}>{money(r.rows[1].net)}</strong><small>sau bảo trì và trả nợ</small></div>
    <div><span>Hoàn vốn tiền khách bỏ ra</span><strong>{r.total<=(value.loan_amount??0)?'Không có vốn tự có':r.payback===null?'Chưa hoàn vốn':r.payback.toLocaleString('vi-VN',{maximumFractionDigits:1})+' năm'}</strong><small>{r.total<=(value.loan_amount??0)?'xem dòng tiền và nghĩa vụ nợ':r.payback===null?`trong ${value.years} năm phân tích`:'lần đầu lũy kế không âm'}</small></div>
    <div><span>Lợi ích ròng lũy kế</span><strong className={r.netBenefit<0?'neg':''}>{money(r.netBenefit)}</strong><small>sau {value.years} năm</small></div>
    <div><span>Giá trị hiện tại ròng (NPV)</span><strong className={r.npv<0?'neg':''}>{money(r.npv)}</strong><small>chiết khấu {value.discount_pct??0}%/năm</small></div>
    <div className="warn"><span>Nếu sản lượng thấp hơn 15%</span><strong>{low.payback===null?'Chưa hoàn vốn':low.payback.toLocaleString('vi-VN',{maximumFractionDigits:1})+' năm'}</strong><small>lợi ích ròng {money(low.netBenefit)}</small></div>
   </div>
   <details open={print}><summary>Dòng tiền từng năm (đã trừ bảo trì, thay thiết bị và trả nợ)</summary><div className="table-scroll"><table className="data-table cashflow-table"><caption>Đơn vị: triệu đồng · sản lượng kWh · dòng tô vàng là năm hoàn vốn</caption>
    <thead><tr><th className="num">Năm</th><th className="num">Sản lượng</th><th className="num">Tiết kiệm điện mua</th><th className="num">Thu điện dư</th><th className="num">Bảo trì</th><th className="num">Thay thiết bị</th><th className="num">Trả nợ</th><th className="num">Ròng</th><th className="num">Lũy kế</th></tr></thead>
    <tbody>{r.rows.map((x,i)=><tr key={x.year} className={i===payback?'payback':i===0?'year-zero':''}><td className="num">{x.year}</td><td className="num">{x.energy?Math.round(x.energy).toLocaleString('vi-VN'):'—'}</td>{[x.saving,x.exportRevenue].map((v,j)=><td key={j} className="num pos">{v?tr(v):'—'}</td>)}{[x.maintenance,x.replacement,x.debt].map((v,j)=><td key={j} className="num cost">{v?'−'+tr(v):'—'}</td>)}<td className={`num strong ${x.net<0?'neg':'pos'}`}>{tr(x.net)}</td><td className={`num strong ${x.cumulative<0?'neg':'pos'}`}>{tr(x.cumulative)}</td></tr>)}</tbody></table></div></details>
  </>}
  <p className="muted-note">Lãi gộp của đơn vị lắp đặt khác khoản tiết kiệm của khách hàng, và khác doanh thu phần mềm SolarOpt. Giá trị này chưa bao gồm thuế thu nhập, thay đổi chính sách, chi phí cơ hội ngoài tỷ lệ chiết khấu hoặc cấu hình pin lưu trữ chưa khai báo. Tỷ lệ tự dùng là giả định, chưa mô phỏng phụ tải theo giờ. Giá điện dư bằng 0 nếu chưa có cơ sở thanh toán. Khoản vay tính trả đều cuối mỗi năm, lãi suất cố định; phí vay bổ sung cần đưa vào chi phí khác. Hoàn vốn là lần đầu dòng tiền lũy kế không âm; thay thiết bị sau đó có thể làm giảm số dư. Sản lượng là ước tính sơ bộ, chưa phải cam kết lợi nhuận.</p></section>
}
