import {Icon} from './Icon'

export const DEMO_IMAGE='/demo/anh-drone-mai-nha.png'
/** The presenter types these in step 1; the recorded vision answer was made with the same size. */
export const DEMO_SIZE={width:'12',length:'9'}
export const DEMO_NOTE='Khách sắp mua xe điện, sạc ban ngày thêm 150 kWh/tháng'

export type DemoStep={id:string;title:string;hint:string;done:boolean;action?:{label:string;run:()=>void;disabled?:boolean}}

/** Presenter's checklist for the pitch: one line per step, the next one highlighted, a button where the app can do it. */
export function DemoGuide({steps,guest,onClose}:{steps:DemoStep[];guest:boolean;onClose:()=>void}){
 const next=steps.findIndex(s=>!s.done)
 return <section className="demo-guide" aria-label="Kịch bản demo">
  <header><span className="demo-pill"><Icon name="sparkles" size={13}/>Chế độ demo</span><p>Kết quả AI có bản ghi sẽ được phát lại ngay và ghi rõ là bản ghi; dữ liệu khác vẫn gọi AI thật (tối đa 30 giây cho trợ lý).</p><button type="button" className="text-button" onClick={onClose}>Tắt chế độ demo</button></header>
  {guest&&<p className="demo-warning" role="status"><Icon name="alert" size={14}/>Đang ở chế độ khách: số dự án tính được mỗi ngày có giới hạn. Đăng nhập tài khoản trước khi trình bày để bước xếp pin không bị chặn.</p>}
  <ol>{steps.map((s,i)=><li key={s.id} className={s.done?'done':i===next?'next':''}>
   <span className="demo-index">{s.done?<Icon name="check" size={12}/>:i+1}</span>
   <div><strong>{s.title}</strong><small>{s.hint}</small></div>
   {s.action&&!s.done&&<button type="button" className={'button small '+(i===next?'primary':'secondary')} disabled={s.action.disabled} onClick={s.action.run}>{s.action.label}</button>}
  </li>)}</ol>
 </section>
}
