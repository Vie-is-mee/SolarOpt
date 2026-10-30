// First-visit splash: status lines describe real work (UI loaded, server check), never fake progress.
const MAX_WAIT_MS=1500,MIN_SHOW_MS=900

export async function dismissSplash(){
 const splash=document.getElementById('splash'),status=document.getElementById('splash-status')
 if(!splash)return
 const remove=()=>{splash.classList.add('done');setTimeout(()=>splash.remove(),400)}
 if(document.documentElement.classList.contains('splash-skip')){splash.remove();return}
 try{sessionStorage.setItem('solaropt-splash-seen','1')}catch{}
 const shown=performance.now()
 if(status)status.textContent='Đang kiểm tra máy chủ tính toán…'
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),MAX_WAIT_MS)
 try{
  const response=await fetch('/api/health',{signal:controller.signal})
  if(status)status.textContent=response.ok?'Sẵn sàng':'Máy chủ chưa sẵn sàng — vẫn có thể xem giao diện'
 }catch{
  if(status)status.textContent='Máy chủ đang khởi động — vẫn có thể xem giao diện'
 }finally{clearTimeout(timer)}
 // Brief minimum so the brand registers on fast connections; still capped well under 2 s.
 setTimeout(remove,Math.max(250,MIN_SHOW_MS-(performance.now()-shown)))
}
