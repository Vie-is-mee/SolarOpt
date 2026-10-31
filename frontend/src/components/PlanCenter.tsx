import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react'
import {accountIdentity} from '../draftOwner'
import {Icon} from './Icon'

type Limits={projects:number;project_window:number|null;ai_reads:number}
type Plan={name:string;price_vnd_month:number;projects:number;ai_reads:number;features:string[];project_window_days:number|null}
type Usage={plan:string;plan_name:string;plan_until:number|null;limits:Limits;used:{projects:number;ai_reads:number};plans:Record<string,Plan>;is_admin:boolean;pending_request?:string|null}
type AdminUser={id:number;email:string;plan:string;plan_until:number|null;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null}
const base=import.meta.env.VITE_API_BASE||''
const money=(n:number)=>n?n.toLocaleString('vi-VN')+' đ/tháng':'0 đ'
const date=(t:number|null)=>t?new Date(t*1000).toLocaleDateString('vi-VN'):'—'
async function call<T>(path:string,body?:unknown):Promise<T>{
 const r=await fetch(base+path,{credentials:'include',method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-SolarOpt-Request':'1','X-SolarOpt-User':accountIdentity()},...(body===undefined?{}:{body:JSON.stringify(body)})})
 if(!r.ok){let d='';try{d=(await r.json()).detail}catch{}throw new Error(typeof d==='string'&&d?d:`Yêu cầu chưa thành công (${r.status}).`)}
 return r.json()
}

function Modal({title,onClose,children,wide=false}:{title:string;onClose:()=>void;children:ReactNode;wide?:boolean}){
 const ref=useRef<HTMLDialogElement>(null)
 useEffect(()=>{const d=ref.current!;d.showModal();return()=>d.close()},[])
 return <dialog ref={ref} className={`account-dialog plan-dialog${wide?' wide':''}`} aria-label={title} onCancel={e=>{e.preventDefault();onClose()}}>
  <button type="button" className="account-close icon-button" aria-label="Đóng" onClick={onClose}><Icon name="close" size={20}/></button>
  <div className="plan-body"><h2>{title}</h2>{children}</div>
 </dialog>
}

/** Usage meter, plan catalogue with upgrade requests, and the admin console for activating plans. */
export function PlanCenter({signedIn,onLogin}:{signedIn:boolean;onLogin:()=>void}){
 const [usage,setUsage]=useState<Usage|null>(null),[open,setOpen]=useState<'plans'|'admin'|null>(null),[message,setMessage]=useState(''),[error,setError]=useState('')
 const [users,setUsers]=useState<AdminUser[]>([]),[choice,setChoice]=useState<Record<number,{plan:string;months:number}>>({})
 const refresh=useCallback(()=>{call<Usage>('/api/account/usage').then(setUsage).catch(()=>{})},[])
 useEffect(()=>{refresh()},[refresh,signedIn])
 useEffect(()=>{
  const used=()=>refresh(),quota=()=>{refresh();setMessage('');setError('');setOpen('plans')}
  window.addEventListener('solaropt-usage',used);window.addEventListener('solaropt-quota',quota)
  return()=>{window.removeEventListener('solaropt-usage',used);window.removeEventListener('solaropt-quota',quota)}
 },[refresh])
 async function request(plan:string){setError('');try{await call('/api/account/upgrade-request',{plan,note:''});setMessage(`Đã gửi yêu cầu nâng cấp lên gói ${usage?.plans[plan]?.name}. Quản trị viên sẽ liên hệ và kích hoạt.`);refresh()}catch(e){setError((e as Error).message)}}
 async function loadAdmin(){setError('');try{setUsers(await call<AdminUser[]>('/api/admin/users'))}catch(e){setError((e as Error).message)}}
 async function apply(u:AdminUser){const c=choice[u.id]||{plan:u.pending_request?.plan||u.plan,months:1};setError('');try{await call(`/api/admin/users/${u.id}/plan`,c);setMessage(`Đã đặt gói ${usage?.plans[c.plan]?.name} cho ${u.email}.`);await loadAdmin()}catch(e){setError((e as Error).message)}}
 if(!usage)return null
 const left=Math.max(0,usage.limits.projects-usage.used.projects)
 return <>
  <span className={`plan-meter${left===0?' empty':''}`} title={usage.plan==='guest'?'Khách: tính thử theo ngày':'Mỗi dự án chỉ tính một lần; tính lại cùng dự án không trừ lượt'}>
   <strong>{usage.plan_name}</strong> · {usage.used.projects}/{usage.limits.projects} dự án{usage.plan==='guest'?' hôm nay':usage.limits.project_window?' / 30 ngày':''}{usage.plan!=='guest'&&<> · AI {usage.used.ai_reads}/{usage.limits.ai_reads}</>}
  </span>
  <button className="button secondary small" onClick={()=>{setMessage('');setError('');setOpen('plans')}}>{usage.plan==='business'?'Gói của bạn':'Nâng cấp'}</button>
  {usage.is_admin&&<button className="button secondary small" onClick={()=>{setMessage('');setOpen('admin');void loadAdmin()}}>Quản trị</button>}
  {open==='plans'&&<Modal title="Gói sử dụng SolarOpt" onClose={()=>setOpen(null)}>
   <p className="plan-note">{left===0?'Bạn đã dùng hết lượt của gói hiện tại. ':''}Mỗi dự án chỉ trừ một lượt; tính lại hoặc so sánh 3 phương án của cùng dự án không trừ thêm.{usage.plan!=='guest'&&usage.plan!=='free'?` Gói hiện tại hiệu lực đến ${date(usage.plan_until)}.`:''}</p>
   <div className="plan-grid">{Object.entries(usage.plans).map(([id,p])=><article key={id} className={usage.plan===id?'current':''}>
    <h3>{p.name}</h3><strong>{money(p.price_vnd_month)}</strong>
    <ul>{p.features.map(f=><li key={f}>{f}</li>)}</ul>
    {usage.plan===id?<span className="badge">Đang dùng</span>:id==='free'?(usage.plan==='guest'?<button className="button secondary small" onClick={()=>{setOpen(null);onLogin()}}>Đăng ký miễn phí</button>:null)
     :!signedIn?<button className="button secondary small" onClick={()=>{setOpen(null);onLogin()}}>Đăng nhập để nâng cấp</button>
     :usage.pending_request===id?<span className="badge amber">Đã gửi yêu cầu</span>
     :<button className="button primary small" onClick={()=>void request(id)}>Gửi yêu cầu nâng cấp</button>}
   </article>)}</div>
   <p className="plan-note">Giá là mức dự kiến trong giai đoạn thử nghiệm. Thanh toán trực tuyến chưa tích hợp: sau khi gửi yêu cầu, quản trị viên liên hệ và kích hoạt gói.</p>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
  </Modal>}
  {open==='admin'&&<Modal title="Quản trị người dùng và gói" onClose={()=>setOpen(null)} wide>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Email</th><th>Gói</th><th>Hết hạn</th><th>Dự án</th><th>AI</th><th>Yêu cầu</th><th>Đặt gói</th></tr></thead><tbody>
    {users.map(u=>{const c=choice[u.id]||{plan:u.pending_request?.plan||u.plan,months:1};return <tr key={u.id}>
     <td>{u.email}</td><td>{usage.plans[u.plan]?.name||u.plan}</td><td>{date(u.plan_until)}</td><td>{u.used.projects}/{u.limits.projects}</td><td>{u.used.ai_reads}/{u.limits.ai_reads}</td>
     <td>{u.pending_request?`${usage.plans[u.pending_request.plan]?.name}${u.pending_request.note?` · ${u.pending_request.note}`:''}`:'—'}</td>
     <td className="admin-actions"><select aria-label={`Gói cho ${u.email}`} value={c.plan} onChange={e=>setChoice({...choice,[u.id]:{...c,plan:e.target.value}})}>{Object.entries(usage.plans).map(([id,p])=><option key={id} value={id}>{p.name}</option>)}</select>
      {c.plan!=='free'&&<select aria-label="Số tháng" value={c.months} onChange={e=>setChoice({...choice,[u.id]:{...c,months:Number(e.target.value)}})}>{[1,3,6,12].map(m=><option key={m} value={m}>{m} tháng</option>)}</select>}
      <button className="button primary small" onClick={()=>void apply(u)}>Áp dụng</button></td>
    </tr>})}
    {!users.length&&<tr><td colSpan={7}>Chưa có người dùng.</td></tr>}
   </tbody></table></div>
  </Modal>}
 </>
}
