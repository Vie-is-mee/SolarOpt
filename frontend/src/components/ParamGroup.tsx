import type {ReactNode} from 'react'

/** One collapsible settings category: a compact row with its current value; opens to edit. */
export function ParamGroup({n,title,summary,open,onToggle,children}:{n:number;title:string;summary:string;open:boolean;onToggle:()=>void;children:ReactNode}){
 return <section className={`param-group${open?' open':''}`}>
  <button type="button" className="param-head" aria-expanded={open} onClick={onToggle}>
   <span className="param-num">{n}</span>
   <span className="param-text"><strong>{title}</strong><small>{summary}</small></span>
   <span className="param-chevron" aria-hidden="true">›</span>
  </button>
  {open&&<div className="param-body">{children}</div>}
 </section>
}
