import {useEffect,useRef,useState,type ReactNode} from 'react'
import App from './App'
import {Icon} from './components/Icon'
import {setDraftOwner} from './draftOwner'
import './account.css'

type User={id:number;email:string}
const base=import.meta.env.VITE_API_BASE||''
async function accountRequest(path:string,body?:unknown):Promise<User>{
 const response=await fetch(base+'/api/auth/'+path,{credentials:'include',signal:AbortSignal.timeout(15000),method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-SolarOpt-Request':'1'},...(body===undefined?{}:{body:JSON.stringify(body)})})
 if(!response.ok){const data=await response.json();throw new Error(typeof data.detail==='string'?data.detail:'Kiểm tra email và mật khẩu (10–128 ký tự).')}
 return response.json()
}

function AuthDialog({children,busy,onDismiss}:{children:ReactNode;busy:boolean;onDismiss:()=>void}){
 const ref=useRef<HTMLDialogElement>(null)
 useEffect(()=>{
  const dialog=ref.current!
  const previousFocus=document.activeElement instanceof HTMLElement?document.activeElement:null
  const previousOverflow=document.body.style.overflow
  dialog.showModal()
  document.body.style.overflow='hidden'
  dialog.querySelector<HTMLInputElement>('#account-email')?.focus()
  return()=>{
   dialog.close()
   document.body.style.overflow=previousOverflow
   if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true})
  }
 },[])
 return <dialog ref={ref} className="account-dialog" aria-labelledby="account-title" aria-describedby="account-description" onKeyDown={event=>{
  if(event.key!=='Tab')return
  const controls=Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled)'))
  const first=controls[0],last=controls.at(-1)
  if(!first){event.preventDefault();return}
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
 }} onCancel={event=>{event.preventDefault();if(!busy)onDismiss()}} onClick={event=>{
  if(event.target!==event.currentTarget||busy)return
  const bounds=event.currentTarget.getBoundingClientRect()
  if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)onDismiss()
 }}>
  <button type="button" className="account-close icon-button" aria-label="Đóng đăng nhập" disabled={busy} onClick={onDismiss}><Icon name="close" size={20}/></button>
  {children}
 </dialog>
}

export default function Account(){
 const [user,setUser]=useState<User|null>(null),[ready,setReady]=useState(false),[mode,setMode]=useState<'login'|'register'|null>(null)
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 useEffect(()=>{accountRequest('me').then(value=>{setDraftOwner(value.id);setUser(value)}).catch(()=>setDraftOwner(null)).finally(()=>setReady(true))},[])
 function closeAuth(){if(busy)return;setMode(null);setPassword('');setError('')}
 async function submit(event:React.FormEvent){event.preventDefault();setBusy(true);setError('');try{const value=await accountRequest(mode||'login',{email,password});setDraftOwner(value.id);setUser(value);setPassword('');setMode(null)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function logout(){setBusy(true);setError('');try{await accountRequest('logout',{});setDraftOwner(null);setUser(null)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 if(!ready)return <p className="account-loading" role="status">Đang kiểm tra tài khoản…</p>
 return <>
  <div className="account-shell"><section className="account-bar" aria-label="Tài khoản">
   <span>{user?user.email:'Chế độ khách · đăng nhập để lưu lịch sử riêng'}</span>
   {user?<button className="button secondary small" disabled={busy} onClick={logout}>Đăng xuất</button>:<button className="button secondary small" onClick={()=>{setMode('login');setError('')}}>Đăng nhập / Đăng ký</button>}
   {error&&!mode&&<span role="alert">{error}</span>}
  </section></div>
  <App key={user?.id??'guest'}/>
  {mode&&<AuthDialog busy={busy} onDismiss={closeAuth}>
   <form className="account-form" aria-busy={busy} onSubmit={submit}>
    <h2 id="account-title">{mode==='login'?'Đăng nhập':'Tạo tài khoản'}</h2>
    <p id="account-description">Lưu lịch sử tính toán riêng theo tài khoản. Bản nháp tự lưu trên trình duyệt này.</p>
    <label htmlFor="account-email">Email</label>
    <input id="account-email" type="email" autoComplete="username" required maxLength={254} disabled={busy} value={email} onChange={e=>setEmail(e.target.value)}/>
    <label htmlFor="account-password">Mật khẩu (10–128 ký tự)</label>
    <input id="account-password" type="password" autoComplete={mode==='login'?'current-password':'new-password'} required minLength={10} maxLength={128} disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/>
    {error&&<p role="alert">{error}</p>}
    <div className="account-form-actions">
     <button className="button primary" disabled={busy}>{busy?'Đang xử lý…':mode==='login'?'Đăng nhập':'Đăng ký'}</button>
     <button type="button" className="text-button" disabled={busy} onClick={()=>{setMode(mode==='login'?'register':'login');setError('')}}>{mode==='login'?'Tạo tài khoản mới':'Đã có tài khoản'}</button>
    </div>
    <button type="button" className="account-guest text-button" disabled={busy} onClick={closeAuth}>Tiếp tục với chế độ khách</button>
   </form>
  </AuthDialog>}
 </>
}
