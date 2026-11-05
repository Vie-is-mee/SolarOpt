import {useState} from 'react'
import type {Config} from '../studioTypes'
import {LOSS_ITEMS,defaultLosses,performanceRatio,type YieldLosses} from '../yieldLosses'
import {studioApi as api} from '../services/studioApi'
import {Icon} from './Icon'

const num=(v:number,d=1)=>v.toLocaleString('vi-VN',{maximumFractionDigits:d})
const area=(pts:{x:number;y:number}[])=>Math.abs(pts.reduce((s,p,i)=>{const q=pts[(i+1)%pts.length];return s+p.x*q.y-q.x*p.y},0))/2

/** The plane the temperature loss is computed for: a rack's own tilt, otherwise the largest roof face. */
function mainPlane(c:Config){
 const mounting=c.mounting||'flush'
 if(mounting==='tilted_rack')return {tilt:c.rack_tilt_deg??15,azimuth:c.rack_azimuth_deg??180,mounting}
 if(mounting==='tracker')return {tilt:0,azimuth:180,mounting}
 const face=[...(c.roof_faces||[])].filter(f=>f.installable!==false).sort((a,b)=>area(b.polygon)-area(a.polygon))[0]
 return face?{tilt:face.tilt_deg,azimuth:face.azimuth_deg,mounting}:{tilt:c.roof_tilt_deg,azimuth:c.roof_azimuth_deg,mounting}
}

/** Where the sunshine figures come from and what is lost on the way to the meter. Typical-year weather from
 * PVGIS replaces the clear-sky model; the itemised losses replace a single assumed performance ratio. */
export function YieldSource({config,onConfig,disabled,onLog}:{config:Config;onConfig:(patch:Partial<Config>,source:string)=>void;disabled:boolean;onLog:(title:string,detail:string,tone?:'ok'|'warn'|'error')=>void}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('')
 const losses=config.yield_losses||null,weather=config.weather||null
 async function load(){
  setBusy(true);setError('')
  const plane=mainPlane(config),base=losses||defaultLosses()
  try{
   const r=await api.weather({latitude:config.latitude,longitude:config.longitude,tilt_deg:Math.min(60,Math.max(0,plane.tilt)),azimuth_deg:((plane.azimuth%360)+360)%360,mounting:plane.mounting,temp_coeff_pct:base.temp_coeff_pct})
   const next:YieldLosses={...base,temperature_pct:r.losses.temperature_pct}
   onConfig({weather:r.weather,annual_irradiance_kwh_m2:r.weather.annual_ghi_kwh_m2,irradiance_reference_tilt_deg:0,irradiance_reference_azimuth_deg:180,yield_losses:next,performance_ratio:performanceRatio(next)},`${r.weather.source} · ${num(r.weather.annual_ghi_kwh_m2,0)} kWh/m²/năm (mặt ngang)`)
   onLog('Đã tải thời tiết năm điển hình',`${r.weather.source}: ${num(r.weather.annual_ghi_kwh_m2,0)} kWh/m²/năm; tổn thất nhiệt ${num(r.losses.temperature_pct)}% cho mặt ${num(plane.tilt,0)}° hướng ${num(plane.azimuth,0)}° (${plane.mounting==='flush'?'lắp sát mái':plane.mounting==='tilted_rack'?'giá nghiêng':'trục xoay'}). Hệ số hiệu năng ${num(performanceRatio(next)*100)}%.`)
  }catch(e){const text=e instanceof Error?e.message:'Chưa tải được dữ liệu thời tiết.';setError(text);onLog('PVGIS chưa khả dụng',text,'warn')}
  finally{setBusy(false)}
 }
 function setLoss(key:keyof YieldLosses,v:number){const next={...(losses||defaultLosses()),[key]:v};onConfig({yield_losses:next,performance_ratio:performanceRatio(next)},'')}
 return <div className="yield-source">
  <div className="source-fact"><span>Nguồn nắng</span><strong>{weather?weather.source:'Mô hình trời quang (chưa phải thời tiết thật)'}</strong></div>
  <p className="muted-note">{weather?`Năm khí tượng điển hình tại ${num(weather.latitude,3)}, ${num(weather.longitude,3)}: ${num(weather.annual_ghi_kwh_m2,0)} kWh/m²/năm trên mặt ngang. Mây, mùa mưa và nhiệt độ từng giờ đã tính vào sản lượng, biểu đồ theo tháng và theo giờ.`:'Đang dùng bức xạ năm nhập tay trên nền trời quang: không có mùa mưa, mây hay nhiệt độ thật. Tải thời tiết PVGIS để sản lượng và tự dùng theo giờ sát thực tế.'}</p>
  <div className="inline-actions"><button type="button" className="button secondary small" disabled={disabled||busy} onClick={load}><Icon name="cloud" size={15}/>{busy?'Đang tải PVGIS…':weather?'Tải lại thời tiết PVGIS':'Tải thời tiết thật của vị trí (PVGIS)'}</button>{weather&&<button type="button" className="text-button" disabled={disabled||busy} onClick={()=>onConfig({weather:null},'Mô hình trời quang')}>Bỏ dữ liệu thời tiết</button>}</div>
  {error&&<p className="tracer-error" role="alert">{error}</p>}
  {losses?<>
   <div className="table-scroll"><table className="data-table loss-table"><caption>Tổn thất từ bức xạ trên mặt tấm đến điện tại công tơ</caption>
    <tbody>{LOSS_ITEMS.map(item=><tr key={item.key}><td>{item.label}{item.hint&&<small> · {item.hint}</small>}</td><td className="num"><input aria-label={item.label} type="number" min={0} max={item.max} step={.1} value={losses[item.key]} onChange={e=>{const v=Number(e.target.value);if(e.target.value!==''&&Number.isFinite(v)&&v>=0&&v<=item.max)setLoss(item.key,v)}}/> %</td></tr>)}</tbody>
    <tfoot><tr><td>Hệ số hiệu năng (PR) = tích các phần còn lại</td><td className="num"><b>{num(performanceRatio(losses)*100)}%</b></td></tr></tfoot></table></div>
   <p className="muted-note">Hệ số nhiệt công suất {num(losses.temp_coeff_pct,2)} %/°C (PERC ≈ −0,35; TOPCon ≈ −0,30). Tổn thất nhiệt {weather?'tính cho mặt mái chính lúc tải thời tiết; đổi cách lắp hoặc dạng mái thì tải lại':'mặc định 8% vì chưa có thời tiết'}. Bóng che tính riêng cho từng tấm.</p>
   <button type="button" className="text-button" disabled={disabled} onClick={()=>onConfig({yield_losses:null},'')}>Dùng một hệ số hiệu năng chung</button>
  </>:<>
   <p className="muted-note">Đang dùng một hệ số hiệu năng chung {num(config.performance_ratio*100)}%.</p>
   <button type="button" className="text-button" disabled={disabled} onClick={()=>{const l=defaultLosses();onConfig({yield_losses:l,performance_ratio:performanceRatio(l)},'')}}>Tách thành bảng tổn thất chi tiết</button>
  </>}
 </div>
}
