import type {PlacedPanel} from './studioTypes'

// Figures derived for the report only from what the optimizer returned, so the report never
// computes energy itself: each panel's kWh = kWp x plane irradiance x PR x (1 - shading loss).

/** Annual energy from the ideal plane-of-array yield down to delivered energy (kWh/year). */
export function lossBreakdown(panels:PlacedPanel[],performanceRatio:number){
 const delivered=panels.reduce((s,p)=>s+p.annual_energy_kwh,0)
 const unshaded=panels.reduce((s,p)=>s+(p.shading_loss_pct<100?p.annual_energy_kwh/(1-p.shading_loss_pct/100):0),0)
 const ideal=performanceRatio>0?unshaded/performanceRatio:unshaded
 return {ideal,shading:unshaded-delivered,system:ideal-unshaded,delivered}
}

export const LOSS_BINS:{label:string;max:number}[]=[{label:'< 1%',max:1},{label:'1–3%',max:3},{label:'3–5%',max:5},{label:'5–10%',max:10},{label:'≥ 10%',max:Infinity}]
/** Panel counts per shading-loss band. */
export function shadingHistogram(panels:PlacedPanel[]){
 const counts=LOSS_BINS.map(()=>0)
 for(const p of panels)counts[LOSS_BINS.findIndex(b=>p.shading_loss_pct<b.max)]++
 return LOSS_BINS.map((b,i)=>({label:b.label,count:counts[i]}))
}

/** Panels, power and energy per roof face, in the order faces first appear. */
export function faceSummary(panels:PlacedPanel[],powerW:number,labels:Record<string,string>={}){
 const rows=new Map<string,{id:string;label:string;count:number;kwp:number;kwh:number;loss:number}>()
 for(const p of panels){
  const id=p.face_id||'roof',row=rows.get(id)||{id,label:labels[id]||(id==='roof'?'Mái chính':id),count:0,kwp:0,kwh:0,loss:0}
  row.count++;row.kwp+=powerW/1000;row.kwh+=p.annual_energy_kwh;row.loss+=p.shading_loss_pct;rows.set(id,row)
 }
 return Array.from(rows.values(),r=>({...r,loss:r.count?r.loss/r.count:0}))
}

/** A round axis step giving about `ticks` divisions up to max. */
export function niceStep(max:number,ticks=4){
 if(!(max>0))return 1
 const raw=max/ticks,base=10**Math.floor(Math.log10(raw)),f=raw/base
 return (f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*base
}

/** Green (unshaded) through amber to red at 10 % shading loss and above. */
export function lossColor(pct:number){
 const t=Math.max(0,Math.min(1,pct/10))
 const stops=[[35,107,80],[226,165,38],[196,64,46]]
 const [a,b,u]=t<.5?[stops[0],stops[1],t*2]:[stops[1],stops[2],(t-.5)*2]
 return '#'+a.map((v,i)=>Math.round(v+(b[i]-v)*u).toString(16).padStart(2,'0')).join('')
}
