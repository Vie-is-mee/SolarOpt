import {useEffect, useRef, useState} from 'react'
import {factChip, type AssistantAction, type ChatMessage} from '../assistantTypes'
import {studioApi as api} from '../services/studioApi'
import {Icon} from './Icon'

type Context=Omit<Parameters<typeof api.chat>[0],'messages'|'demo'>

/** Models answer in light Markdown: keep **bold**, *italic* and `code`, drop the markers, never inject HTML. */
function Rich({text}:{text:string}){
 return <>{text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g).map((part,i)=>part.startsWith('**')&&part.endsWith('**')&&part.length>4?<strong key={i}>{part.slice(2,-2)}</strong>:part.startsWith('`')&&part.endsWith('`')&&part.length>2?<code key={i}>{part.slice(1,-1)}</code>:part.startsWith('*')&&part.endsWith('*')&&part.length>2?<em key={i}>{part.slice(1,-1)}</em>:part)}</>
}

function chips(reply:NonNullable<ChatMessage['reply']>){
 const seen=new Set<string>()
 return reply.facts_used.flatMap(k=>{const c=factChip(k,reply.facts[k]);if(!c||seen.has(c.label+c.value))return [];seen.add(c.label+c.value);return [{key:k,...c}]})
}

/** Chat with the project: answers come from SolarOpt's computed facts; proposed edits wait for the engineer's click. */
export function AssistantDrawer({messages,onMessages,context,demo,suggestions,onAction,disabled}:{messages:ChatMessage[];onMessages:(m:ChatMessage[])=>void;context:()=>Context;demo:boolean;suggestions:string[];onAction:(a:AssistantAction)=>void;disabled:boolean}){
 const [open,setOpen]=useState(false),[text,setText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const list=useRef<HTMLDivElement>(null)
 useEffect(()=>{list.current?.scrollTo({top:list.current.scrollHeight,behavior:'smooth'})},[messages.length,busy,open])
 useEffect(()=>{if(!open)return;const close=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false)};window.addEventListener('keydown',close);return()=>window.removeEventListener('keydown',close)},[open])
 async function send(question:string){
  const q=question.trim();if(!q||busy)return
  const history=[...messages,{role:'user' as const,content:q}]
  onMessages(history);setText('');setBusy(true);setError('')
  try{
   const reply=await api.chat({...context(),demo,messages:history.slice(-10).map(m=>({role:m.role,content:m.content}))})
   onMessages([...history,{role:'assistant',content:reply.reply,reply,applied:[]}])
  }catch(e){setError(e instanceof Error?e.message:'Trợ lý chưa trả lời được.')}
  finally{setBusy(false)}
 }
 function apply(index:number,action:AssistantAction,i:number){
  onAction(action)
  onMessages(messages.map((m,j)=>j===index?{...m,applied:[...(m.applied||[]),i]}:m))
 }
 return <>
  <button type="button" className={'assistant-fab'+(open?' open':'')} onClick={()=>setOpen(v=>!v)} aria-expanded={open} aria-controls="assistant-drawer" title="Hỏi trợ lý về dự án đang mở"><Icon name={open?'close':'sparkles'} size={18}/><span>{open?'Đóng':'Trợ lý'}</span></button>
  {open&&<aside id="assistant-drawer" className="assistant-drawer" aria-label="Trợ lý SolarOpt">
   <header><div><strong>Trợ lý SolarOpt</strong><small>Trả lời từ số liệu đã tính · thao tác chỉ đổi khi bạn bấm</small></div>{messages.length>0&&<button type="button" className="text-button" onClick={()=>onMessages([])} disabled={busy}>Xóa hội thoại</button>}</header>
   <div className="assistant-list" ref={list} aria-live="polite">
    {!messages.length&&<p className="assistant-empty">Hỏi về mái, bóng che, số tấm, hoàn vốn, inverter; hoặc yêu cầu dời vật cản, đổi ngân sách, tính lại.</p>}
    {messages.map((m,index)=>m.role==='user'?<p key={index} className="assistant-msg user">{m.content}</p>:<div key={index} className="assistant-msg bot">
     {m.reply?.replay&&<p className="replay-note"><Icon name="history" size={13}/>{m.reply.replay}</p>}
     {m.reply?.notice&&<p className="assistant-notice"><Icon name="info" size={13}/>{m.reply.notice}</p>}
     <p className="assistant-text"><Rich text={m.content.replace(/ {2,}\n/g,'\n')}/></p>
     {m.reply&&m.reply.unverified.length>0&&<p className="assistant-unverified"><Icon name="alert" size={13}/>Số chưa đối chiếu được với dữ kiện SolarOpt: {m.reply.unverified.join(', ')}. Kiểm tra lại trước khi dùng.</p>}
     {m.reply&&<span className="advisor-refs">{chips(m.reply).map(c=><i key={c.key} title={`Dữ kiện ${c.key}, do SolarOpt tính`}>{c.label}: <b>{c.value}</b></i>)}</span>}
     {m.reply&&m.reply.actions.length>0&&<div className="assistant-actions">{m.reply.actions.map((a,i)=>{const done=m.applied?.includes(i);return <button key={i} type="button" className={'button small '+(done?'secondary':'primary')} disabled={done||disabled} onClick={()=>apply(index,a,i)}><Icon name={done?'check':'arrow'} size={14}/>{done?'Đã áp dụng: ':''}{a.label}</button>})}</div>}
     {m.reply&&<small className="assistant-meta">{m.reply.mode==='llm'?`AI · ${m.reply.model}`:'Bộ quy tắc SolarOpt'}{m.reply.replay?'':` · ${(m.reply.elapsed_ms/1000).toLocaleString('vi-VN',{maximumFractionDigits:1})} giây`}</small>}
    </div>)}
    {busy&&<p className="assistant-msg bot assistant-typing" role="status"><i/><i/><i/>Đang đọc số liệu dự án…</p>}
    {error&&<p className="tracer-error" role="alert">{error}</p>}
   </div>
   {suggestions.length>0&&<div className="assistant-suggestions">{suggestions.map(s=><button key={s} type="button" disabled={busy} onClick={()=>void send(s)}>{s}</button>)}</div>}
   <form className="assistant-input" onSubmit={e=>{e.preventDefault();void send(text)}}>
    <textarea aria-label="Câu hỏi cho trợ lý" value={text} rows={2} placeholder="Ví dụ: vì sao chỉ có 6 tấm?" onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send(text)}}}/>
    <button type="submit" className="button primary small" disabled={busy||!text.trim()}><Icon name="arrow" size={15}/>Gửi</button>
   </form>
  </aside>}
 </>
}
