import type {Obstacle,Vision} from './studioTypes'
import {PRESETS,fromPreset} from './assets'

/** Turns an image reading into draft objects on the drawing. The AI places, the engineer decides: everything stays
 * unconfirmed, a height nobody read is marked as assumed, and a new reading never touches the engineer's work. */
export type AiObject=Vision['obstacles'][number]
const presetOf=(kind?:string|null)=>PRESETS.find(p=>p.kind===kind)
const metres=(v:number)=>Math.round(v*1000)/1000
const SPOT_STEP=2

export function draftsFromVision(items:AiObject[],width:number,depth:number,source:Obstacle['source'],stamp:string):Obstacle[]{
 let spot=0
 return items.map((o,i)=>{const preset=presetOf(o.kind),around=o.scope==='around',boxW=o.width_pct/100*width,boxD=o.depth_pct/100*depth
  const unplaced=!!o.requires_placement
  // A box too small to mean anything, or one with no position, takes the library size.
  const w=unplaced?preset?.w??1:metres(Math.max(.1,boxW)),d=unplaced?preset?.d??1:metres(Math.max(.1,boxD))
  const start=unplaced&&around&&preset?fromPreset(preset,width,depth,i):null
  const x=start?start.x:unplaced?.6+spot%4*SPOT_STEP:metres(o.x_pct/100*width),y=start?start.y:unplaced?.6+Math.floor(spot/4)*SPOT_STEP:metres(o.y_pct/100*depth)
  if(unplaced&&!start)spot++
  const height=o.height_m??preset?.h??1
  return {id:`ai-${stamp}-${i}`,label:o.label+(unplaced?' · vị trí tạm':''),kind:preset?.kind??null,x,y,width_m:w,depth_m:d,height_m:height,scope:around?'neighbor':'roof',
   shape:preset?.shape==='ellipse'&&Math.abs(w-d)/Math.max(w,d)<.35?'ellipse':'rect',floors:preset?.floors??null,source,confidence:o.confidence,confirmed:false,
   ai_ref:o.id,ai_edited:false,height_assumed:o.height_m==null,position_assumed:unplaced}})}

const rectOf=(o:Obstacle)=>({x0:o.x,y0:o.y,x1:o.x+o.width_m,y1:o.y+o.depth_m})
function sameSpot(a:Obstacle,b:Obstacle){const p=rectOf(a),q=rectOf(b),w=Math.min(p.x1,q.x1)-Math.max(p.x0,q.x0),d=Math.min(p.y1,q.y1)-Math.max(p.y0,q.y0)
 if(w<=0||d<=0)return false
 return w*d/Math.min(a.width_m*a.depth_m,b.width_m*b.depth_m)>=.5}

/** Keeps every object the engineer made, moved, edited or confirmed; only untouched AI drafts are replaced,
 * and a draft is skipped where the engineer already has an object. */
export function mergeReading(existing:Obstacle[],drafts:Obstacle[]){const isDraft=(o:Obstacle)=>!!o.ai_ref&&!o.ai_edited&&!o.confirmed
 const kept=existing.filter(o=>!isDraft(o)),added=drafts.filter(d=>!kept.some(k=>sameSpot(k,d)))
 return {objects:[...kept,...added],kept:kept.length,added:added.length,skipped:drafts.length-added.length}}

const LOW_CONFIDENCE=.6
/** Why an AI object needs a look. Empty means nothing stands out; the model's own confidence is never shown as a percentage. */
export function reviewReasons(o:Obstacle){const why:string[]=[]
 if(o.position_assumed)why.push('Chưa có vị trí, đang đặt tạm')
 if(o.height_assumed)why.push('Chiều cao là giả định theo thư viện')
 if(!o.kind)why.push('AI chưa nhận ra loại vật')
 if(o.confidence<LOW_CONFIDENCE)why.push('AI chưa chắc')
 return why}

/** AI objects still waiting for the engineer: no position first, then the tallest, which cast the longest shadows. */
export const needsReview=(o:Obstacle)=>!!o.ai_ref||!!o.height_assumed||!!o.position_assumed
export function reviewQueue(objects:Obstacle[]){return objects.filter(o=>needsReview(o)&&!o.confirmed).sort((a,b)=>Number(!!b.position_assumed)-Number(!!a.position_assumed)||reviewReasons(b).length-reviewReasons(a).length||b.height_m-a.height_m)}

/** Fields that change when the engineer edits an object: it becomes their work, and what they typed is no longer assumed. */
export function touchedPatch(o:Obstacle,patch:Partial<Obstacle>):Partial<Obstacle>{const keys=Object.keys(patch).filter(k=>k!=='confirmed')
 if(!keys.length)return {}
 return {...(o.ai_ref?{ai_edited:true}:{}),...('height_m'in patch&&o.height_assumed?{height_assumed:false}:{}),...(('x'in patch||'y'in patch)&&o.position_assumed?{position_assumed:false,label:o.label.replace(/ · vị trí tạm$/,'')}:{})}}

/** Changing the library type: the shape follows, and an assumed height takes the new type's value. */
export function withKind(o:Obstacle,kind:string):Partial<Obstacle>{const preset=presetOf(kind);if(!preset)return {kind:null}
 return {kind:preset.kind,shape:o.shape==='polygon'?o.shape:preset.shape,...(o.height_assumed?{height_m:preset.h,height_assumed:true}:{})}}
