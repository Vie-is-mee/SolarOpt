import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react'
import {accountIdentity} from '../draftOwner'
import {Icon} from './Icon'
import {vnd} from '../format'

type Limits={projects:number|null;ai_reads:number|null;chat?:number|null;cycle_end?:number|null}
type Plan={name:string;price_vnd:number;period:'month'|'year'|null;projects:number;ai_reads:number;chat?:number;features:string[];seats:number;price_per_project_vnd:number}
type StorageTerms={tiers:{max_projects:number;fee_vnd_month:number}[];months_free_per_year:number;grace_days:number;trial_keep_days:number}
type Member={id:number;email:string;role:'owner'|'member'}
type Team={id:number;name:string;role:'owner'|'member';plan:string;plan_name:string;plan_until:number|null;seats:number;members:Member[]}
type Usage={plan:string;plan_name:string;plan_until:number|null;limits:Limits;used:{projects:number;ai_reads:number;chat?:number};plans:Record<string,Plan>;storage_terms:StorageTerms;storage_due:number;is_admin:boolean;pending_request?:string|null;team:Team|null}
type StoredProject={owner:string;owner_label?:string;project_key:string;project_name:string;first_used:number;covered_until:number;storage_until:number|null;purged_at:number|null;keep_until:number;delete_after:number;state:'included'|'paid'|'grace'|'expired'|'purged';state_label:string}
type StorageAccount={owner:string;owner_label?:string;projects:number;fee_vnd_month:number|null;pending_months:number|null}
type StorageBill={billable:number;fee_vnd_month:number|null;pending_months:number|null}
type AdminUser={id:number;email:string;role:string;plan:string;plan_name:string;plan_until:number|null;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null;team:{name:string;role:string}|null}
type AdminTeam={id:number;name:string;plan:string;plan_name:string;plan_until:number|null;owner:string;members:number;seats:number;used:{projects:number;ai_reads:number};limits:Limits;pending_request:{plan:string;note:string}|null}
type Choice={plan:string;periods:number}
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
const PLAN_ICON:Record<string,string>={free:'sun',single:'bolt',start:'building',team:'building',pro:'building'}
const STORAGE_MONTHS=[1,3,6,12]
const PERIOD_LABEL={month:'tháng',year:'năm'} as const
const STATE_TONE:Record<StoredProject['state'],string>={included:'',paid:'',grace:'amber',expired:'red',purged:'red'}
function Modal({title,onClose,children,wide=false,art=false}:{title:string;onClose:()=>void;children:ReactNode;wide?:boolean;art?:boolean}){
 const ref=useRef<HTMLDialogElement>(null)
 useEffect(()=>{const d=ref.current!;d.showModal();return()=>d.close()},[])
 return <dialog ref={ref} className={`account-dialog plan-dialog${wide?' wide':''}`} aria-label={title} onCancel={e=>{e.preventDefault();onClose()}}>
  <button type="button" className="account-close icon-button" aria-label="Đóng" onClick={onClose}><Icon name="close" size={20}/></button>
  {art&&<div className="plan-hero"><PlanArt/><div><span className="plan-eyebrow">SolarOpt Studio</span><h2>{title}</h2></div></div>}
  <div className="plan-body">{!art&&<h2>{title}</h2>}{children}</div>
 </dialog>
}

function PlanPicker({plans,value,onChange}:{plans:Record<string,Plan>;value:Choice;onChange:(v:Choice)=>void}){
 const period=plans[value.plan]?.period
 return <><select aria-label="Gói" value={value.plan} onChange={e=>onChange({plan:e.target.value,periods:1})}>{Object.entries(plans).map(([id,p])=><option key={id} value={id}>{p.name}</option>)}</select>
  {period&&<select aria-label={`Số ${PERIOD_LABEL[period]}`} value={value.periods} onChange={e=>onChange({...value,periods:Number(e.target.value)})}>{(period==='month'?[1,3,6,12]:[1,2,3]).map(m=><option key={m} value={m}>{m} {PERIOD_LABEL[period]}</option>)}</select>}</>
}

function PlanCard({id,p,usage,signedIn,team,onLogin,onRequest}:{id:string;p:Plan;usage:Usage;signedIn:boolean;team:Team|null;onLogin:()=>void;onRequest:()=>void}){
 return <article className={`plan-card plan-${id}${usage.plan===id?' current':''}`}>
  {id==='team'&&<span className="plan-ribbon">Khuyên dùng</span>}
  <div className="plan-card-head"><span className="plan-icon"><Icon name={PLAN_ICON[id]||'sparkles'} size={18}/></span><h3>{p.name}</h3></div>
  <div className="plan-price"><strong>{p.price_vnd?vnd(p.price_vnd,''):'0'}</strong><small>{p.period==='year'?'đ / năm':p.period?'đ / dự án · 30 ngày':'đ · dùng thử'}</small></div>
  {p.price_per_project_vnd>0&&p.projects>1&&<p className="plan-per-project">≈ {vnd(p.price_per_project_vnd,'')} đ mỗi dự án</p>}
  <ul>{p.features.map(f=><li key={f}>{f}</li>)}</ul>
  {usage.plan===id?<span className="badge">Đang dùng</span>:id==='free'?(usage.plan==='guest'?<button className="button secondary small" onClick={onLogin}>Đăng ký dùng thử</button>:null)
   :!signedIn?<button className="button secondary small" onClick={onLogin}>Đăng nhập để mua gói</button>
   :usage.pending_request===id?<span className="badge amber">Đã gửi yêu cầu</span>
   :<button className="button primary small" onClick={onRequest}>{team?.role==='owner'?'Yêu cầu gói cho nhóm':'Gửi yêu cầu mua gói'}</button>}
 </article>
}

/** Usage meter, project plans with purchase requests, project storage, team management and the admin console. */
export function PlanCenter({signedIn,onLogin}:{signedIn:boolean;onLogin:()=>void}){
 const [usage,setUsage]=useState<Usage|null>(null),[open,setOpen]=useState<'plans'|'storage'|'team'|'admin'|null>(null),[message,setMessage]=useState(''),[error,setError]=useState('')
 const [users,setUsers]=useState<AdminUser[]>([]),[teams,setTeams]=useState<AdminTeam[]>([]),[stored,setStored]=useState<StoredProject[]>([]),[accounts,setAccounts]=useState<StorageAccount[]>([]),[bill,setBill]=useState<StorageBill|null>(null),[choice,setChoice]=useState<Record<string,Choice>>({})
 const [months,setMonths]=useState<Record<string,number>>({})
 const [teamName,setTeamName]=useState(''),[memberEmail,setMemberEmail]=useState('')
 const refresh=useCallback(()=>{call<Usage>('/api/account/usage').then(setUsage).catch(()=>{})},[])
 useEffect(()=>{refresh()},[refresh,signedIn])
 useEffect(()=>{
  const used=()=>refresh(),quota=()=>{refresh();setMessage('');setError('');setOpen('plans')}
  window.addEventListener('solaropt-usage',used);window.addEventListener('solaropt-quota',quota)
  return()=>{window.removeEventListener('solaropt-usage',used);window.removeEventListener('solaropt-quota',quota)}
 },[refresh])
 const show=(view:'plans'|'storage'|'team'|'admin')=>{setMessage('');setError('');setOpen(view);if(view==='admin')void loadAdmin();if(view==='storage')void loadStorage()}
 async function run(action:()=>Promise<unknown>,ok:string){setError('');setMessage('');try{await action();setMessage(ok);refresh()}catch(e){setError((e as Error).message)}}
 async function loadAdmin(){try{const [u,t,st]=await Promise.all([call<AdminUser[]>('/api/admin/users'),call<AdminTeam[]>('/api/admin/teams'),call<{projects:StoredProject[];accounts:StorageAccount[]}>('/api/admin/storage')]);setUsers(u);setTeams(t);setStored(st.projects);setAccounts(st.accounts)}catch(e){setError((e as Error).message)}}
 async function loadStorage(){try{const st=await call<StorageBill&{projects:StoredProject[]}>('/api/account/storage');setStored(st.projects);setBill(st)}catch(e){setError((e as Error).message)}}
 if(!usage)return null
 const team=usage.team,unlimited=usage.limits.projects===null,terms=usage.storage_terms
 const left=unlimited?1:Math.max(0,usage.limits.projects!-usage.used.projects)
 const pick=(key:string,fallback:string)=>choice[key]||{plan:fallback in usage.plans?fallback:'free',periods:1}
 const monthsOf=(key:string)=>months[key]||1
 const money=(n:number)=>vnd(n,'')+' đ'
 const billed=(m:number)=>m-terms.months_free_per_year*Math.floor(m/12)
 const tierList=terms.tiers.map(t=>`tới ${t.max_projects} dự án ${money(t.fee_vnd_month)}`).join(' · ')
 const lastTier=terms.tiers[terms.tiers.length-1].max_projects
 const plansBy=(period:Plan['period'])=>Object.entries(usage.plans).filter(([,p])=>p.period===period)
 const request=(id:string,p:Plan)=>()=>void run(()=>call('/api/account/upgrade-request',{plan:id,note:''}),`Đã gửi yêu cầu mua gói ${p.name}. Quản trị viên sẽ liên hệ thanh toán và kích hoạt.`)
 const card=([id,p]:[string,Plan])=><PlanCard key={id} id={id} p={p} usage={usage} signedIn={signedIn} team={team} onLogin={()=>{setOpen(null);onLogin()}} onRequest={request(id,p)}/>
 const extend=(key:string,feeMonth:number|null)=><select aria-label="Số tháng lưu trữ" value={monthsOf(key)} onChange={e=>setMonths({...months,[key]:Number(e.target.value)})}>{STORAGE_MONTHS.map(m=><option key={m} value={m}>{m} tháng{feeMonth===null?'':` · ${money(feeMonth*billed(m))}`}</option>)}</select>
 return <>
  <span className={`plan-meter${left===0?' empty':''}`} title={usage.plan==='guest'?'Khách: tính thử theo ngày':'Mỗi dự án chỉ trừ một lượt; khi còn gói, sửa lại dự án đã tính trong 12 tháng không trừ thêm'}>
   <strong>{usage.plan_name}</strong> · {unlimited?'không giới hạn':<>{usage.used.projects}/{usage.limits.projects} dự án{usage.plan==='guest'?' hôm nay':usage.limits.cycle_end?` · đến ${date(usage.limits.cycle_end)}`:''}{usage.plan!=='guest'&&<> · AI {usage.used.ai_reads}/{usage.limits.ai_reads}{usage.limits.chat!=null&&<> · trợ lý {usage.used.chat??0}/{usage.limits.chat}</>}</>}</>}
  </span>
  {!usage.is_admin&&<button className="button secondary small" onClick={()=>show('plans')}>{usage.plan==='free'||usage.plan==='guest'?'Mua gói':'Gói của bạn'}</button>}
  {signedIn&&!usage.is_admin&&<button className={`button secondary small${usage.storage_due?' attention':''}`} onClick={()=>show('storage')}>Lưu trữ{usage.storage_due?` · ${usage.storage_due} sắp xóa`:''}</button>}
  {signedIn&&<button className="button secondary small" onClick={()=>show('team')}>{team?`Nhóm: ${team.name}`:'Nhóm'}</button>}
  {usage.is_admin&&<button className="button secondary small" onClick={()=>show('admin')}>Quản trị</button>}

  {open==='plans'&&<Modal title="Gói dự án SolarOpt" art onClose={()=>setOpen(null)}>
   <p className="plan-note">{left===0?'Bạn đã dùng hết số dự án của gói trong chu kỳ này. ':''}Gói bán theo <strong>số dự án</strong>: mỗi dự án chỉ trừ một lượt. Khi còn gói, tính lại, so sánh 3 phương án hay sửa dự án đã tính trong 12 tháng đều không trừ thêm, kể cả khi công trình kéo dài qua chu kỳ sau. Dự án lẻ dùng trong 30 ngày, gói năm trong 12 tháng; dự án chưa dùng không cộng dồn sang chu kỳ sau. Trên 60 dự án mỗi năm: liên hệ để nhận báo giá.{usage.plan_until?` Gói hiện tại hiệu lực đến ${date(usage.plan_until)}.`:''}</p>
   <h3 className="plan-group">Gói theo năm</h3>
   <div className="plan-grid">{plansBy('year').map(card)}</div>
   <h3 className="plan-group">Dùng lẻ và dùng thử</h3>
   <div className="plan-grid">{plansBy('month').map(card)}{plansBy(null).map(card)}</div>
   <div className="plan-storage-terms"><Icon name="shield" size={18}/><p><strong>Lưu trữ hồ sơ dự án:</strong> dữ liệu mỗi dự án (ảnh, biên mái, phương án, bản duyệt) được giữ trong thời hạn gói đã dùng nó. Gói năm còn hiệu lực lưu miễn phí thêm bằng số dự án của gói. Phần còn lại tính phí theo tháng cho cả tài khoản: <strong>{tierList}</strong>; trên {lastTier} dự án báo giá riêng; trả 12 tháng chỉ tính {12-terms.months_free_per_year} tháng. Quá hạn {terms.grace_days} ngày không gia hạn, dữ liệu dự án có thể bị xóa và không khôi phục được; hãy tải gói dự án (.json) và báo cáo PDF về máy trước.</p></div>
   <p className="plan-note">Thanh toán trực tuyến chưa tích hợp: sau khi gửi yêu cầu, quản trị viên liên hệ, xuất hóa đơn và kích hoạt gói.</p>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
  </Modal>}

  {open==='storage'&&<Modal title="Lưu trữ dữ liệu dự án" onClose={()=>setOpen(null)} wide>
   <p className="plan-note">Dự án được lưu trong thời hạn gói đã dùng nó{usage.plan==='free'?` (gói dùng thử: ${terms.trial_keep_days} ngày)`:''}. Gói năm còn hiệu lực lưu miễn phí thêm bằng số dự án của gói. Phần còn lại: <strong>{tierList}</strong>. Quá {terms.grace_days} ngày sau ngày hết hạn mà chưa gia hạn, dự án bị ẩn và có thể bị xóa hẳn khỏi máy chủ.</p>
   {bill&&bill.billable>0&&<div className="admin-actions"><span><strong>{bill.billable} dự án</strong> cần đóng phí · {bill.fee_vnd_month===null?'báo giá riêng':`${money(bill.fee_vnd_month)} / tháng`}</span>{bill.pending_months?<span className="badge amber">Đã yêu cầu {bill.pending_months} tháng</span>:<>{extend('account',bill.fee_vnd_month)}<button className="button primary small" onClick={()=>void run(async()=>{await call('/api/account/storage-request',{months:monthsOf('account')});await loadStorage()},`Đã gửi yêu cầu gia hạn lưu trữ ${monthsOf('account')} tháng. Quản trị viên sẽ liên hệ thanh toán.`)}>Gửi yêu cầu</button></>}</div>}
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Dự án</th><th>Dùng từ</th><th>Lưu đến</th><th>Trạng thái</th><th>Xóa sau</th></tr></thead><tbody>
    {stored.map(r=><tr key={r.owner+'|'+r.project_key}><td>{r.project_name}</td><td>{date(r.first_used)}</td><td>{date(r.keep_until)}</td>
     <td><span className={`badge ${STATE_TONE[r.state]}`}>{r.state_label}</span></td><td>{r.state==='purged'?date(r.purged_at):date(r.delete_after)}</td></tr>)}
    {!stored.length&&<tr><td colSpan={5}>Chưa có dự án nào được tính bằng tài khoản này.</td></tr>}
   </tbody></table></div>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
  </Modal>}

  {open==='team'&&<Modal title={team?`Nhóm ${team.name}`:'Tạo nhóm công ty'} onClose={()=>setOpen(null)}>
   {!team?<form className="team-form" onSubmit={e=>{e.preventDefault();void run(()=>call('/api/team',{name:teamName}),'Đã tạo nhóm. Mua gói cho nhóm để thêm kỹ sư và dùng chung số dự án.')}}>
     <p className="plan-note">Nhóm dùng chung số dự án của gói và xem chung lịch sử dự án. Bạn sẽ là chủ nhóm.</p>
     <label className="field"><span>Tên công ty / nhóm</span><input value={teamName} minLength={2} maxLength={80} required onChange={e=>setTeamName(e.target.value)}/></label>
     <button className="button primary small">Tạo nhóm</button>
    </form>:<>
     <p className="plan-note">Gói nhóm: <strong>{team.plan_name}</strong>{team.plan_until?` đến ${date(team.plan_until)}`:''} · {team.members.length}/{team.seats} chỗ.{team.plan==='free'?' Gói năm mở 2–10 chỗ, dùng chung số dự án và lịch sử.':''}</p>
     <ul className="team-members">{team.members.map(m=><li key={m.id}><span>{m.email}</span><small>{m.role==='owner'?'Chủ nhóm':'Kỹ sư'}</small>
      {team.role==='owner'&&m.role!=='owner'&&<button className="text-button danger" onClick={()=>void run(()=>call(`/api/team/members/${m.id}/remove`,{}),`Đã xóa ${m.email} khỏi nhóm.`)}>Xóa</button>}</li>)}</ul>
     {team.role==='owner'&&<form className="team-form inline" onSubmit={e=>{e.preventDefault();void run(()=>call('/api/team/members',{email:memberEmail}),`Đã thêm ${memberEmail}.`).then(()=>setMemberEmail(''))}}>
      <label className="field"><span>Thêm kỹ sư (email đã đăng ký)</span><input type="email" value={memberEmail} required onChange={e=>setMemberEmail(e.target.value)}/></label>
      <button className="button primary small">Thêm</button>
     </form>}
     <div className="inline-actions">{team.role==='owner'&&team.plan==='free'&&<button className="button secondary small" onClick={()=>show('plans')}>Mua gói cho nhóm</button>}
      <button className="text-button danger" onClick={()=>{if(confirm(team.role==='owner'?'Giải tán nhóm này?':'Rời nhóm này?'))void run(()=>call('/api/team/leave',{}),team.role==='owner'?'Đã giải tán nhóm.':'Đã rời nhóm.')}}>{team.role==='owner'?'Giải tán nhóm':'Rời nhóm'}</button></div>
    </>}
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
  </Modal>}

  {open==='admin'&&<Modal title="Quản trị người dùng, nhóm, gói và lưu trữ" onClose={()=>setOpen(null)} wide>
   {message&&<p role="status" className="plan-ok">{message}</p>}{error&&<p role="alert">{error}</p>}
   <h3>Nhóm công ty</h3>
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Nhóm</th><th>Chủ nhóm</th><th>Gói</th><th>Hết hạn</th><th>Thành viên</th><th>Dự án</th><th>Yêu cầu</th><th>Đặt gói</th></tr></thead><tbody>
    {teams.map(t=>{const c=pick('t'+t.id,t.pending_request?.plan||t.plan);return <tr key={t.id}><td>{t.name}</td><td>{t.owner}</td><td>{t.plan_name}</td><td>{date(t.plan_until)}</td><td>{t.members}/{t.seats}</td><td>{of(t.used.projects,t.limits.projects)}</td>
     <td>{t.pending_request?usage.plans[t.pending_request.plan]?.name||t.pending_request.plan:'—'}</td>
     <td className="admin-actions"><PlanPicker plans={usage.plans} value={c} onChange={v=>setChoice({...choice,['t'+t.id]:v})}/><button className="button primary small" onClick={()=>void run(async()=>{await call(`/api/admin/teams/${t.id}/plan`,c);await loadAdmin()},`Đã đặt gói ${usage.plans[c.plan]?.name} cho nhóm ${t.name}.`)}>Áp dụng</button></td></tr>})}
    {!teams.length&&<tr><td colSpan={8}>Chưa có nhóm.</td></tr>}
   </tbody></table></div>
   <h3>Người dùng</h3>
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Email</th><th>Gói đang dùng</th><th>Nhóm</th><th>Dự án</th><th>AI</th><th>Yêu cầu</th><th>Đặt gói cá nhân</th></tr></thead><tbody>
    {users.map(u=>{const c=pick('u'+u.id,u.pending_request?.plan||u.plan);return <tr key={u.id}>
     <td>{u.email}{u.role==='admin'&&<small> · quản trị</small>}</td><td>{u.plan_name}</td><td>{u.team?`${u.team.name} (${u.team.role==='owner'?'chủ':'thành viên'})`:'—'}</td><td>{of(u.used.projects,u.limits.projects)}</td><td>{of(u.used.ai_reads,u.limits.ai_reads)}</td>
     <td>{u.pending_request?`${usage.plans[u.pending_request.plan]?.name||u.pending_request.plan}${u.pending_request.note?` · ${u.pending_request.note}`:''}`:'—'}</td>
     <td className="admin-actions">{u.role==='admin'?'—':<><PlanPicker plans={usage.plans} value={c} onChange={v=>setChoice({...choice,['u'+u.id]:v})}/><button className="button primary small" onClick={()=>void run(async()=>{await call(`/api/admin/users/${u.id}/plan`,c);await loadAdmin()},`Đã đặt gói ${usage.plans[c.plan]?.name} cho ${u.email}.`)}>Áp dụng</button></>}</td>
    </tr>})}
   </tbody></table></div>
   <h3>Lưu trữ dự án</h3>
   <p className="plan-note">Phí tính theo số dự án của cả tài khoản: {tierList}. Ghi nhận sau khi đã thu. Dự án quá hạn {terms.grace_days} ngày bị ẩn; xóa hẳn bằng <code>python scripts/purge_expired_projects.py --apply</code>.</p>
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Tài khoản</th><th>Dự án tính phí</th><th>Phí/tháng</th><th>Yêu cầu</th><th>Gia hạn</th></tr></thead><tbody>
    {accounts.map(a=><tr key={a.owner}><td>{a.owner_label||a.owner}</td><td>{a.projects}</td><td>{a.fee_vnd_month===null?'Báo giá':money(a.fee_vnd_month)}</td><td>{a.pending_months?`${a.pending_months} tháng`:'—'}</td>
     <td className="admin-actions">{extend(a.owner,a.fee_vnd_month)}<button className="button primary small" onClick={()=>void run(async()=>{await call('/api/admin/storage',{owner:a.owner,months:monthsOf(a.owner)});await loadAdmin()},`Đã gia hạn lưu trữ ${a.owner_label||a.owner} thêm ${monthsOf(a.owner)} tháng.`)}>Ghi nhận đã thu</button></td></tr>)}
    {!accounts.length&&<tr><td colSpan={5}>Chưa có tài khoản nào cần đóng phí lưu trữ.</td></tr>}
   </tbody></table></div>
   <div className="table-scroll"><table className="admin-table"><thead><tr><th>Chủ sở hữu</th><th>Dự án</th><th>Lưu đến</th><th>Trạng thái</th></tr></thead><tbody>
    {stored.map(r=><tr key={r.owner+'|'+r.project_key}><td>{r.owner_label||r.owner}</td><td>{r.project_name}</td><td>{r.state==='purged'?'Đã xóa '+date(r.purged_at):date(r.keep_until)}</td><td><span className={`badge ${STATE_TONE[r.state]}`}>{r.state_label}</span></td></tr>)}
    {!stored.length&&<tr><td colSpan={4}>Chưa có dự án nào cần lưu trữ.</td></tr>}
   </tbody></table></div>
   <p className="plan-note">Quyền quản trị chỉ cấp trên máy chủ: <code>python scripts/manage_admin.py grant email</code>.</p>
  </Modal>}
 </>
}
