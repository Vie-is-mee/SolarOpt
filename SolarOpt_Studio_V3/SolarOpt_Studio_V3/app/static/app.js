const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
let appState = null;
let currentScreen = 'setup';
let objective = 'balanced';
let selectedEntity = null;
let designTool = 'select';
let lastEvents = [];
let sunIndex = 3;
let showBlueprint = true;
let showLabels = true;
let canvasTransforms = {};

const fmtMoney = v => v == null ? '—' : `${(v/1_000_000).toFixed(v >= 100_000_000 ? 0 : 1)} triệu`;
const fmtEnergy = v => v == null ? '—' : `${(v/1000).toFixed(2)} MWh`;
const fmtPct = v => `${Number(v).toFixed(1)}%`;
const escapeHtml = s => String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function api(path, options={}){
  const r = await fetch(path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
  if(!r.ok){ let msg='Có lỗi xảy ra'; try{const e=await r.json();msg=e.detail||msg}catch{}; throw new Error(msg); }
  return r.json();
}
function toast(msg){ const el=$('#toast'); el.textContent=msg; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),2200); }
function setProjectStatus(kind,text){ const el=$('#projectStatus'); el.className=`project-status ${kind||''}`; el.querySelector('span').textContent=text; }

function switchScreen(name){
  currentScreen=name;
  $$('.screen').forEach(x=>x.classList.toggle('active',x.id===`screen-${name}`));
  const order=['setup','review','design','verification'];
  const idx=order.indexOf(name);
  $$('.workflow-step').forEach(btn=>{
    const i=order.indexOf(btn.dataset.screen);
    btn.classList.toggle('active',i===idx); btn.classList.toggle('done',i<idx);
  });
  window.scrollTo({top:0,behavior:'smooth'});
  if(name==='review') renderReviewScreen();
  if(name==='design') renderDesignScreen();
  if(name==='verification') renderVerificationScreen();
}
$$('.workflow-step').forEach(b=>b.addEventListener('click',()=>switchScreen(b.dataset.screen)));

function renderLibraries(){
  if(!appState) return;
  const panelSelects=[$('#panelSetupSelect'),$('#panelChangeSelect')];
  panelSelects.forEach(sel=>{
    if(!sel) return;
    const val=sel.value;
    sel.innerHTML=appState.panel_library.map(p=>`<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
    sel.value=val||appState.project.panel.id;
  });
  const inv=$('#inverterSelect');
  inv.innerHTML=(appState.inverter_library||[]).map(x=>`<option>${escapeHtml(x)}</option>`).join('');
  inv.value=appState.project.inverter_name || appState.inverter_library?.[0] || '';
  renderPanelSpec();
}
function renderPanelSpec(){
  if(!appState) return;
  const id=$('#panelSetupSelect')?.value || appState.project.panel.id;
  const p=appState.panel_library.find(x=>x.id===id) || appState.panel_library[0];
  if(!p) return;
  $('#panelSpecCard').innerHTML=`
    <div><span>Công suất</span><b>${p.power_w} W</b></div>
    <div><span>Kích thước</span><b>${p.width_m.toFixed(3)} × ${p.height_m.toFixed(3)} m</b></div>
    <div><span>Hiệu suất</span><b>${(p.efficiency*100).toFixed(1)}%</b></div>
    <div><span>Giá demo</span><b>${fmtMoney(p.price_vnd)}</b></div>`;
}

function sourceUrl(){
  const f=appState?.project?.uploaded_file;
  if(f?.url && !String(f.name||'').toLowerCase().endsWith('.pdf')) return f.url;
  return '/demo/roof_blueprint.svg';
}
function renderSource(){
  const f=appState.project.uploaded_file || {};
  const name=f.name || appState.project.source_label || 'Bản vẽ mẫu SolarOpt';
  $('#sourceName').textContent=name;
  $('#reviewSourceLabel').textContent=name;
  $('#sourceBadge').textContent=f.url?'UPLOADED':'DEMO';
  $('#sourceBadge').className=`badge ${f.url?'good':'neutral'}`;
  const preview=$('#sourcePreview');
  if(f.url && String(f.name||'').toLowerCase().endsWith('.pdf')){
    preview.innerHTML='<div class="pdf-preview"><b>PDF đã tải lên</b><span>Canvas demo dùng mô hình mái đã chuẩn hóa để đảm bảo luồng Agent chạy ổn định.</span></div>';
  }else preview.innerHTML=`<img src="${sourceUrl()}" alt="Nguồn bản vẽ"/>`;
}

function renderReadiness(){
  const p=appState.project;
  const items=[
    ['Bản vẽ / ảnh mái',p.uploaded_file?.name||'Bộ dữ liệu demo','Sẵn sàng'],
    ['Tỷ lệ thực','A–B = '+($('#scaleAB')?.value||'5.40')+' m','Sẵn sàng'],
    ['Vị trí',`${Number($('#latInput')?.value||p.latitude).toFixed(3)}, ${Number($('#lngInput')?.value||p.longitude).toFixed(3)}`,'Sẵn sàng'],
    ['Tấm pin',$('#panelSetupSelect')?.selectedOptions?.[0]?.textContent||p.panel.name,'Đã chọn'],
    ['Mục tiêu',objective==='energy'?'Tối đa sản lượng':objective==='robust'?'Ưu tiên độ bền':'Cân bằng','Đã chọn'],
  ];
  $('#readinessList').innerHTML=items.map((x,i)=>`<div class="readiness-item"><div class="ri">${String(i+1).padStart(2,'0')}</div><div><b>${x[0]}</b><span>${escapeHtml(x[1])}</span></div><em>${x[2]}</em></div>`).join('');
}

$('#panelSetupSelect').addEventListener('change',()=>{renderPanelSpec();renderReadiness()});
$$('#objectiveSegments button').forEach(btn=>btn.addEventListener('click',()=>{
  objective=btn.dataset.value; $$('#objectiveSegments button').forEach(x=>x.classList.toggle('selected',x===btn)); renderReadiness();
}));
['scaleAB','latInput','lngInput','tiltInput','azimuthInput','setbackInput','budgetInput','inverterSelect'].forEach(id=>$('#'+id)?.addEventListener('input',renderReadiness));

// Upload UX
const uploadZone=$('#uploadZone'), fileInput=$('#fileInput');
['dragenter','dragover'].forEach(ev=>uploadZone.addEventListener(ev,e=>{e.preventDefault();uploadZone.classList.add('drag')}));
['dragleave','drop'].forEach(ev=>uploadZone.addEventListener(ev,e=>{e.preventDefault();uploadZone.classList.remove('drag')}));
uploadZone.addEventListener('drop',e=>{const f=e.dataTransfer.files?.[0]; if(f) uploadFile(f)});
fileInput.addEventListener('change',()=>{const f=fileInput.files?.[0];if(f) uploadFile(f)});
async function uploadFile(file){
  const fd=new FormData(); fd.append('file',file); setProjectStatus('running','Đang tải file');
  try{
    const r=await fetch('/api/upload',{method:'POST',body:fd}); if(!r.ok){const x=await r.json();throw new Error(x.detail||'Upload lỗi')}
    const data=await r.json(); appState=data.state; renderAll(); toast(`Đã nhận ${file.name}`); setProjectStatus('','Chờ phân tích');
  }catch(e){toast(e.message);setProjectStatus('','Upload lỗi')}
}
$('#useDemoBtn').addEventListener('click',async()=>{appState=await api('/api/reset',{method:'POST'});renderAll();toast('Đã nạp lại bộ dữ liệu demo')});

async function saveConfiguration(){
  const payload={
    panel_id:$('#panelSetupSelect').value,
    latitude:Number($('#latInput').value),longitude:Number($('#lngInput').value),
    roof_tilt_deg:Number($('#tiltInput').value),roof_azimuth_deg:Number($('#azimuthInput').value),
    edge_setback_m:Number($('#setbackInput').value),objective,
    budget_vnd:Math.round(Number($('#budgetInput').value)*1_000_000),inverter_name:$('#inverterSelect').value
  };
  appState=await api('/api/configure',{method:'POST',body:JSON.stringify(payload)});
  renderAll();
}
$('#analyzeBtn').addEventListener('click',async()=>{
  try{setProjectStatus('running','Đang dựng mô hình mái');await saveConfiguration();setProjectStatus('','Mô hình mái sẵn sàng');switchScreen('review');toast('Đã dựng mô hình mái và phát hiện vật cản')}catch(e){toast(e.message)}
});

// Canvas renderer ------------------------------------------------------------
function getTransform(state,W=980,H=600,pad=52){
  const pts=state.project.roof_polygon; const maxX=Math.max(...pts.map(v=>v[0])),maxY=Math.max(...pts.map(v=>v[1]));
  const minX=Math.min(...pts.map(v=>v[0])),minY=Math.min(...pts.map(v=>v[1]));
  const scale=Math.min((W-pad*2)/(maxX-minX),(H-pad*2)/(maxY-minY));
  return {W,H,pad,maxX,maxY,minX,minY,scale,pt:(x,y)=>[pad+(x-minX)*scale,pad+(maxY-y)*scale]};
}
function shadowGeometry(obs,tr){
  const hour=7+sunIndex; const proximity=Math.abs(12-hour)/5; const extra=(obs.object_height_m||.5)*(1.6+proximity*2.8); // visual proxy
  const [x1,y1]=tr.pt(obs.x-.08,obs.y+obs.height+extra); const [x2,y2]=tr.pt(obs.x+obs.width+.08,obs.y);
  return {x:Math.min(x1,x2),y:Math.min(y1,y2),w:Math.abs(x2-x1),h:Math.abs(y2-y1)};
}
function panelColor(c,heat=false){
  if(!heat) return '#3f8f62';
  const loss=c.shade_loss||0; if(loss>.12)return'#c79042'; if(loss>.05)return'#83a86d'; return'#2f8b5a';
}
function renderCanvas(sel,state,{interactive=true,showPanels=true,showShadow=false,heat=false,blueprint=false}={}){
  const el=$(sel); if(!el||!state) return; const tr=getTransform(state); canvasTransforms[sel]=tr;
  const poly=state.project.roof_polygon.map(([x,y])=>tr.pt(x,y).join(',')).join(' ');
  const bg=blueprint&&showBlueprint?`<image href="${sourceUrl()}" x="28" y="20" width="924" height="560" preserveAspectRatio="xMidYMid meet" opacity="0.22"/>`:'';
  let svg=`<svg viewBox="0 0 ${tr.W} ${tr.H}" preserveAspectRatio="xMidYMid meet" data-canvas="${sel}">
    <defs>
      <pattern id="minorGrid${sel.replace(/\W/g,'')}" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#dfe7e2" stroke-width="1"/></pattern>
      <filter id="shadowBlur${sel.replace(/\W/g,'')}"><feGaussianBlur stdDeviation="7"/></filter>
    </defs>
    <rect width="${tr.W}" height="${tr.H}" fill="#f4f7f5"/><rect width="${tr.W}" height="${tr.H}" fill="url(#minorGrid${sel.replace(/\W/g,'')})" opacity=".55"/>${bg}`;
  if(heat){
    for(let i=0;i<6;i++){
      const y=82+i*72; const opacity=.045+i*.012; svg+=`<rect class="heat-cell" x="70" y="${y}" width="800" height="70" fill="#e7a743" opacity="${opacity}"/>`;
    }
  }
  svg+=`<polygon class="entity-node" data-entity-type="roof" data-entity-id="ROOF" points="${poly}" fill="#dcece2" fill-opacity=".82" stroke="#6f9a80" stroke-width="2.2"/>`;
  // usable boundary impression
  svg+=`<polyline points="${poly} ${state.project.roof_polygon.length?tr.pt(...state.project.roof_polygon[0]).join(','):''}" fill="none" stroke="#9db7a7" stroke-width="1" stroke-dasharray="6 6" opacity=".7"/>`;
  if(showShadow){
    state.project.obstacles.forEach(o=>{
      if(!['obstacle','unknown'].includes(o.kind))return; const sh=shadowGeometry(o,tr); svg+=`<rect class="shadow-shape" x="${sh.x}" y="${sh.y}" width="${sh.w}" height="${sh.h}" rx="12" fill="#3a5146" opacity=".15" filter="url(#shadowBlur${sel.replace(/\W/g,'')})"/>`;
    });
  }
  state.project.obstacles.forEach(o=>{
    const [x,y]=tr.pt(o.x,o.y+o.height),w=o.width*tr.scale,h=o.height*tr.scale; const unk=o.kind==='unknown';
    svg+=`<g class="entity-node" data-entity-type="obstacle" data-entity-id="${o.id}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5" fill="${unk?'#f6e9c9':'#f0d8b4'}" stroke="${unk?'#b47b27':'#b98336'}" stroke-width="${unk?2:1.5}" ${unk?'stroke-dasharray="5 4"':''}/>${showLabels?`<text x="${x+w/2}" y="${y+h/2+3}" text-anchor="middle" font-size="9" font-weight="650" fill="#704c1e">${o.id}</text>`:''}</g>`;
  });
  if(showPanels){
    (state.selected_panels||[]).forEach(c=>{
      const [x,y]=tr.pt(c.x,c.y+c.height),w=c.width*tr.scale,h=c.height*tr.scale; const selected=selectedEntity?.type==='panel'&&selectedEntity.id===c.id;
      svg+=`<g class="panel-node" data-entity-type="panel" data-entity-id="${c.id}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="2" fill="${panelColor(c,heat)}" stroke="${selected?'#123d27':'#2b7049'}" stroke-width="${selected?2.5:1}"/><line x1="${x+w/2}" y1="${y+2}" x2="${x+w/2}" y2="${y+h-2}" stroke="#dcece2" opacity=".35"/><line x1="${x+2}" y1="${y+h/2}" x2="${x+w-2}" y2="${y+h/2}" stroke="#dcece2" opacity=".35"/></g>`;
    });
  }
  svg+=`<g transform="translate(900 58)"><circle r="20" fill="#fff" stroke="#cad5cf"/><path d="M0 11V-10M0-10l-5 7M0-10l5 7" stroke="#486457" stroke-width="2" fill="none"/><text x="0" y="32" text-anchor="middle" font-size="9" fill="#65766d">Bắc</text></g>`;
  svg+=`</svg>`; el.innerHTML=svg;
  if(interactive){
    el.querySelectorAll('[data-entity-type]').forEach(node=>node.addEventListener('click',e=>{
      e.stopPropagation(); selectedEntity={type:node.dataset.entityType,id:node.dataset.entityId};
      if(currentScreen==='review'){showEntityInReview(selectedEntity);renderCanvas('#reviewCanvas',appState,{interactive:true,showPanels:false,blueprint:true});}
      else {showEntityInDesign(selectedEntity);renderDesignCanvas();}
    }));
    el.querySelector('svg')?.addEventListener('click',e=>{
      if(currentScreen==='design'&&designTool==='why-not') showWhyNotAt(e,sel);
      else if(currentScreen==='review') {selectedEntity={type:'roof',id:'ROOF'};showEntityInReview(selectedEntity)};
    });
  }
}

function obstacleById(id){return appState.project.obstacles.find(x=>x.id===id)}
function showEntityInReview(entity){
  $$('.inspector-tabs button[data-inspector-tab]').forEach(x=>x.classList.toggle('active',x.dataset.inspectorTab==='properties'));
  $('#findingsPane').classList.remove('active');$('#propertiesPane').classList.add('active');
  const box=$('#entityChi tiết'); box.classList.remove('empty-state');
  if(entity.type==='roof'){
    box.innerHTML=`<div class="kicker">MẶT MÁI</div><h3>Mặt mái chính</h3>
      <div class="entity-meta"><span>Diện tích</span><b>${appState.project.roof_area_m2} m²</b></div>
      <div class="entity-meta"><span>Độ nghiêng</span><b>${appState.project.roof_tilt_deg}°</b></div>
      <div class="entity-meta"><span>Phương vị</span><b>${appState.project.roof_azimuth_deg}°</b></div>
      <div class="entity-meta"><span>Khoảng lùi mép mái</span><b>${appState.project.edge_setback_m} m</b></div>
      <div class="inspector-callout">Ranh giới này là cơ sở để sinh các vị trí tấm pin khả thi. Bạn có thể chỉnh ranh giới trong phiên bản sản phẩm đầy đủ.</div>`;
  }else{
    const o=obstacleById(entity.id); if(!o)return;
    box.innerHTML=`<div class="kicker">${o.kind==='unknown'?'VẬT THỂ CHƯA CHẮC CHẮN':'VẬT THỂ TRÊN MÁI'}</div><h3>${escapeHtml(o.label)}</h3>
      <div class="entity-meta"><span>Kích thước footprint</span><b>${o.width.toFixed(2)} × ${o.height.toFixed(2)} m</b></div>
      <div class="entity-meta"><span>Chiều cao</span><b>${o.object_height_m.toFixed(2)} m</b></div>
      <div class="entity-meta"><span>Độ chắc chắn AI</span><b>${Math.round(o.confidence*100)}%</b></div>
      <div class="entity-meta"><span>Mức ảnh hưởng</span><b>${o.impact_hint.toUpperCase()}</b></div>
      <div class="inspector-callout">${o.id==='UNK'?'Độ chắc chắn thấp không đồng nghĩa phải hỏi. SolarOpt thử các giả thuyết trước và hiện đánh giá tác động của vật thể này là thấp.':'Vật cản này được đưa vào vùng cấm và mô hình bóng trước khi tối ưu.'}</div>`;
  }
}
function showEntityInDesign(entity){
  const box=$('#whyChi tiết'); box.classList.remove('empty-state');
  $$('.inspector-tabs button[data-design-tab]').forEach(x=>x.classList.toggle('active',x.dataset.designTab==='inspect')); $('#designInspectPane').classList.add('active');$('#autopilotPane').classList.remove('active');
  if(entity.type==='panel'){
    const c=(appState.selected_panels||[]).find(x=>x.id===entity.id); if(!c)return;
    const rank=Math.max(1,Math.round((1-(c.shade_loss||0))*10));
    box.innerHTML=`<div class="kicker">VÌ SAO ĐẶT Ở ĐÂY?</div><h3>${c.id}</h3><p class="muted-small">SolarOpt giữ tấm này vì đóng góp điện năng tốt, bóng thấp và không vi phạm hình học.</p>
      <div class="entity-meta"><span>Sản lượng biên</span><b>${Math.round(c.energy_kwh)} kWh/năm</b></div>
      <div class="entity-meta"><span>Tổn thất bóng</span><b>${(c.shade_loss*100).toFixed(1)}%</b></div>
      <div class="entity-meta"><span>Hướng đặt</span><b>${c.orientation==='portrait'?'Dọc':'Ngang'}</b></div>
      <div class="entity-meta"><span>Nhóm chất lượng ánh sáng</span><b>Top ${rank*2}%</b></div>
      <div class="entity-meta"><span>Hình học / vùng cấm</span><b style="color:#17784a">ĐẠT</b></div>
      <div class="inspector-callout"><b>Bằng chứng, không phải lời giải thích tự bịa.</b><br/>Các con số phía trên lấy từ dữ liệu backend của đúng vị trí đang chọn.</div>`;
  }else if(entity.type==='obstacle'){
    const o=obstacleById(entity.id);box.innerHTML=`<div class="kicker">OBSTACLE</div><h3>${escapeHtml(o.label)}</h3><div class="entity-meta"><span>Chiều cao</span><b>${o.object_height_m.toFixed(2)} m</b></div><div class="entity-meta"><span>Độ chắc chắn</span><b>${Math.round(o.confidence*100)}%</b></div><div class="inspector-callout">Bật Dòng thời gian mặt trời để xem vùng bóng ước tính thay đổi theo thời gian.</div>`;
  }else {
    box.innerHTML=`<div class="kicker">MẶT MÁI</div><h3>Mặt mái chính</h3><div class="entity-meta"><span>Diện tích</span><b>${appState.project.roof_area_m2} m²</b></div><div class="entity-meta"><span>Độ nghiêng</span><b>${appState.project.roof_tilt_deg}°</b></div><div class="entity-meta"><span>Phương vị</span><b>${appState.project.roof_azimuth_deg}°</b></div><div class="entity-meta"><span>Diện tích mái đang dùng</span><b>${appState.design?appState.design.roof_utilization+'%':'—'}</b></div><div class="inspector-callout">Nhấp một tấm pin để xem “Why here?”, hoặc chọn công cụ “Vì sao không?” rồi bấm vào vùng trống.</div>`;
  }
}
function showWhyNotAt(e,sel){
  const svg=$(sel).querySelector('svg'); if(!svg)return; const r=svg.getBoundingClientRect(),tr=canvasTransforms[sel];
  const sx=(e.clientX-r.left)/r.width*tr.W, sy=(e.clientY-r.top)/r.height*tr.H;
  const x=(sx-tr.pad)/tr.scale+tr.minX, y=tr.maxY-(sy-tr.pad)/tr.scale;
  const tank=obstacleById('TANK'); const nearTank=tank&&x>tank.x-1&&x<tank.x+tank.width+1&&y>tank.y-1&&y<tank.y+tank.height+2;
  const edge=x<appState.project.edge_setback_m+0.6||y<appState.project.edge_setback_m+0.6||x>12.8-appState.project.edge_setback_m-0.6;
  const reasons=nearTank?['Vùng bóng/rủi ro quanh bồn nước cao','Giá trị biên thấp hơn các vị trí đang chọn']:edge?['Gần khoảng lùi mép mái','Không đủ biên hình học ổn định']:['Xung đột với lưới panel đang được chọn','Lợi ích điện năng biên không đủ để thay một vị trí tốt hơn'];
  $('#whyChi tiết').classList.remove('empty-state');
  $('#whyChi tiết').innerHTML=`<div class="kicker">VÌ SAO KHÔNG ĐẶT Ở ĐÂY?</div><h3>Vị trí thử (${x.toFixed(1)} m, ${y.toFixed(1)} m)</h3><p class="muted-small">SolarOpt tạo một candidate giả tại điểm bạn bấm và giải thích vì sao nó không nằm trong phương án hiện tại.</p>${reasons.map((r,i)=>`<div class="entity-meta"><span>Lý do ${i+1}</span><b>${r}</b></div>`).join('')}<div class="inspector-callout">Trong bản thương mại, nút “Thử vẫn đặt” sẽ fork một nhánh thiết kế và so sánh trực tiếp với phương án hiện tại.</div>`;
  $('#canvasActionHint').textContent='Đã kiểm tra điểm bạn chọn. Xem bảng Chi tiết bên phải.';
}

function renderFindings(){
  const findings=[{id:'ROOF',type:'roof',label:'Biên mái',confidence:.98,impact:'high',desc:`${appState.project.roof_area_m2} m² · ${appState.project.roof_tilt_deg}°`},...appState.project.obstacles.map(o=>({id:o.id,type:'obstacle',label:o.label,confidence:o.confidence,impact:o.impact_hint,desc:`${o.width.toFixed(2)} × ${o.height.toFixed(2)} m · cao ${o.object_height_m.toFixed(2)} m`}))];
  $('#findingList').innerHTML=findings.map(f=>`<div class="finding-item ${f.confidence<.7?'warn':''}" data-finding-id="${f.id}" data-finding-type="${f.type}"><div class="finding-top"><div><b>${escapeHtml(f.label)}</b><p>${escapeHtml(f.desc)}</p></div><span class="impact-chip ${f.impact}">${f.impact==='high'?'Ảnh hưởng cao':f.impact==='medium'?'Trung bình':'Thấp'}</span></div><div class="confidence-bar"><i style="width:${Math.round(f.confidence*100)}%"></i></div><p>Độ chắc chắn: ${Math.round(f.confidence*100)}%</p></div>`).join('');
  $$('.finding-item').forEach(el=>el.addEventListener('click',()=>{selectedEntity={type:el.dataset.findingType,id:el.dataset.findingId};showEntityInReview(selectedEntity);renderCanvas('#reviewCanvas',appState,{interactive:true,showPanels:false,blueprint:true})}));
}
function renderLowImpact(){
  const u=appState.low_impact_uncertainty;
  $('#lowImpactDecision').innerHTML=`<div class="decision-stat"><span>Độ chắc chắn</span><b>${Math.round(u.confidence*100)}%</b></div><div class="decision-stat"><span>Chênh sản lượng</span><b>${u.energy_delta_pct}%</b></div><div class="decision-stat good"><span>Quyết định</span><b>Tự tiếp tục</b></div>`;
}
function renderAttention(){
  const box=$('#attentionPanel'),a=appState.attention||[];
  if(!a.length){box.className='card attention-panel idle';box.innerHTML='<div class="kicker">CẦN KỸ SƯ XÁC NHẬN</div><h3>0 việc cần kỹ sư</h3><p>Hiện không có bất định nào đủ lớn để chặn Tự vận hành.</p>';return;}
  const x=a[0];box.className='card attention-panel warn';box.innerHTML=`<div class="kicker">CẦN KỸ SƯ XÁC NHẬN</div><h3>${escapeHtml(x.title)}</h3><p>${escapeHtml(x.detail)}</p><div class="attention-choices">${x.choices.map(c=>`<button>${escapeHtml(c)}</button>`).join('')}</div>`;
}
function renderReviewScreen(){
  if(!appState)return; renderCanvas('#reviewCanvas',appState,{interactive:true,showPanels:false,blueprint:true});renderFindings();renderLowImpact();renderAttention();$('#reviewScale').textContent=`A–B ${Number($('#scaleAB').value||5.4).toFixed(2).replace('.',',')} m`;
}

// inspector tabs
$$('[data-inspector-tab]').forEach(btn=>btn.addEventListener('click',()=>{
  $$('[data-inspector-tab]').forEach(x=>x.classList.toggle('active',x===btn));$('#findingsPane').classList.toggle('active',btn.dataset.inspectorTab==='findings');$('#propertiesPane').classList.toggle('active',btn.dataset.inspectorTab==='properties');
}));
$$('.tool[data-tool]').forEach(btn=>btn.addEventListener('click',()=>{$$('.tool[data-tool]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');toast(`${btn.querySelector('b').textContent}: công cụ minh họa đã được chọn`)}));
$('#toggleBlueprint').addEventListener('click',()=>{showBlueprint=!showBlueprint;$('#toggleBlueprint').classList.toggle('active',showBlueprint);renderReviewScreen()});
$('#toggleLabels').addEventListener('click',()=>{showLabels=!showLabels;$('#toggleLabels').classList.toggle('active',showLabels);renderReviewScreen()});
$('#probeBtn').addEventListener('click',async()=>{appState=await api('/api/uncertainty',{method:'POST',body:JSON.stringify({high_impact:true})});renderAll();renderReviewScreen();toast('Đã tạo một bất định có ảnh hưởng lớn để demo')});

// Tự vận hành ------------------------------------------------------------
function eventClass(e){if(e.type==='LỖI')return'fail';if(e.type==='REPAIR')return'repair';if(e.type==='FINAL')return'final';return''}
function missionHTML(events,current=-1){
  const steps=[['UNDERSTAND','Hiểu công trình'],['CANDIDATES','Sinh vị trí khả thi'],['SOLAR','Mô phỏng nắng & bóng'],['DESIGN','Tạo phương án'],['VERIFY','Kiểm tra thiết kế'],['KIỂM THỬ','Thử độ bền'],['REPAIR','Tự sửa nếu cần'],['FINAL','Bàn giao']];
  return steps.map(([type,label],i)=>{const idx=events.findIndex(e=>e.type===type),done=idx>=0&&idx<current,run=idx===current,ev=events[idx];return `<div class="mission-step ${done?'done':''} ${run?'running':''}"><div class="num">${done?'✓':String(i+1).padStart(2,'0')}</div><div><strong>${label}</strong><small>${ev?.detail||'Đang chờ'}</small></div><div class="ms-status">${done?'DONE':run?'RUN':'—'}</div></div>`}).join('');
}
async function playEvents(events){
  lastEvents=events||[];$('#eventTimeline').innerHTML='';$('#missionSteps').innerHTML=missionHTML(lastEvents,-1);setProjectStatus('running','Tự vận hành đang chạy');
  for(let i=0;i<lastEvents.length;i++){
    const e=lastEvents[i];$('#missionSteps').innerHTML=missionHTML(lastEvents,i);$('#eventTimeline').insertAdjacentHTML('beforeend',`<div class="event-item ${eventClass(e)}"><time>${e.time}</time><i class="event-dot"></i><div class="event-copy"><b>${escapeHtml(e.title)}</b><p>${escapeHtml(e.detail)}</p></div></div>`);
    $('#eventTimeline').scrollTop=$('#eventTimeline').scrollHeight;
    if(e.type==='LỖI'||e.type==='REPAIR'){const n=$('#repairNotice');n.classList.remove('hidden');n.innerHTML=`<b>${e.type==='LỖI'?'Phát hiện vấn đề':'Auto Repair'}</b> · ${escapeHtml(e.detail)}`;}
    await new Promise(r=>setTimeout(r,250));
  }
  $('#missionSteps').innerHTML=missionHTML(lastEvents,lastEvents.length+1); setProjectStatus('ready','Thiết kế đã kiểm chứng'); setTimeout(()=>$('#repairNotice').classList.add('hidden'),2500);
}
$('#toDesignBtn').addEventListener('click',async()=>{
  switchScreen('design'); $('#autopilotPane').classList.add('active');$('#designInspectPane').classList.remove('active');$$('[data-design-tab]').forEach(x=>x.classList.toggle('active',x.dataset.designTab==='autopilot'));
  try{appState=await api('/api/autopilot',{method:'POST'});renderAll();renderDesignScreen();await playEvents(appState.events);toast('Tự vận hành đã hoàn tất vòng thiết kế → kiểm chứng → tự sửa')}catch(e){toast(e.message);setProjectStatus('','Có lỗi')}
});
$('#replayBtn').addEventListener('click',()=>playEvents(lastEvents));
$$('[data-design-tab]').forEach(btn=>btn.addEventListener('click',()=>{$$('[data-design-tab]').forEach(x=>x.classList.toggle('active',x===btn));$('#designInspectPane').classList.toggle('active',btn.dataset.designTab==='inspect');$('#autopilotPane').classList.toggle('active',btn.dataset.designTab==='autopilot')}));

function renderDesignMetrics(){
  const d=appState.design;if(!d){['metricPanels','metricEnergy','metricCost','metricUtil','metricStress'].forEach(id=>$('#'+id).textContent='—');return;}
  $('#metricPanels').textContent=`${d.panel_count} tấm`;$('#metricEnergy').textContent=fmtEnergy(d.energy_kwh);$('#metricCost').textContent=fmtMoney(d.cost_vnd);$('#metricUtil').textContent=fmtPct(d.roof_utilization);$('#metricStress').textContent=d.stress_total?`${d.stress_passed}/${d.stress_total}`:'—';$('#designVersionLabel').textContent=`v${d.version} · ${d.label||'Thiết kế hiện tại'}`;
}
function renderDesignOptionsSelect(){
  const sel=$('#designOptionSelect'),opts=appState.design_options||[]; if(!opts.length){sel.innerHTML='<option>Chạy Tự vận hành trước</option>';return;}
  sel.innerHTML=opts.map(o=>`<option value="${o.id}">${escapeHtml(o.label)}</option>`).join(''); sel.value='OPT-2';
}
$('#designOptionSelect').addEventListener('change',async()=>{
  if(!$('#designOptionSelect').value.startsWith('OPT'))return;
  try{appState=await api('/api/design/select',{method:'POST',body:JSON.stringify({option_id:$('#designOptionSelect').value})});renderAll();renderDesignScreen();toast('Đã chuyển phương án để xem xét')}catch(e){toast(e.message)}
});
function renderDesignCanvas(){
  renderCanvas('#designCanvas',appState,{interactive:true,showPanels:true,showShadow:$('#shadowToggle').checked,heat:$('#heatToggle').checked,blueprint:false});
}
function renderDesignScreen(){if(!appState)return;renderDesignMetrics();renderDesignOptionsSelect();if(!selectedEntity&&appState.selected_panels?.length) selectedEntity={type:'panel',id:appState.selected_panels[0].id};renderDesignCanvas();if(selectedEntity) showEntityInDesign(selectedEntity);$('#missionSteps').innerHTML=missionHTML(appState.events||[],(appState.events||[]).length+1);renderEventTimelineStatic();renderWhatIfResult();}
function renderEventTimelineStatic(){
  $('#eventTimeline').innerHTML=(appState.events||[]).map(e=>`<div class="event-item ${eventClass(e)}"><time>${e.time}</time><i class="event-dot"></i><div class="event-copy"><b>${escapeHtml(e.title)}</b><p>${escapeHtml(e.detail)}</p></div></div>`).join('');
}
$$('[data-design-tool]').forEach(btn=>btn.addEventListener('click',()=>{designTool=btn.dataset.designTool;$$('[data-design-tool]').forEach(x=>x.classList.toggle('active',x===btn));if(designTool==='why-not')$('#canvasActionHint').textContent='Nhấp vào một vùng trống trên mái để hỏi: “Vì sao không đặt panel ở đây?”';else if(designTool==='shade'){$('#shadowToggle').checked=true;renderDesignCanvas()}else if(designTool==='heat'){$('#heatToggle').checked=true;renderDesignCanvas()}else $('#canvasActionHint').textContent='Chọn một tấm pin để xem “Vì sao đặt ở đây?”.'}));
$('#shadowToggle').addEventListener('change',renderDesignCanvas);$('#heatToggle').addEventListener('change',renderDesignCanvas);
$('#sunTimeSlider').addEventListener('input',e=>{sunIndex=Number(e.target.value);const h=7+sunIndex;$('#sunTimeLabel').textContent=`Tháng 12 · ${String(h).padStart(2,'0')}:00`;renderDesignCanvas()});

// What-if drawer
function openDrawer(){$('#whatIfDrawer').classList.add('open');$('#drawerBackdrop').classList.add('open');$('#whatIfDrawer').setAttribute('aria-hidden','false')}
function closeDrawer(){ $('#whatIfDrawer').classList.remove('open');$('#drawerBackdrop').classList.remove('open');$('#whatIfDrawer').setAttribute('aria-hidden','true') }
$('#whatIfBtn').addEventListener('click',openDrawer);$('#openHardwareTool').addEventListener('click',openDrawer);$('#closeWhatIf').addEventListener('click',closeDrawer);$('#drawerBackdrop').addEventListener('click',closeDrawer);
$('#tankHeight').addEventListener('input',e=>$('#tankHeightValue').textContent=`${e.target.value} m`);
$('#tankBtn').addEventListener('click',async()=>{try{setProjectStatus('running','Đang xử lý thay đổi');appState=await api('/api/change/tank-height',{method:'POST',body:JSON.stringify({height_m:Number($('#tankHeight').value)})});renderAll();renderDesignScreen();await playEvents(appState.events);renderWhatIfResult();toast('Đã truy dấu tác động và cập nhật thiết kế')}catch(e){toast(e.message)}});
$('#panelBtn').addEventListener('click',async()=>{try{setProjectStatus('running','Đang đổi linh kiện');appState=await api('/api/change/panel',{method:'POST',body:JSON.stringify({panel_id:$('#panelChangeSelect').value})});renderAll();renderDesignScreen();await playEvents(appState.events);renderWhatIfResult();toast('Đã thay linh kiện và đồng bộ các phần phụ thuộc')}catch(e){toast(e.message)}});
function renderWhatIfResult(){
  const box=$('#whatIfResult'),ch=appState.last_change||{},rp=appState.last_repair||{};
  if(!ch.type){box.className='drawer-result empty-state';box.innerHTML='<b>Chưa có thay đổi</b><p>Kết quả tự sửa và số phần bị ảnh hưởng sẽ xuất hiện ở đây.</p>';return;}
  box.className=`drawer-result ${rp.changed_count?'fail':'success'}`;
  box.innerHTML=`<h3>${rp.changed_count?'Đã tự phục hồi thiết kế':'Thay đổi đã được hấp thụ'}</h3><p>${escapeHtml(ch.label)}: <b>${escapeHtml(ch.before)}</b> → <b>${escapeHtml(ch.after)}</b></p><div class="drawer-result-grid"><span>Nút phụ thuộc đã cập nhật</span><b>${Object.values(appState.dependency_status||{}).filter(x=>x==='VERIFIED').length}</b><span>Vị trí được giữ nguyên</span><b>${rp.kept??'—'}</b><span>Thao tác thay đổi</span><b>${rp.changed_count??0}</b><span>Kiểm thử tình huống xấu cuối</span><b>${appState.design?.stress_total?appState.design.stress_passed+'/'+appState.design.stress_total:'—'}</b></div>`;
}

// Verification ----------------------------------------------------------
function renderOptionCards(){
  const opts=appState.design_options||[]; const current=appState.design;
  $('#designOptionCards').innerHTML=opts.map(o=>`<div class="design-option-card ${current&&Math.abs(current.energy_kwh-o.energy_kwh)<.1&&current.panel_count===o.panel_count?'selected':''}" data-option-id="${o.id}"><div class="option-title">${escapeHtml(o.label)}</div>${o.id==='OPT-2'?'<span class="option-badge">Khuyến nghị</span>':''}<div class="option-metrics"><div><span>Tấm</span><b>${o.panel_count}</b></div><div><span>Điện</span><b>${fmtEnergy(o.energy_kwh)}</b></div><div><span>Chi phí</span><b>${fmtMoney(o.cost_vnd)}</b></div><div><span>Stress</span><b>${o.stress_passed}/${o.stress_total}</b></div></div></div>`).join('') || '<div class="empty-state"><b>Chưa có phương án</b><p>Hãy chạy Tự vận hành trước.</p></div>';
  $$('.design-option-card').forEach(c=>c.addEventListener('click',async()=>{try{appState=await api('/api/design/select',{method:'POST',body:JSON.stringify({option_id:c.dataset.optionId})});renderAll();renderVerificationScreen();toast('Đã chọn phương án này làm phương án đang xem xét')}catch(e){toast(e.message)}}));
}
function renderStress(){
  const rows=appState.stress_results||[];$('#stressTable').innerHTML=rows.map((r,i)=>`<div class="stress-row" data-stress-index="${i}"><span class="sr-index">${String(i+1).padStart(2,'0')}</span><b>${escapeHtml(r.name)}</b><span class="stress-status ${r.status.toLowerCase()}">${r.status}</span></div>`).join('') || '<div class="empty-state"><b>Chưa có stress-test</b><p>Chạy Tự vận hành trước.</p></div>';
  $$('.stress-row').forEach(row=>row.addEventListener('click',()=>showStressDetail(Number(row.dataset.stressIndex))));
}
function showStressDetail(i){
  const r=appState.stress_results[i];if(!r)return; const vs=r.violations||[];
  $('#stressDetail').classList.remove('empty-state');$('#stressDetail').innerHTML=`<b>${escapeHtml(r.name)} · ${r.status}</b><p>${r.status==='ĐẠT'?'Thiết kế vẫn thỏa các kiểm tra trong tình huống này.':'Thiết kế phát sinh vi phạm và cần vòng tự sửa.'}</p>${vs.length?`<div class="violation-list">${vs.map(v=>`<span class="violation-chip">${escapeHtml(v.code)} · ${escapeHtml(v.panel||'')}</span>`).join('')}</div>`:'<p>Không có vi phạm được ghi nhận.</p>'}`;
}
function renderDependencies(){
  const labels={candidates:'Vị trí ứng viên',shadow:'Bóng',layout:'Bố trí',energy:'Sản lượng',electrical:'Điện',cost:'Chi phí',roi:'Hoàn vốn',bom:'Vật tư',report:'Báo cáo'};
  const keys=Object.keys(labels);$('#dependencyGraph').innerHTML=keys.map((k,i)=>`<div class="dep-node ${appState.dependency_status?.[k]||''}" data-dep="${k}"><div><b>${labels[k]}</b><small>${appState.dependency_status?.[k]||'IDLE'}</small></div></div>${i<keys.length-1?'<span class="dep-arrow">→</span>':''}`).join('');
  $$('.dep-node').forEach(n=>n.addEventListener('click',()=>{const k=n.dataset.dep,st=appState.dependency_status?.[k]||'IDLE';$('#dependencyDetail').innerHTML=`<b>${labels[k]}</b><p>Trạng thái: ${st}. ${dependencyExplanation(k)}</p>`}));
}
function dependencyExplanation(k){const m={candidates:'Chạy lại khi hình học mái hoặc kích thước tấm pin thay đổi.',shadow:'Chạy lại khi chiều cao/vị trí vật cản hoặc bố trí thay đổi.',layout:'Là đầu ra bố trí được sửa với mục tiêu thay đổi ít nhất.',energy:'Phụ thuộc vào panel, bố trí và bóng.',electrical:'Phụ thuộc công suất và cấu hình tấm pin.',cost:'Phụ thuộc số lượng/giá linh kiện.',roi:'Phụ thuộc sản lượng và chi phí.',bom:'Danh sách vật tư phải đồng bộ với layout.',report:'Báo cáo cuối chỉ sinh khi các nút trước đã đồng bộ.'};return m[k]||''}
function renderVersions(){
  const v=appState.versions||[];$('#versionTable').innerHTML='<div class="version-row head"><span>Phiên bản</span><span>Lý do</span><span>Số tấm</span><span>Sản lượng</span><span>Stress</span></div>'+v.map(x=>`<div class="version-row"><span class="version-tag">v${x.version}</span><span>${escapeHtml(x.label||'Thiết kế')}</span><b>${x.count}</b><b>${fmtEnergy(x.energy_kwh)}</b><b>${x.stress}</b></div>`).join('');
}
function renderVerificationScreen(){
  if(!appState)return; const d=appState.design; const badge=$('#readyBadge');badge.textContent=d?.verified?`Sẵn sàng xem xét · ${d.stress_passed}/${d.stress_total} đạt`:'Cần chạy/kiểm tra thêm';badge.classList.toggle('ready',!!d?.verified);renderOptionCards();renderStress();renderDependencies();renderVersions();$('#impactEnergy').textContent=d?fmtEnergy(d.energy_kwh):'—';$('#impactRedesign').textContent=(appState.last_repair?.changed_count??0)>0?`${appState.last_repair.changed_count} thao tác tự sửa`:'Tự động';$('#impactHuman').textContent=(appState.attention||[]).length?'1':'0';
}
$('#toVerificationBtn').addEventListener('click',()=>switchScreen('verification'));

// Help / reset -----------------------------------------------------------
$('#helpBtn').addEventListener('click',()=>{$('#helpModal').classList.add('open');$('#helpModal').setAttribute('aria-hidden','false')});$('#closeHelp').addEventListener('click',()=>{$('#helpModal').classList.remove('open');$('#helpModal').setAttribute('aria-hidden','true')});$('#helpModal').addEventListener('click',e=>{if(e.target===$('#helpModal'))$('#closeHelp').click()});
$('#resetBtn').addEventListener('click',async()=>{appState=await api('/api/reset',{method:'POST'});objective='balanced';selectedEntity=null;designTool='select';renderAll();setProjectStatus('','Chưa chạy');switchScreen('setup');toast('Đã đặt lại dự án demo')});

function renderAll(){
  if(!appState)return; renderLibraries();renderSource();renderReadiness();renderLowImpact();renderAttention();renderDesignMetrics();renderDesignOptionsSelect();renderDependencies();renderVersions();renderWhatIfResult();
  $('#tiltInput').value=appState.project.roof_tilt_deg;$('#azimuthInput').value=appState.project.roof_azimuth_deg;$('#latInput').value=appState.project.latitude;$('#lngInput').value=appState.project.longitude;$('#setbackInput').value=appState.project.edge_setback_m;$('#budgetInput').value=Math.round((appState.project.budget_vnd||120_000_000)/1_000_000);$('#panelSetupSelect').value=appState.project.panel.id;$('#panelChangeSelect').value=appState.project.panel.id;$('#inverterSelect').value=appState.project.inverter_name;objective=appState.project.objective||objective;$$('#objectiveSegments button').forEach(x=>x.classList.toggle('selected',x.dataset.value===objective));renderPanelSpec();renderReadiness();
}

(async function init(){
  try{appState=await api('/api/state');renderAll();$('#missionSteps').innerHTML=missionHTML([], -1);renderReviewScreen();renderDesignScreen();renderVerificationScreen();}
  catch(e){toast('Không kết nối được backend: '+e.message)}
})();
