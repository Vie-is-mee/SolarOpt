import {useState} from 'react'
import type {Point} from '../studioTypes'
import {edgeLength} from '../roofEdit'
import {Icon} from './Icon'

/** Collapsed by default. Follows what is selected on the drawing: nothing, or one roof node. */
export function NodeTools({ring,selected,adding,onAdding,onDelete,onMove,onEdge}:{ring:Point[];selected:number|null;adding:boolean;onAdding:(v:boolean)=>void;onDelete:(i:number)=>void;onMove:(i:number,p:Point)=>void;onEdge:(i:number,side:1|-1,length:number)=>void}){
 const [open,setOpen]=useState(false),node=selected!=null?ring[selected]:null
 const shown=open||adding||!!node
 const number=(label:string,value:number,commit:(v:number)=>void,key:string)=><label key={key}>{label}<input aria-label={label} type="number" step=".01" min="0" defaultValue={Number(value.toFixed(3))} key={`${key}-${value}`} onBlur={e=>{const v=Number(e.target.value);if(Number.isFinite(v)&&Math.abs(v-value)>.0005)commit(v)}} onKeyDown={e=>{if(e.key==='Enter')e.currentTarget.blur()}}/><small>m</small></label>
 return <details className="node-tools" open={shown} onToggle={e=>setOpen(e.currentTarget.open)}>
  <summary><Icon name="move" size={14}/>Công cụ node<span>{ring.length} node{node?` · đang chọn node ${selected!+1}`:''}</span></summary>
  <div className="node-tools-body">
   <button type="button" className={`button small ${adding?'primary':'secondary'}`} aria-pressed={adding} onClick={()=>onAdding(!adding)}><Icon name="plus" size={14}/>{adding?'Đang thêm node · bấm lên mái':'Thêm node'}</button>
   {adding&&<p className="muted-note">Bấm vào chỗ cần node: node tự nối vào cạnh gần nhất. <kbd>Esc</kbd> để dừng.</p>}
   {!adding&&!node&&<p className="muted-note">Bấm một node trên mái để sửa số hoặc xóa.</p>}
   {node&&<>
    <div className="node-fields">{number('X',node.x,v=>onMove(selected!,{x:v,y:node.y}),'x')}{number('Y',node.y,v=>onMove(selected!,{x:node.x,y:v}),'y')}</div>
    <div className="node-fields">{number('Cạnh tới node sau',edgeLength(ring,selected!,1),v=>onEdge(selected!,1,v),'next')}{number('Cạnh tới node trước',edgeLength(ring,selected!,-1),v=>onEdge(selected!,-1,v),'prev')}</div>
    <p className="muted-note">Node đang chọn đứng yên, đầu kia của cạnh dời theo chiều dài bạn nhập.</p>
    <button type="button" className="button secondary small" disabled={ring.length<=3} onClick={()=>onDelete(selected!)}><Icon name="trash" size={14}/>Xóa node (Backspace)</button>
   </>}
  </div>
 </details>
}
