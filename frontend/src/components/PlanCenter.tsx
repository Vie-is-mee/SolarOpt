import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react'
import {accountIdentity} from '../draftOwner'
import {Icon} from './Icon'
import {vnd} from '../format'

type Limits={projects:number|null;project_window:number|null;ai_reads:number|null}
type Plan={name:string;price_vnd_month:number;projects:number;ai_reads:number;features:string[];project_window_days:number|null;seats:number}
type Member={id:number;email:string;role:'owner'|'member'}
type Team={id:number;name:string;role:'owner'|'member';plan:string;plan_name:string;plan_until:number|null;seats:number;members:Member[]}
type Usage={plan:string;plan_name:string;plan_until:number|null;limits:Limits;used:{projects:number;ai_reads:number};plans:Record<string,Plan>;is_admin:boolean;pending_request?:string|null;team:Team|null}
type AdminUser={id:number;email:string;role:string;plan:string;plan_name:string;plan_until:number|null;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null;team:{name:string;role:string}|null}
type AdminTeam={id:number;name:string;plan:string;plan_until:number|null;owner:string;members:number;seats:number;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null}
const base=import.meta.env.VITE_API_BASE||''
const date=(t:number|null)=>t?new Date(t*1000).toLocaleDateString('vi-VN'):'—'
const of=(used:number,limit:number|null)=>limit===null?`${used} · không giới hạn`:`${used}/${limit}`
async function call<T>(path:string,body?:unknown):Promise<T>{
 const r=await fetch(base+path,{credentials:'include',method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-SolarOpt-Request':'1','X-SolarOpt-User':accountIdentity()},...(body===undefined?{}:{body:JSON.stringify(body)})})
 if(!r.ok){let d='';try{d=(await r.json()).detail}catch{}throw new Error(typeof d==='string'&&d?d:`Yêu cầu chưa thành công (${r.status}).`)}
 return r.json()
}

// Line drawing for the plans header: rooftops with panel rows under a low sun. Drawn in code (thin strokes in
// the brand greens) so it stays crisp and matches the app instead of a stock photo.
function PlanArt(){
 // House: walls from the ground line G, gable roof; a panel array lies on the left slope (A eave -> B ridge).
 const G=168,house=(x:number,w:number,h:number)=>{const A={x,y:G-h},B={x:x+w/2,y:G-h-w*.36},len=Math.hypot(B.x-A.x,B.y-A.y),u={x:(B.x-A.x)/len,y:(B.y-A.y)/len},n={x:u.y,y:-u.x}
  const at=(t:number,d=0)=>({x:A.x+(B.x-A.x)*t+n.x*d,y:A.y+(B.y-A.y)*t+n.y*d}),p=[at(.16,1.5),at(.84,1.5),at(.84,8),at(.16,8)]
  return <g key={x}><path d={`M${x} ${G}V${A.y}L${B.x} ${B.y}L${x+w} ${A.y}V${G}`} className="pa-house"/>
   <path d={`M${p.map(q=>q.x.toFixed(1)+' '+q.y.toFixed(1)).join('L')}Z`} className="pa-panel"/>
   {[.38,.61].map(t=>{const q1=at(t,1.5),q2=at(t,8);return <path key={t} d={`M${q1.x} ${q1.y}L${q2.x} ${q2.y}`} className="pa-cell"/>})}
   <rect x={x+w*.6} y={G-h*.58} width={w*.16} height={h*.58} className="pa-door"/><rect x={x+w*.18} y={G-h*.7} width={w*.18} height={h*.24} className="pa-door"/></g>}
 return <svg className="plan-art" viewBox="0 0 1000 170" preserveAspectRatio="xMaxYMax slice" aria-hidden="true">
  <defs><linearGradient id="pa-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f4f9ee"/><stop offset="1" stopColor="#e5f1dc"/></linearGradient></defs>
  <rect width="1000" height="170" fill="url(#pa-sky)"/>
  <path d="M720 168a170 170 0 0 1 280 -92" className="pa-arc"/><path d="M760 168a130 130 0 0 1 220 -70" className="pa-arc"/>
  <circle cx="905" cy="58" r="19" className="pa-sun"/>{Array.from({length:12},(_,i)=>{const a=Math.PI*2*i/12,c=Math.cos(a),s=Math.sin(a);return <path key={i} d={`M${905+c*27} ${58-s*27}L${905+c*35} ${58-s*35}`} className="pa-ray"/>})}
  <path d="M380 160C520 146 640 152 760 140S900 144 1000 132V170H380Z" className="pa-hill"/>
  {[[480,74,34],[575,96,44],[690,70,30],[780,104,48],[905,78,36]].map(([x,w,h])=>house(x,w,h))}
  <path d="M380 168.5H1000" className="pa-ground"/>
 </svg>
}
const PLAN_ICON:Record<string,string>={free:'sun',pro:'bolt',business:'building'}
function Modal({title,onClose,children,wide=false,art=false}:{title:string;onClose:()=>void;children:ReactNode;wide?:boolean;art?:boolean}){
 const ref=useRef<HTMLDialogElement>(null)
 useEffect(()=>{const d=ref.current!;d.showModal();return()=>d.close()},[])
 return <dialog ref={ref} className={`account-dialog plan-dialog${wide?' wide':''}`} aria-label={title} onCancel={e=>{e.preventDefault();onClose()}}>
  <button type="button" className="account-close icon-button" aria-label="Đóng" onClick={onClose}><Icon name="close" size={20}/></button>
  {art&&<div className="plan-hero"><PlanArt/><div><span className="plan-eyebrow">SolarOpt Studio</span><h2>{title}</h2></div></div>}
  <div className="plan-body">{!art&&<h2>{title}</h2>}{children}</div>
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

  {open==='plans'&&<Modal title="Gói sử dụng SolarOpt" art onClose={()=>setOpen(null)}>
   <p className="plan-note">{left===0?'Bạn đã dùng hết lượt của gói hiện tại. ':''}Mỗi dự án chỉ trừ một lượt; tính lại hoặc so sánh 3 phương án của cùng dự án không trừ thêm.{usage.plan_until?` Gói hiện tại hiệu lực đến ${date(usage.plan_until)}.`:''}</p>
   <div className="plan-grid">{Object.entries(usage.plans).map(([id,p])=><article key={id} className={`plan-card plan-${id}${usage.plan===id?' current':''}`}>
    {id==='pro'&&<span className="plan-ribbon">Phổ biến</span>}
    <div className="plan-card-head"><span className="plan-icon"><Icon name={PLAN_ICON[id]||'sparkles'} size={18}/></span><h3>{p.name}</h3></div>
    <div className="plan-price"><strong>{p.price_vnd_month?vnd(p.price_vnd_month,''):'0'}</strong><small>{p.price_vnd_month?'đ / tháng':'đ · miễn phí'}</small></div>
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
