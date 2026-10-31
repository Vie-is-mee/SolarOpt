import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react'
import {accountIdentity} from '../draftOwner'
import {Icon} from './Icon'

type Limits={projects:number|null;project_window:number|null;ai_reads:number|null}
type Plan={name:string;price_vnd_month:number;projects:number;ai_reads:number;features:string[];project_window_days:number|null;seats:number}
type Member={id:number;email:string;role:'owner'|'member'}
type Team={id:number;name:string;role:'owner'|'member';plan:string;plan_name:string;plan_until:number|null;seats:number;members:Member[]}
type Usage={plan:string;plan_name:string;plan_until:number|null;limits:Limits;used:{projects:number;ai_reads:number};plans:Record<string,Plan>;is_admin:boolean;pending_request?:string|null;team:Team|null}
type AdminUser={id:number;email:string;role:string;plan:string;plan_name:string;plan_until:number|null;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null;team:{name:string;role:string}|null}
type AdminTeam={id:number;name:string;plan:string;plan_until:number|null;owner:string;members:number;seats:number;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null}
const base=import.meta.env.VITE_API_BASE||''
const money=(n:number)=>n?n.toLocaleString('vi-VN')+' đ/tháng':'0 đ'
const date=(t:number|null)=>t?new Date(t*1000).toLocaleDateString('vi-VN'):'—'
const of=(used:number,limit:number|null)=>limit===null?`${used} · không giới hạn`:`${used}/${limit}`
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

function PlanPicker({plans,value,onChange}:{plans:Record<string,Plan>;value:{plan:string;months:number};onChange:(v:{plan:string;months:number})=>void}){
 return <><select aria-label="Gói" value={value.plan} onChange={e=>onChange({...value,plan:e.target.value})}>{Object.entries(plans).map(([id,p])=><option key={id} value={id}>{p.name}</option>)}</select>
  {value.plan!=='free'&&<select aria-label="Số tháng" value={value.months} onChange={e=>onChange({...value,months:Number(e.target.value)})}>{[1,3,6,12].map(m=><option key={m} value={m}>{m} tháng</option>)}</select>}</>
}

/** Usage meter, plan catalogue with upgrade requests, team management and the admin console. */
export function PlanCenter({signedIn,onLogin}:{signedIn:boolean;onLogin:()=>void}){
 const [usage,setUsage]=useState<Usage|null>(null),[open,setOpen]=useState<'plans'|'team'|'admin'|null>(null),[message,setMessage]=useState(''),[error,setError]=useState('')
 const [users,setUsers]=useState<AdminUser[]>([]),[teams,setTeams]=useState<AdminTeam[]>([]),[choice,setChoice]=useState<Record<string,{plan:string;months:number}>>({})
 const [teamName,setTeamName]=useState(''),[memberEmail,setMemberEmail]=useState('')
 const refresh=useCallback(()=>{call<Usage>('/api/account/usage').then(setUsage).catch(()=>{})},[])
 useEffect(()=>{refresh()},[refresh,signedIn])
 useEffect(()=>{
  const used=()=>refresh(),quota=()=>{refresh();setMessage('');setError('');setOpen('plans')}
  window.addEventListener('solaropt-usage',used);window.addEventListener('solaropt-quota',quota)
  return()=>{window.removeEventListener('solaropt-usage',used);window.removeEventListener('solaropt-quota',quota)}
 },[refresh])
 const show=(view:'plans'|'team'|'admin')=>{setMessage('');setError('');setOpen(view);if(view==='admin')void loadAdmin()}
 async function run(action:()=>Promise<unknown>,ok:string){setError('');setMessage('');try{await action();setMessage(ok);refresh()}catch(e){setError((e as Error).message)}}
 async function loadAdmin(){try{const [u,t]=await Promise.all([call<AdminUser[]>('/api/admin/users'),call<AdminTeam[]>('/api/admin/teams')]);setUsers(u);setTeams(t)}catch(e){setError((e as Error).message)}}
 if(!usage)return null
 const team=usage.team,unlimited=usage.limits.projects===null
 const left=unlimited?1:Math.max(0,usage.limits.projects!-usage.used.projects)
 const pick=(key:string,fallback:string)=>choice[key]||{plan:fallback,months:1}
 return <>
  <span className={`plan-meter${left===0?' empty':''}`} title={usage.plan==='guest'?'Khách: tính thử theo ngày':'Mỗi dự án chỉ tính một lần; tính lại cùng dự án không trừ lượt'}>
   <strong>{usage.plan_name}</strong> · {unlimited?'không giới hạn':<>{usage.used.projects}/{usage.limits.projects} dự án{usage.plan==='guest'?' hôm nay':usage.limits.project_window?' / 30 ngày':''}{usage.plan!=='guest'&&<> · AI {usage.used.ai_reads}/{usage.limits.ai_reads}</>}</>}
  </span>
  {!usage.is_admin&&<button className="button secondary small" onClick={()=>show('plans')}>{usage.plan==='business'?'Gói của bạn':'Nâng cấp'}</button>}
  {signedIn&&<button className="button secondary small" onClick={()=>show('team')}>{team?`Nhóm: ${team.name}`:'Nhóm'}</button>}
  {usage.is_admin&&<button className="button secondary small" onClick={()=>show('admin')}>Quản trị</button>}

  {open==='plans'&&<Modal title="Gói sử dụng SolarOpt" onClose={()=>setOpen(null)}>
   <p className="plan-note">{left===0?'Bạn đã dùng hết lượt của gói hiện tại. ':''}Mỗi dự án chỉ trừ một lượt; tính lại hoặc so sánh 3 phương án của cùng dự án không trừ thêm.{usage.plan_until?` Gói hiện tại hiệu lực đến ${date(usage.plan_until)}.`:''}</p>
   <div className="plan-grid">{Object.entries(usage.plans).map(([id,p])=><article key={id} className={usage.plan===id?'current':''}>
    <h3>{p.name}</h3><strong>{money(p.price_vnd_month)}</strong>
    <ul>{p.features.map(f=><li key={f}>{f}</li>)}</ul>
    {usage.plan===id?<span className="badge">Đang dùng</span>:id==='free'?(usage.plan==='guest'?<button className="button secondary small" onClick={()=>{setOpen(null);onLogin()}}>Đăng ký miễn phí</button>:null)
     :!signedIn?<button className="button secondary small" onClick={()=>{setOpen(null);onLogin()}}>Đăng nhập để nâng cấp</button>
     :usage.pending_request===id?<span className="badge amber">Đã gửi yêu cầu</span>
     :id==='business'&&team?.role!=='owner'?<button className="button secondary small" onClick={()=>show('team')}>{team?'Chỉ chủ nhóm yêu cầu':'Tạo nhóm trước'}</button>
     :<button className="button primary small" onClick={()=>void run(()=>call('/api/account/upgrade-request',{plan:id,note:''}),`Đã gửi yêu cầu nâng cấp lên gói ${p.name}. Quản trị viên sẽ liên hệ và kích hoạt.`)}>Gửi yêu cầu nâng cấp</button>}
   </article>)}</div>
   <p className="plan-note">Giá là mức dự kiến trong giai đoạn thử nghiệm. Thanh toán trực tuyến chưa tích hợp: sau khi gửi yêu cầu, quản trị viên liên hệ và kích hoạt gói.</p>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
  </Modal>}

  {open==='team'&&<Modal title={team?`Nhóm ${team.name}`:'Tạo nhóm doanh nghiệp'} onClose={()=>setOpen(null)}>
   {!team?<form className="team-form" onSubmit={e=>{e.preventDefault();void run(()=>call('/api/team',{name:teamName}),'Đã tạo nhóm. Gửi yêu cầu gói Doanh nghiệp để thêm tới 5 kỹ sư.')}}>
     <p className="plan-note">Nhóm dùng chung hạn mức gói Doanh nghiệp và xem chung lịch sử dự án. Bạn sẽ là chủ nhóm.</p>
     <label className="field"><span>Tên công ty / nhóm</span><input value={teamName} minLength={2} maxLength={80} required onChange={e=>setTeamName(e.target.value)}/></label>
     <button className="button primary small">Tạo nhóm</button>
    </form>:<>
     <p className="plan-note">Gói nhóm: <strong>{team.plan_name}</strong>{team.plan_until?` đến ${date(team.plan_until)}`:''} · {team.members.length}/{team.seats} chỗ.{team.plan==='free'?' Gói Doanh nghiệp mở 5 chỗ, hạn mức chung và lịch sử chung.':''}</p>
     <ul className="team-members">{team.members.map(m=><li key={m.id}><span>{m.email}</span><small>{m.role==='owner'?'Chủ nhóm':'Kỹ sư'}</small>
      {team.role==='owner'&&m.role!=='owner'&&<button className="text-button danger" onClick={()=>void run(()=>call(`/api/team/members/${m.id}/remove`,{}),`Đã xóa ${m.email} khỏi nhóm.`)}>Xóa</button>}</li>)}</ul>
     {team.role==='owner'&&<form className="team-form inline" onSubmit={e=>{e.preventDefault();void run(()=>call('/api/team/members',{email:memberEmail}),`Đã thêm ${memberEmail}.`).then(()=>setMemberEmail(''))}}>
      <label className="field"><span>Thêm kỹ sư (email đã đăng ký)</span><input type="email" value={memberEmail} required onChange={e=>setMemberEmail(e.target.value)}/></label>
      <button className="button primary small">Thêm</button>
     </form>}
     <div className="inline-actions">{team.role==='owner'&&team.plan==='free'&&<button className="button secondary small" onClick={()=>show('plans')}>Nâng cấp gói Doanh nghiệp</button>}
      <button className="text-button danger" onClick={()=>{if(confirm(team.role==='owner'?'Giải tán nhóm này?':'Rời nhóm này?'))void run(()=>call('/api/team/leave',{}),team.role==='owner'?'Đã giải tán nhóm.':'Đã rời nhóm.')}}>{team.role==='owner'?'Giải tán nhóm':'Rời nhóm'}</button></div>
    </>}
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
  </Modal>}

  {open==='admin'&&<Modal title="Quản trị người dùng, nhóm và gói" onClose={()=>setOpen(null)} wide>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
   <h3>Nhóm doanh nghiệp</h3>
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Nhóm</th><th>Chủ nhóm</th><th>Gói</th><th>Hết hạn</th><th>Thành viên</th><th>Dự án</th><th>Yêu cầu</th><th>Đặt gói</th></tr></thead><tbody>
    {teams.map(t=>{const c=pick('t'+t.id,t.pending_request?.plan||t.plan);return <tr key={t.id}><td>{t.name}</td><td>{t.owner}</td><td>{usage.plans[t.plan]?.name}</td><td>{date(t.plan_until)}</td><td>{t.members}/{t.seats}</td><td>{of(t.used.projects,t.limits.projects)}</td>
     <td>{t.pending_request?usage.plans[t.pending_request.plan]?.name:'—'}</td>
     <td className="admin-actions"><PlanPicker plans={usage.plans} value={c} onChange={v=>setChoice({...choice,['t'+t.id]:v})}/><button className="button primary small" onClick={()=>void run(async()=>{await call(`/api/admin/teams/${t.id}/plan`,c);await loadAdmin()},`Đã đặt gói ${usage.plans[c.plan]?.name} cho nhóm ${t.name}.`)}>Áp dụng</button></td></tr>})}
    {!teams.length&&<tr><td colSpan={8}>Chưa có nhóm.</td></tr>}
   </tbody></table></div>
   <h3>Người dùng</h3>
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Email</th><th>Gói đang dùng</th><th>Nhóm</th><th>Dự án</th><th>AI</th><th>Yêu cầu</th><th>Đặt gói cá nhân</th></tr></thead><tbody>
    {users.map(u=>{const c=pick('u'+u.id,u.pending_request?.plan||(u.plan in usage.plans?u.plan:'free'));return <tr key={u.id}>
     <td>{u.email}{u.role==='admin'&&<small> · quản trị</small>}</td><td>{u.plan_name}</td><td>{u.team?`${u.team.name} (${u.team.role==='owner'?'chủ':'thành viên'})`:'—'}</td><td>{of(u.used.projects,u.limits.projects)}</td><td>{of(u.used.ai_reads,u.limits.ai_reads)}</td>
     <td>{u.pending_request?`${usage.plans[u.pending_request.plan]?.name}${u.pending_request.note?` · ${u.pending_request.note}`:''}`:'—'}</td>
     <td className="admin-actions">{u.role==='admin'?'—':<><PlanPicker plans={usage.plans} value={c} onChange={v=>setChoice({...choice,['u'+u.id]:v})}/><button className="button primary small" onClick={()=>void run(async()=>{await call(`/api/admin/users/${u.id}/plan`,c);await loadAdmin()},`Đã đặt gói ${usage.plans[c.plan]?.name} cho ${u.email}.`)}>Áp dụng</button></>}</td>
    </tr>})}
   </tbody></table></div>
   <p className="plan-note">Quyền quản trị chỉ cấp trên máy chủ: <code>python scripts/manage_admin.py grant email</code>.</p>
  </Modal>}
 </>
}
