import type {Obstacle} from '../studioTypes'
import {PRESETS} from '../assets'
import {needsReview,reviewQueue,reviewReasons} from '../aiPlacement'
import {Icon} from './Icon'

const KINDS=PRESETS.filter((p,i,a)=>a.findIndex(q=>q.kind===p.kind)===i)

/** Walks the engineer through what the AI placed, most consequential first. */
export function AiReview({objects,selected,onSelect,onKind,onHeight,onAccept,onRemove,onAcceptHeights}:{objects:Obstacle[];selected:string|null;onSelect:(id:string)=>void;onKind:(id:string,kind:string)=>void;onHeight:(id:string,height:number)=>void;onAccept:(id:string)=>void;onRemove:(id:string)=>void;onAcceptHeights:()=>void}){
 const queue=reviewQueue(objects),placed=objects.filter(needsReview).length
 if(!placed)return null
 if(!queue.length)return <section className="card ai-review done"><p><Icon name="check" size={15}/>Đã duyệt xong {placed} vật AI đặt.</p></section>
 const current=queue.find(o=>o.id===selected)||queue[0],why=reviewReasons(current),at=queue.indexOf(current),assumed=queue.filter(o=>o.height_assumed).length
 return <section className="card ai-review" aria-label="Duyệt vật thể AI đặt">
  <div className="ai-review-head"><strong><Icon name="sparkles" size={15}/>Duyệt vật AI đặt</strong><span>Còn {queue.length}/{placed}</span></div>
  <p className="ai-review-name">{current.label}</p>
  {why.length>0?<ul className="ai-review-why">{why.map(w=><li key={w}>{w}</li>)}</ul>:<p className="muted-note">AI thấy rõ vật này; đối chiếu vị trí với ảnh nền.</p>}
  <label className="field"><span>Loại trong thư viện</span><select aria-label="Loại vật thể" value={current.kind||''} onChange={e=>onKind(current.id,e.target.value)}><option value="">Khác</option>{KINDS.map(p=><option key={p.kind} value={p.kind}>{p.label}</option>)}</select></label>
  <label className="field"><span>Chiều cao{current.height_assumed?' (giả định)':''}</span><div className="input-wrap"><input aria-label="Chiều cao vật thể" key={`${current.id}-${current.height_m}`} type="number" min="0" step=".1" defaultValue={current.height_m} onBlur={e=>{const v=Number(e.target.value);if(e.target.value.trim()&&v>=0&&v!==current.height_m)onHeight(current.id,v)}} onKeyDown={e=>{if(e.key==='Enter')e.currentTarget.blur()}}/><small>m</small></div></label>
  <div className="ai-review-actions"><button type="button" className="button primary small" onClick={()=>onAccept(current.id)}><Icon name="check" size={14}/>Đúng, tiếp theo</button><button type="button" className="button secondary small" onClick={()=>onRemove(current.id)}><Icon name="trash" size={14}/>Không phải vật</button></div>
  {queue.length>1&&<button type="button" className="text-button" onClick={()=>onSelect(queue[(at+1)%queue.length].id)}>Bỏ qua, xem vật khác</button>}
  {assumed>0&&<button type="button" className="text-button" onClick={onAcceptHeights}>Giữ {assumed} chiều cao giả định làm ước lượng</button>}
 </section>
}
