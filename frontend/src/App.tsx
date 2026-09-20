import { useState, useEffect, useRef } from 'react'
import { api } from './services/api'

// ─── Design tokens ────────────────────────────────────────────────────────────
const G = '#1a5c35' // primary green CTA

// ─── Types ────────────────────────────────────────────────────────────────────
type AppStep = 1 | 2 | 3 | 4 | 5
type ObsShape = 'circle' | 'square' | 'rect' | 'triangle'
interface CustomObs {
  id: string; cx: number; cy: number
  shape: ObsShape; w: number; h: number; label: string
}

interface ObsDef {
  id: string; label: string
  cx: number; cy: number; w: number; h: number
  conf: number; impact: 'Cao' | 'Trung bình' | 'Thấp'
  kind: string; size: string; height: string
  tags: string[]
}

// ─── Constants ────────────────────────────────────────────────────────────────

const OBS: ObsDef[] = [
  { id: 'bien_mai', label: 'Biên mái (đa giác)', cx: 325, cy: 240, w: 0, h: 0, conf: 98, impact: 'Cao', kind: 'Đường viền mái', size: '10 × 8 m (80 m²)', height: 'Lan can 1.1 m', tags: [] },
  // top-left: water tank — blueprint: Ø 1.5 m
  { id: 'bon_nuoc', label: 'Bồn nước', cx: 155, cy: 126, w: 90, h: 90, conf: 96, impact: 'Cao', kind: 'Bồn nước inox', size: 'Ø 1.5 m (1.77 m²)', height: '1.20 m', tags: ['Bóng','Layout','Sản lượng'] },
  // top-center: vent pipe — blueprint: Ø 0.15 m (two pipes, shown as one here)
  { id: 'ong_thong_gio', label: 'Ống thông gió', cx: 242, cy: 103, w: 36, h: 36, conf: 93, impact: 'Trung bình', kind: 'Ống thoát', size: 'Ø 0.15 m (0.02 m²)', height: '0.4 m', tags: ['Bóng'] },
  // top-right: AC unit (~68% x, 22% y)
  { id: 'dan_nong', label: 'Dàn nóng', cx: 413, cy: 135, w: 96, h: 72, conf: 91, impact: 'Cao', kind: 'Máy điều hòa', size: '0.90 × 0.70 m', height: '0.8 m', tags: ['Bóng','Layout'] },
  // bottom-left: unknown object (~24% x, 65% y)
  { id: 'vat_the_a', label: 'Vật thể A ?', cx: 198, cy: 297, w: 100, h: 72, conf: 52, impact: 'Thấp', kind: 'Chưa xác định', size: '~0.8 × 0.5 m', height: '?', tags: [] },
]

// Panel positions computed to avoid all obstacle exclusion zones:
// bon_nuoc:     cx=155,cy=126,w=90,h=90  → exclude x∈[90,220],  y∈[61,191]
// ong_thong_gio:cx=242,cy=103,w=36,h=36  → exclude x∈[204,280], y∈[65,141]
// dan_nong:     cx=413,cy=135,w=96,h=72  → exclude x∈[345,481], y∈[79,191]
// vat_the_a:    cx=198,cy=297,w=100,h=72 → exclude x∈[128,268], y∈[241,353]
const PANELS_17 = [
  // Right side — 2 columns just right of dan_nong (x≥490, y∈[80,212])
  {x:490,y:80}, {x:543,y:80},
  {x:490,y:115},{x:543,y:115},
  {x:490,y:150},{x:543,y:150},
  {x:490,y:185},{x:543,y:185},
  // Center-right row — below all top obstacles (y=220, x≥270)
  {x:270,y:220},{x:323,y:220},{x:376,y:220},{x:429,y:220},{x:482,y:220},{x:535,y:220},
  // Third row — avoids vat_the_a on lower-left (x≥270)
  {x:270,y:255},{x:323,y:255},{x:376,y:255},
]

const PANELS_18 = [...PANELS_17, {x:429,y:255}]
const PANELS_15 = PANELS_17.slice(0, 15)

const DESIGN_OPTIONS = [
  // area = panel_count × 2.583m²/panel × 1.16 layout factor (spacing + margins), capped well under 80m² roof
  { id:'max',   icon:'📊', label:'Tối đa sản lượng',  panels:18, mwh:15.15, cost:75.6, payback:4.8, stress:'5/8', area:53.9, panelList: PANELS_18, desc:'Tập trung tối đa vào sản lượng điện, phù hợp khi ưu tiên hiệu quả năng lượng.' },
  { id:'bal',   icon:'⚖️', label:'Cân bằng',          panels:17, mwh:14.32, cost:71.4, payback:5.2, stress:'8/8', area:50.9, panelList: PANELS_17, rec:true, desc:'Cân bằng giữa sản lượng, chi phí và độ bền. Phù hợp cho đa số công trình.' },
  { id:'dur',   icon:'🛡️', label:'Ưu tiên độ bền',   panels:15, mwh:12.60, cost:63.0, payback:5.2, stress:'8/8', area:44.9, panelList: PANELS_15, desc:'Tập trung vào độ an toàn và tuổi thọ, phù hợp khu vực thời tiết khắc nghiệt.' },
]

const STRESS = [
  { id:'01', name:'Base geometry',    r:[true,true,true]  },
  { id:'02', name:'Winter low sun',   r:[false,true,true] },
  { id:'03', name:'Tank +20 cm',      r:[true,true,true]  },
  { id:'04', name:'Tank +30 cm',      r:[false,true,true] },
  { id:'05', name:'Morning low sun',  r:[true,true,true]  },
  { id:'06', name:'Afternoon low sun',r:[true,true,true]  },
  { id:'07', name:'Panel tolerance',  r:[true,true,true]  },
  { id:'08', name:'Field variance',   r:[false,true,true] },
]

// ─── Small helpers ────────────────────────────────────────────────────────────

function Pill({ children, tone = 'green' }: { children: React.ReactNode; tone?: 'green'|'amber'|'red'|'sky'|'gray' }) {
  const cls: Record<string,string> = {
    green:'bg-green-100 text-green-800 border-green-200',
    amber:'bg-amber-100 text-amber-800 border-amber-200',
    red  :'bg-red-100 text-red-700 border-red-200',
    sky  :'bg-sky-100 text-sky-700 border-sky-200',
    gray :'bg-gray-100 text-gray-600 border-gray-200',
  }
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border font-mono ${cls[tone]}`}>{children}</span>
}

function Dot({ tone }: { tone: 'green'|'amber'|'red' }) {
  const c = { green:'bg-green-500', amber:'bg-amber-500', red:'bg-red-500' }[tone]
  return <span className={`inline-block w-2 h-2 rounded-full ${c}`} />
}

function Check({ pass }: { pass: boolean }) {
  return pass
    ? <span className="inline-flex items-center gap-1 text-green-700 text-[11px] font-semibold"><span className="w-4 h-4 bg-green-100 border border-green-300 rounded-full flex items-center justify-center text-[9px]">✓</span>Đạt</span>
    : <span className="inline-flex items-center gap-1 text-red-600 text-[11px] font-semibold"><span className="w-4 h-4 bg-red-100 border border-red-300 rounded-full flex items-center justify-center text-[9px]">✕</span>Không đạt</span>
}

function SectionNum({ n, label, sub }: { n: number; label: string; sub?: string }) {
  return (
    <div className="flex gap-3 items-start mb-4">
      <div className="w-7 h-7 rounded-full bg-gray-800 text-white text-sm font-bold flex items-center justify-center shrink-0">{n}</div>
      <div>
        <div className="font-semibold text-gray-800">{label}</div>
        {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function InputField({ label, value, unit, sub }: { label: string; value: string|number; unit?: string; sub?: string }) {
  return (
    <div>
      <label className="text-xs text-gray-500 block mb-1">{label}</label>
      <div className="flex items-center bg-white border border-gray-200 rounded-lg overflow-hidden focus-within:border-green-500 focus-within:ring-1 focus-within:ring-green-200 transition-all">
        <input defaultValue={value} className="flex-1 px-3 py-2 text-sm text-gray-800 bg-transparent focus:outline-none font-mono" />
        {unit && <span className="text-xs text-gray-400 pr-3 shrink-0">{unit}</span>}
      </div>
      {sub && <p className="text-[10px] text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white border border-gray-200 rounded-xl shadow-sm ${className}`}>{children}</div>
}

// ─── Blueprint SVG (top-down flat roof simulation matching drone photo) ────────

function BlueprintSVG({
  selectedObs, onSelectObs,
  obsPos, onObsMove,
}: {
  selectedObs?: string
  onSelectObs?: (id: string) => void
  obsPos?: Record<string, {cx: number, cy: number}>
  onObsMove?: (id: string, cx: number, cy: number) => void
}) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [dragState, setDragState] = useState<{id: string, startPx: number, startPy: number, origCx: number, origCy: number} | null>(null)

  const toSVGCoords = (e: React.PointerEvent) => {
    const svg = svgRef.current
    if (!svg) return {x: 0, y: 0}
    const pt = svg.createSVGPoint()
    pt.x = e.clientX; pt.y = e.clientY
    const p = pt.matrixTransform(svg.getScreenCTM()!.inverse())
    return {x: p.x, y: p.y}
  }

  const handleObsDown = (e: React.PointerEvent, obs: typeof OBS[0]) => {
    if (!onObsMove) return
    e.stopPropagation()
    ;(e.currentTarget as SVGElement).setPointerCapture(e.pointerId)
    const {x, y} = toSVGCoords(e)
    const cur = obsPos?.[obs.id] ?? {cx: obs.cx, cy: obs.cy}
    setDragState({id: obs.id, startPx: x, startPy: y, origCx: cur.cx, origCy: cur.cy})
  }

  const handleMove = (e: React.PointerEvent) => {
    if (!dragState || !onObsMove) return
    const {x, y} = toSVGCoords(e)
    onObsMove(dragState.id, dragState.origCx + x - dragState.startPx, dragState.origCy + y - dragState.startPy)
  }

  // Roof area matching the drone photo (flat corrugated roof)
  const RX = 60, RY = 32, RW = 530, RH = 416

  // Generate corrugated metal ridges (vertical lines, light green-gray)
  const ridgeCount = 35
  const ridges = Array.from({length: ridgeCount}, (_, i) => RX + (i / ridgeCount) * RW)

  const labelStyle = (isSel: boolean, isDrag: boolean) =>
    isDrag ? '#0ea5e9' : isSel ? '#f59e0b' : '#1a5c35'

  return (
    <svg ref={svgRef} viewBox={`0 0 ${VW} ${VH}`} className="w-full h-full"
      style={{ fontFamily: 'Inter, sans-serif', cursor: dragState ? 'grabbing' : 'default' }}
      onPointerMove={handleMove}
      onPointerUp={() => setDragState(null)}
      onPointerLeave={() => setDragState(null)}
    >
      <defs>
        {/* Corrugated metal fill */}
        <linearGradient id="roofGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#b8c9b8" />
          <stop offset="50%" stopColor="#c8d8c8" />
          <stop offset="100%" stopColor="#b8c9b8" />
        </linearGradient>
        {/* Stainless steel sheen for water tank */}
        <radialGradient id="tankSheen" cx="38%" cy="35%" r="60%">
          <stop offset="0%" stopColor="#e8ede8" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#c8d0c0" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#a8b0a0" stopOpacity="0.3" />
        </radialGradient>
        <pattern id="corrugated" width="15" height="416" patternUnits="userSpaceOnUse" x={RX} y={RY}>
          <rect width="15" height="416" fill="#bfcfbf" />
          <rect x="3" width="9" height="416" fill="#cad8ca" />
          <rect x="5" width="5" height="416" fill="#d2dfd2" />
        </pattern>
      </defs>

      {/* Surroundings (concrete / ground outside roof) */}
      <rect width={VW} height={VH} fill="#e8ebe8" />

      {/* Concrete border / parapet */}
      <rect x={RX-10} y={RY-10} width={RW+20} height={RH+20} fill="#c8cfc8" stroke="#a8b0a8" strokeWidth="1" />

      {/* Roof surface — corrugated metal */}
      <rect x={RX} y={RY} width={RW} height={RH} fill="url(#corrugated)" />

      {/* Ridge highlight lines */}
      {ridges.map((x, i) => (
        <line key={i} x1={x} y1={RY} x2={x} y2={RY+RH}
          stroke={i % 3 === 0 ? '#a8baa8' : '#b8c8b8'} strokeWidth={i % 3 === 0 ? '1.5' : '0.8'} opacity="0.6" />
      ))}

      {/* Shadow / highlight on parapet edges */}
      <rect x={RX-10} y={RY-10} width={RW+20} height={10} fill="#b0b8b0" opacity="0.6" />
      <rect x={RX-10} y={RY-10} width={10} height={RH+20} fill="#b0b8b0" opacity="0.4" />

      {/* Safety zone dashed green */}
      <rect x={RX+30} y={RY+30} width={RW-60} height={RH-60}
        fill="none" stroke="#16a34a" strokeWidth="1.5" strokeDasharray="10 5" opacity="0.7" />

      {/* Compass */}
      <g transform={`translate(${RX+28}, ${RY+RH-28})`}>
        <circle cx={0} cy={0} r={16} fill="white" fillOpacity="0.85" stroke="#94a3b8" strokeWidth="1" />
        <polygon points="0,-11 3,4 0,0 -3,4" fill="#1a5c35" />
        <polygon points="0,11 3,-4 0,0 -3,-4" fill="#9ca3af" />
        <text y={-15} textAnchor="middle" fontSize="9" fontWeight="700" fill="#1a5c35">N</text>
      </g>

      {/* Dimension labels */}
      <line x1={RX} y1={RY-18} x2={RX+RW} y2={RY-18} stroke="#475569" strokeWidth="1"/>
      <line x1={RX} y1={RY-22} x2={RX} y2={RY-14} stroke="#475569" strokeWidth="1"/>
      <line x1={RX+RW} y1={RY-22} x2={RX+RW} y2={RY-14} stroke="#475569" strokeWidth="1"/>
      <text x={RX+RW/2} y={RY-20} textAnchor="middle" fontSize="10" fill="#334155" fontWeight="700">10 m</text>
      <line x1={RX+RW+18} y1={RY} x2={RX+RW+18} y2={RY+RH} stroke="#475569" strokeWidth="1"/>
      <line x1={RX+RW+14} y1={RY} x2={RX+RW+22} y2={RY} stroke="#475569" strokeWidth="1"/>
      <line x1={RX+RW+14} y1={RY+RH} x2={RX+RW+22} y2={RY+RH} stroke="#475569" strokeWidth="1"/>
      <text x={RX+RW+30} y={RY+RH/2+4} textAnchor="middle" fontSize="10" fill="#334155" fontWeight="700"
        transform={`rotate(90,${RX+RW+30},${RY+RH/2})`}>8 m</text>

      {/* ── Draggable obstacles ── */}
      {OBS.filter(o => o.w > 0).map(obs => {
        const cur = obsPos?.[obs.id] ?? {cx: obs.cx, cy: obs.cy}
        const {cx, cy} = cur
        const isSel = selectedObs === obs.id
        const isDrag = dragState?.id === obs.id
        const accentColor = isDrag ? '#0ea5e9' : isSel ? '#f59e0b' : '#1a5c35'
        const hw = obs.w / 2, hh = obs.h / 2
        const isWaterTank = obs.id === 'bon_nuoc'
        const isVent = obs.id === 'ong_thong_gio'

        if (isVent) {
          const r = hw
          return (
            <g key={obs.id} style={{ cursor: 'grab' }} onPointerDown={e => handleObsDown(e, obs)} onClick={() => onSelectObs?.(obs.id)}>
              {/* Shadow */}
              <ellipse cx={cx+3} cy={cy+3} rx={r+2} ry={r+2} fill="rgba(0,0,0,0.18)" />
              {/* Pipe body — dark gray cylinder from top */}
              <circle cx={cx} cy={cy} r={r+2} fill="#5a6a5a" />
              <circle cx={cx} cy={cy} r={r} fill="#7a8a7a" />
              <circle cx={cx} cy={cy} r={r*0.6} fill="#6a7a6a" />
              <circle cx={cx} cy={cy} r={r*0.3} fill="#4a5a4a" />
              {/* Selection ring */}
              {(isSel || isDrag) && <circle cx={cx} cy={cy} r={r+6} fill="none" stroke={accentColor} strokeWidth="2" strokeDasharray="5 3" />}
              {/* Label */}
              <text x={cx} y={cy - r - 10} textAnchor="middle" fontSize="9" fill={accentColor} fontWeight="700"
                style={{ filter: 'drop-shadow(0 1px 2px white)' }}>
                {obs.label}
              </text>
            </g>
          )
        }

        if (isWaterTank) {
          const r = hw
          return (
            <g key={obs.id} style={{ cursor: 'grab' }} onPointerDown={e => handleObsDown(e, obs)} onClick={() => onSelectObs?.(obs.id)}>
              {/* Shadow */}
              <ellipse cx={cx+5} cy={cy+5} rx={r+4} ry={r+4} fill="rgba(0,0,0,0.22)" />
              {/* Tank base (legs/frame) */}
              <rect x={cx-r-4} y={cy-r-4} width={(r+4)*2} height={(r+4)*2} fill="#a0a890" rx="2" opacity="0.5" />
              {/* Tank top — stainless steel sheen */}
              <circle cx={cx} cy={cy} r={r} fill="#c8d0c0" />
              <circle cx={cx} cy={cy} r={r} fill="url(#tankSheen)" />
              <circle cx={cx} cy={cy} r={r*0.85} fill="none" stroke="#b0b8a8" strokeWidth="2" />
              <circle cx={cx} cy={cy} r={r*0.6} fill="none" stroke="#b0b8a8" strokeWidth="1.5" />
              <circle cx={cx} cy={cy} r={r*0.25} fill="#a0a898" />
              {/* Crosshair */}
              <line x1={cx-r*0.85} y1={cy} x2={cx+r*0.85} y2={cy} stroke="#8a9288" strokeWidth="1.2" />
              <line x1={cx} y1={cy-r*0.85} x2={cx} y2={cy+r*0.85} stroke="#8a9288" strokeWidth="1.2" />
              {/* Selection ring */}
              {(isSel || isDrag) && <circle cx={cx} cy={cy} r={r+8} fill="none" stroke={accentColor} strokeWidth="2.5" strokeDasharray="8 4" />}
              {/* Label */}
              <text x={cx} y={cy - r - 14} textAnchor="middle" fontSize="10" fill={accentColor} fontWeight="700"
                style={{ filter: 'drop-shadow(0 1px 3px white)' }}>
                {obs.label}
              </text>
              <text x={cx} y={cy - r - 4} textAnchor="middle" fontSize="8" fill={accentColor} opacity="0.8">(Ø 1.5 m)</text>
            </g>
          )
        }

        // Equipment block — flat-roof AC or unknown box
        const isUnknown = obs.id === 'vat_the_a'
        return (
          <g key={obs.id} style={{ cursor: 'grab' }} onPointerDown={e => handleObsDown(e, obs)} onClick={() => onSelectObs?.(obs.id)}>
            {/* Shadow */}
            <rect x={cx-hw+4} y={cy-hh+4} width={obs.w} height={obs.h} fill="rgba(0,0,0,0.22)" rx="2" />
            {/* Body */}
            <rect x={cx-hw} y={cy-hh} width={obs.w} height={obs.h}
              fill={isUnknown ? '#c8c8b8' : '#d8ddd0'} stroke={isUnknown ? '#a8a898' : '#a0aa98'} strokeWidth="1.5" rx="2" />
            {/* Internal detail lines */}
            <line x1={cx-hw+4} y1={cy-hh+4} x2={cx+hw-4} y2={cy+hh-4} stroke={isUnknown ? '#b0b0a0' : '#aab0a0'} strokeWidth="1" opacity="0.5" />
            <line x1={cx+hw-4} y1={cy-hh+4} x2={cx-hw+4} y2={cy+hh-4} stroke={isUnknown ? '#b0b0a0' : '#aab0a0'} strokeWidth="1" opacity="0.5" />
            <rect x={cx-hw+4} y={cy-hh+4} width={obs.w-8} height={obs.h-8} fill="none" stroke={isUnknown ? '#b0b0a0' : '#aab0a0'} strokeWidth="0.8" opacity="0.4" />
            {/* Selection */}
            {(isSel || isDrag) && <rect x={cx-hw-5} y={cy-hh-5} width={obs.w+10} height={obs.h+10}
              fill="none" stroke={accentColor} strokeWidth="2" strokeDasharray="6 3" rx="4" />}
            {/* Label */}
            <text x={cx} y={cy - hh - 8} textAnchor="middle" fontSize="10" fill={accentColor} fontWeight="700"
              style={{ filter: 'drop-shadow(0 1px 3px white)' }}>
              {obs.label}
            </text>
          </g>
        )
      })}

      {/* Instruction hint */}
      <rect x={RX} y={RY+RH-22} width={RW} height={22} fill="rgba(0,0,0,0.25)" />
      <text x={RX + RW/2} y={RY+RH-8} textAnchor="middle" fontSize="9" fill="white" opacity="0.9">
        Kéo để di chuyển vật cản · Nhấp để chọn và xem thông tin
      </text>
    </svg>
  )
}

// ─── SVG Aerial Roof ──────────────────────────────────────────────────────────

const VW = 650, VH = 480

const ROOF_POLY = '90,52 642,52 642,385 90,385'
const ROOF_VERTS = [{x:90,y:52},{x:642,y:52},{x:642,y:385},{x:90,y:385}]

// Pre-defined tree circles
const TREES = [
  {cx:22,cy:22,r:28,d:'#2a5a2a'},{cx:50,cy:12,r:20,d:'#1e4a1e'},
  {cx:12,cy:55,r:18,d:'#2e622e'},{cx:620,cy:18,r:26,d:'#2a5a2a'},
  {cx:638,cy:50,r:18,d:'#1e4a1e'},{cx:18,cy:420,r:24,d:'#2a5a2a'},
  {cx:45,cy:455,r:20,d:'#1e4a1e'},{cx:615,cy:410,r:22,d:'#2a5a2a'},
  {cx:638,cy:445,r:18,d:'#1e4a1e'},{cx:540,cy:22,r:24,d:'#2a5a2a'},
  {cx:565,cy:12,r:16,d:'#1e4a1e'},{cx:25,cy:200,r:18,d:'#2e622e'},
  {cx:22,cy:310,r:20,d:'#2a5a2a'},
]

function AerialSVG({
  mode,
  selectedObs, onSelectObs,
  selectedPanel, onSelectPanel,
  panelList = PANELS_17,
  uploadedImage,
  obsPos,
  onObsMove,
  tintMode,
  timeH = 10,
  activeTool = 'select',
  compassAngle = 360,
  onCompassChange,
  addedObs = [],
  onAddRequest,
}: {
  mode: 'detect' | 'design'
  selectedObs?: string; onSelectObs?: (id: string) => void
  selectedPanel?: number | null; onSelectPanel?: (i: number) => void
  panelList?: typeof PANELS_17
  uploadedImage?: string | null
  obsPos?: Record<string, {cx: number, cy: number}>
  onObsMove?: (id: string, cx: number, cy: number) => void
  tintMode?: 'shadow' | 'radiation'
  timeH?: number
  activeTool?: string
  compassAngle?: number
  onCompassChange?: (angle: number) => void
  addedObs?: CustomObs[]
  onAddRequest?: (svgX: number, svgY: number, screenX: number, screenY: number) => void
}) {
  const PW = 45, PH = 27
  const svgRef = useRef<SVGSVGElement>(null)
  const [dragState, setDragState] = useState<{id: string, startPx: number, startPy: number, origCx: number, origCy: number} | null>(null)
  // Measure tool state
  const [measurePts, setMeasurePts] = useState<Array<{x: number, y: number}>>([])
  // Pan state
  const [panOffset, setPanOffset] = useState({x: 0, y: 0})
  const [panDrag, setPanDrag] = useState<{startX: number, startY: number, origX: number, origY: number} | null>(null)
  // Mouse position for add-mode crosshair
  const [mousePos, setMousePos] = useState<{x: number, y: number} | null>(null)
  // Compass drag
  const [compassDragging, setCompassDragging] = useState(false)
  // Compass SVG center
  const COMPASS_CX = 113, COMPASS_CY = 368

  const toSVGCoords = (e: React.PointerEvent): {x: number, y: number} => {
    const svg = svgRef.current
    if (!svg) return {x: 0, y: 0}
    const pt = svg.createSVGPoint()
    pt.x = e.clientX; pt.y = e.clientY
    const svgPt = pt.matrixTransform(svg.getScreenCTM()!.inverse())
    return {x: svgPt.x, y: svgPt.y}
  }

  const handleObsPointerDown = (e: React.PointerEvent, obs: typeof OBS[0]) => {
    if (activeTool !== 'select' || !onObsMove) return
    e.stopPropagation()
    ;(e.currentTarget as SVGElement).setPointerCapture(e.pointerId)
    const {x, y} = toSVGCoords(e)
    const cur = obsPos?.[obs.id] ?? {cx: obs.cx, cy: obs.cy}
    setDragState({id: obs.id, startPx: x, startPy: y, origCx: cur.cx, origCy: cur.cy})
  }

  const handleCompassPointerDown = (e: React.PointerEvent) => {
    e.stopPropagation()
    // Capture on the SVG root so onPointerMove on the SVG fires during drag
    svgRef.current?.setPointerCapture(e.pointerId)
    setCompassDragging(true)
  }

  const handleSVGPointerDown = (e: React.PointerEvent) => {
    const {x, y} = toSVGCoords(e)
    if (activeTool === 'pan') {
      ;(e.currentTarget as SVGElement).setPointerCapture(e.pointerId)
      setPanDrag({startX: e.clientX, startY: e.clientY, origX: panOffset.x, origY: panOffset.y})
    } else if (activeTool === 'measure') {
      if (measurePts.length >= 2) {
        setMeasurePts([{x, y}])
      } else {
        setMeasurePts(prev => [...prev, {x, y}])
      }
    } else if (activeTool === 'add') {
      if (x >= 90 && x <= 642 && y >= 52 && y <= 385) {
        onAddRequest?.(x, y, e.clientX, e.clientY)
      }
    }
  }

  const handleSVGPointerMove = (e: React.PointerEvent) => {
    const {x, y} = toSVGCoords(e)
    if (activeTool === 'add' || activeTool === 'measure') {
      setMousePos({x, y})
    } else {
      setMousePos(null)
    }
    if (compassDragging && onCompassChange) {
      const dx = x - COMPASS_CX, dy = y - COMPASS_CY
      // atan2 gives angle from east; rotate so 0 = north (up = negative y)
      let angle = Math.atan2(dx, -dy) * (180 / Math.PI)
      if (angle < 0) angle += 360
      onCompassChange(Math.round(angle))
      return
    }
    if (panDrag && activeTool === 'pan') {
      const dx = (e.clientX - panDrag.startX)
      const dy = (e.clientY - panDrag.startY)
      // Scale screen pixels to SVG coords
      const svg = svgRef.current
      if (!svg) return
      const rect = svg.getBoundingClientRect()
      const scaleX = VW / rect.width, scaleY = VH / rect.height
      setPanOffset({x: panDrag.origX - dx * scaleX, y: panDrag.origY - dy * scaleY})
      return
    }
    if (!dragState || !onObsMove) return
    const dx = x - dragState.startPx, dy = y - dragState.startPy
    onObsMove(dragState.id, dragState.origCx + dx, dragState.origCy + dy)
  }

  const handleSVGPointerUp = () => {
    setDragState(null)
    setPanDrag(null)
    setCompassDragging(false)
  }

  // Measurement distance in meters (scale: 552 SVG px = 10 m)
  const PX_PER_M = 552 / 10
  const measureDist = measurePts.length === 2
    ? Math.sqrt(Math.pow(measurePts[1].x - measurePts[0].x, 2) + Math.pow(measurePts[1].y - measurePts[0].y, 2)) / PX_PER_M
    : null

  // Compass direction label
  const compassLabel = (a: number) => {
    if (a < 22.5 || a >= 337.5) return 'Bắc'
    if (a < 67.5) return 'Đông Bắc'
    if (a < 112.5) return 'Đông'
    if (a < 157.5) return 'Đông Nam'
    if (a < 202.5) return 'Nam'
    if (a < 247.5) return 'Tây Nam'
    if (a < 292.5) return 'Tây'
    return 'Tây Bắc'
  }

  const cursorStyle = activeTool === 'pan' ? (panDrag ? 'grabbing' : 'grab')
    : activeTool === 'measure' ? 'crosshair'
    : dragState ? 'grabbing' : 'default'

  const viewBox = `${panOffset.x} ${panOffset.y} ${VW} ${VH}`

  return (
    <svg ref={svgRef} viewBox={viewBox} className="w-full h-full"
      style={{ fontFamily: 'Inter, sans-serif', cursor: cursorStyle }}
      onPointerMove={handleSVGPointerMove}
      onPointerUp={handleSVGPointerUp}
      onPointerLeave={handleSVGPointerUp}
      onPointerDown={handleSVGPointerDown}
    >
      <defs>
        {/* Corrugated metal roof for aerial view */}
        <pattern id="aerial-corrugated" width="15" height="333" patternUnits="userSpaceOnUse" x="90" y="52">
          <rect width="15" height="333" fill="#bfcfbf" />
          <rect x="3" width="9" height="333" fill="#cad8ca" />
          <rect x="5" width="5" height="333" fill="#d2dfd2" />
        </pattern>
        {/* Panel glow */}
        <filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feComposite in="SourceGraphic" in2="blur" operator="over"/></filter>
      </defs>

      {/* Yard background */}
      <rect width={VW} height={VH} fill="#3c6640" />

      {/* Uploaded image as background */}
      {uploadedImage && (
        <image href={uploadedImage} x="0" y="0" width={VW} height={VH} preserveAspectRatio="xMidYMid slice" opacity="0.85" />
      )}

      {/* Trees */}
      {TREES.map((t, i) => (
        <g key={i}>
          <circle cx={t.cx} cy={t.cy} r={t.r} fill={t.d} opacity="0.9" />
          <circle cx={t.cx - 3} cy={t.cy - 4} r={t.r * 0.6} fill="#346a34" opacity="0.5" />
        </g>
      ))}

      {/* Concrete parapet border */}
      <rect x="80" y="42" width="572" height="353" fill="#c8cfc8" stroke="#a8b0a8" strokeWidth="1.5" />

      {/* Flat corrugated metal roof */}
      <rect x="90" y="52" width="552" height="333" fill="url(#aerial-corrugated)" />

      {/* Corrugated ridge lines */}
      {Array.from({length: 40}, (_, i) => 90 + (i / 40) * 552).map((x, i) => (
        <line key={i} x1={x} y1={52} x2={x} y2={385}
          stroke={i % 3 === 0 ? '#a8baa8' : '#b8c8b8'} strokeWidth={i % 3 === 0 ? '1.5' : '0.8'} opacity="0.55" />
      ))}

      {/* Parapet shadow edges */}
      <rect x="80" y="42" width="572" height="10" fill="#b0b8b0" opacity="0.5" />
      <rect x="80" y="42" width="10" height="353" fill="#b0b8b0" opacity="0.35" />

      {/* ── DETECT MODE ─── */}
      {mode === 'detect' && (
        <>
          {/* Roof polygon overlay */}
          <polygon
            points={ROOF_POLY}
            fill="rgba(52,211,153,0.12)"
            stroke="#10b981"
            strokeWidth="2"
            strokeDasharray="10 5"
          />
          {/* Vertex handles */}
          {ROOF_VERTS.map((v, i) => (
            <circle key={i} cx={v.x} cy={v.y} r={6} fill="white" stroke="#10b981" strokeWidth="2" style={{ cursor:'move' }} />
          ))}

          {/* Obstacle detection overlays */}
          {OBS.filter(o => o.w > 0).map(obs => {
            const isSel = selectedObs === obs.id
            const isDragging = dragState?.id === obs.id
            const cur = obsPos?.[obs.id] ?? {cx: obs.cx, cy: obs.cy}
            const cx = cur.cx, cy = cur.cy
            const hw = obs.w / 2, hh = obs.h / 2
            const chipColor = obs.conf < 60 ? '#f59e0b' : '#1a5c35'
            const ringColor = isDragging ? '#38bdf8' : isSel ? '#f59e0b' : obs.conf < 60 ? '#f59e0b' : '#f59e0b'
            const fillAlpha = isDragging ? 'rgba(56,189,248,0.18)' : isSel ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.08)'
            const sw = isDragging ? 3 : isSel ? 2.5 : 2
            const canDrag = !!onObsMove
            const isCircle = obs.id === 'bon_nuoc'
            const isSmallCircle = obs.id === 'ong_thong_gio'
            const labelY = isCircle || isSmallCircle ? cy - hw - 10 : cy - hh - 10

            return (
              <g key={obs.id}
                style={{ cursor: canDrag ? (isDragging ? 'grabbing' : 'grab') : 'pointer' }}
                onClick={() => !isDragging && onSelectObs?.(obs.id)}
                onPointerDown={(e) => handleObsPointerDown(e, obs)}
              >
                {isCircle ? (
                  // Water tank — circular detection ring + stainless top
                  <>
                    {/* Outer dashed detection ring */}
                    <circle cx={cx} cy={cy} r={hw + 8} fill="none"
                      stroke={ringColor} strokeWidth={sw} strokeDasharray="8 4" />
                    {/* Tank body (stainless from above) */}
                    <circle cx={cx+3} cy={cy+3} r={hw} fill="rgba(0,0,0,0.2)" />
                    <circle cx={cx} cy={cy} r={hw} fill="rgba(200,210,200,0.85)" stroke={ringColor} strokeWidth="1.5" />
                    <circle cx={cx} cy={cy} r={hw*0.8} fill="none" stroke="rgba(180,190,180,0.7)" strokeWidth="1.5" />
                    <circle cx={cx} cy={cy} r={hw*0.5} fill="rgba(160,175,165,0.7)" />
                    <line x1={cx-hw*0.8} y1={cy} x2={cx+hw*0.8} y2={cy} stroke="rgba(150,165,155,0.6)" strokeWidth="1.2" />
                    <line x1={cx} y1={cy-hw*0.8} x2={cx} y2={cy+hw*0.8} stroke="rgba(150,165,155,0.6)" strokeWidth="1.2" />
                    {canDrag && <text x={cx} y={cy+3} textAnchor="middle" dominantBaseline="middle" fontSize="9" fill={ringColor} opacity="0.6" pointerEvents="none">⠿</text>}
                  </>
                ) : isSmallCircle ? (
                  // Vent pipe — small circle detection
                  <>
                    <circle cx={cx} cy={cy} r={hw + 6} fill="none"
                      stroke={ringColor} strokeWidth={sw} strokeDasharray="6 3" />
                    <circle cx={cx+2} cy={cy+2} r={hw} fill="rgba(0,0,0,0.2)" />
                    <circle cx={cx} cy={cy} r={hw} fill="rgba(80,90,80,0.85)" stroke={ringColor} strokeWidth="1.5" />
                    <circle cx={cx} cy={cy} r={hw*0.55} fill="rgba(50,60,50,0.8)" />
                    <circle cx={cx} cy={cy} r={hw*0.25} fill="rgba(30,40,30,0.9)" />
                    {canDrag && <text x={cx} y={cy+3} textAnchor="middle" dominantBaseline="middle" fontSize="8" fill={ringColor} opacity="0.6" pointerEvents="none">⠿</text>}
                  </>
                ) : (
                  // Equipment — rectangular detection box
                  <>
                    <rect x={cx-hw} y={cy-hh} width={obs.w} height={obs.h}
                      fill={fillAlpha} stroke={ringColor} strokeWidth={sw}
                      strokeDasharray="7 3" rx="3" />
                    {/* Inner shape detail */}
                    <rect x={cx-hw+5} y={cy-hh+5} width={obs.w-10} height={obs.h-10}
                      fill="rgba(200,210,200,0.4)" stroke="rgba(200,210,200,0.3)" strokeWidth="1" rx="2" />
                    {canDrag && <text x={cx} y={cy+3} textAnchor="middle" dominantBaseline="middle" fontSize="9" fill={ringColor} opacity="0.6" pointerEvents="none">⠿</text>}
                  </>
                )}
                {/* Label chip */}
                <rect x={cx - obs.label.length * 3.2} y={labelY - 14}
                  width={obs.label.length * 6.4 + 10} height={17} rx="3"
                  fill={chipColor} pointerEvents="none"
                />
                <text x={cx} y={labelY - 2}
                  textAnchor="middle" fill="white" fontSize="10" fontWeight="600" pointerEvents="none">
                  {obs.label}
                </text>
              </g>
            )
          })}
        </>
      )}

      {/* ── DESIGN MODE ─── */}
      {mode === 'design' && (
        <>
          {/* Subtle roof boundary */}
          <polygon points={ROOF_POLY} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" strokeDasharray="6 4" />

          {/* Obstacle no-go zones (translucent) */}
          {OBS.filter(o => o.w > 0).map(obs => {
            const cur = obsPos?.[obs.id] ?? {cx: obs.cx, cy: obs.cy}
            const {cx, cy} = cur
            const hw = obs.w / 2 + 20, hh = obs.h / 2 + 20
            const isRound = obs.id === 'bon_nuoc' || obs.id === 'ong_thong_gio'
            return (
              <g key={obs.id} pointerEvents="none">
                {isRound
                  ? <circle cx={cx} cy={cy} r={hw} fill="rgba(239,68,68,0.12)" stroke="rgba(239,68,68,0.45)" strokeWidth="1.5" strokeDasharray="5 3" />
                  : <rect x={cx-hw} y={cy-hh} width={hw*2} height={hh*2} fill="rgba(239,68,68,0.12)" stroke="rgba(239,68,68,0.45)" strokeWidth="1.5" strokeDasharray="5 3" rx="3" />
                }
                <text x={cx} y={cy + (isRound ? hw + 10 : hh + 10)} textAnchor="middle" fontSize="8" fill="rgba(239,100,100,0.9)" fontWeight="600">{obs.label}</text>
              </g>
            )
          })}

          {/* Solar panels */}
          {panelList.map((p, i) => {
            const isSel = selectedPanel === i
            // Shadow: panels near obstacles or edges lose more sun at certain hours
            const shadowFactor = tintMode === 'shadow'
              ? Math.max(0, Math.min(1, (p.x < 200 && timeH < 11 ? 0.7 : p.x > 450 && timeH > 14 ? 0.65 : p.y < 110 ? 0.55 : 0.08)))
              : 0
            // Radiation: brighter in center, dimmer near edges
            const cx2 = p.x + PW / 2, cy2 = p.y + PH / 2
            const radNorm = tintMode === 'radiation'
              ? Math.max(0, 1 - (Math.abs(cx2 - 366) / 300 + Math.abs(cy2 - 218) / 200) * 0.5)
              : 0
            const baseFill = isSel ? '#38bdf8'
              : tintMode === 'shadow' ? (shadowFactor > 0.4 ? `rgba(180,60,30,${0.5 + shadowFactor * 0.4})` : shadowFactor > 0.1 ? `rgba(220,130,30,${0.5 + shadowFactor})` : '#1e3a5f')
              : tintMode === 'radiation' ? `hsl(${40 + radNorm * 80},${70 + radNorm * 20}%,${20 + radNorm * 30}%)`
              : '#1e3a5f'
            const baseStroke = isSel ? '#7dd3fc' : tintMode === 'shadow' ? (shadowFactor > 0.4 ? '#ef4444' : shadowFactor > 0.1 ? '#f59e0b' : '#2563eb') : tintMode === 'radiation' ? `hsl(${40+radNorm*80},80%,50%)` : '#2563eb'
            return (
              <g key={i} style={{ cursor: 'pointer' }} onClick={() => onSelectPanel?.(i)}>
                <rect x={p.x} y={p.y} width={PW} height={PH}
                  fill={baseFill}
                  stroke={baseStroke}
                  strokeWidth={isSel ? 2 : 0.8}
                  rx="1.5"
                  filter={isSel ? 'url(#glow)' : undefined}
                />
                {tintMode === 'shadow' && shadowFactor > 0.15 && (
                  <rect x={p.x} y={p.y} width={PW} height={PH * shadowFactor} fill="rgba(0,0,0,0.35)" rx="1.5" />
                )}
                {/* Panel cell lines */}
                <line x1={p.x + PW/3} y1={p.y} x2={p.x + PW/3} y2={p.y + PH} stroke={isSel ? '#bae6fd' : '#3b82f6'} strokeWidth="0.5" opacity="0.4" />
                <line x1={p.x + PW*2/3} y1={p.y} x2={p.x + PW*2/3} y2={p.y + PH} stroke={isSel ? '#bae6fd' : '#3b82f6'} strokeWidth="0.5" opacity="0.4" />
                <line x1={p.x} y1={p.y + PH/2} x2={p.x + PW} y2={p.y + PH/2} stroke={isSel ? '#bae6fd' : '#3b82f6'} strokeWidth="0.5" opacity="0.4" />
                <text x={p.x + PW/2} y={p.y + PH/2 + 3} textAnchor="middle" fontSize="7" fill={isSel ? 'white' : '#93c5fd'} opacity="0.8">#{i + 1}</text>
              </g>
            )
          })}
        </>
      )}

      {/* Interactive compass — always on top, drag to rotate roof heading */}
      <g transform={`translate(${COMPASS_CX},${COMPASS_CY})`}
        style={{ cursor: compassDragging ? 'grabbing' : 'grab' }}
        onPointerDown={handleCompassPointerDown}
      >
        {/* Drop shadow */}
        <circle cx="1" cy="2" r="24" fill="rgba(0,0,0,0.18)" />
        <circle cx="0" cy="0" r="24" fill="white" fillOpacity="0.96" stroke={compassDragging ? '#1a5c35' : '#c8d0c8'} strokeWidth={compassDragging ? 2 : 1} />
        {/* Cardinal tick marks (rotate with world, not needle) */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map(deg => {
          const isMajor = deg % 90 === 0
          const rad = deg * Math.PI / 180
          const r1 = isMajor ? 16 : 19, r2 = 22
          return <line key={deg} x1={Math.sin(rad)*r1} y1={-Math.cos(rad)*r1} x2={Math.sin(rad)*r2} y2={-Math.cos(rad)*r2}
            stroke={isMajor ? '#6b7280' : '#d1d5db'} strokeWidth={isMajor ? 1.5 : 0.8} />
        })}
        {/* Needle group rotates by compassAngle */}
        <g transform={`rotate(${compassAngle})`}>
          {/* North (green) */}
          <polygon points="0,-15 3.5,2 0,0 -3.5,2" fill="#1a5c35" />
          {/* South (gray) */}
          <polygon points="0,15 3.5,-2 0,0 -3.5,-2" fill="#9ca3af" />
          {/* Center dot */}
          <circle cx="0" cy="0" r="2.5" fill="white" stroke="#6b7280" strokeWidth="1" />
        </g>
        {/* Fixed N label (doesn't rotate with needle) */}
        <text x="0" y="-26" textAnchor="middle" fontSize="8" fontWeight="800" fill="#1a5c35">N</text>
        {/* Angle readout below */}
        <text y="33" textAnchor="middle" fontSize="9" fontWeight="700" fill="#1a5c35">{compassAngle}°</text>
        <text y="42" textAnchor="middle" fontSize="7" fill="#6b7280">{compassLabel(compassAngle)}</text>
        {/* Drag hint ring */}
        {!compassDragging && (
          <circle cx="0" cy="0" r="24" fill="none" stroke="#1a5c35" strokeWidth="0" strokeOpacity="0" />
        )}
      </g>

      {/* Measure tool overlay */}
      {activeTool === 'measure' && measurePts.length > 0 && (
        <g>
          {measurePts.map((pt, i) => (
            <g key={i}>
              <circle cx={pt.x} cy={pt.y} r={5} fill="white" stroke="#f59e0b" strokeWidth="2" />
              <circle cx={pt.x} cy={pt.y} r={2} fill="#f59e0b" />
            </g>
          ))}
          {measurePts.length === 2 && (
            <>
              <line x1={measurePts[0].x} y1={measurePts[0].y} x2={measurePts[1].x} y2={measurePts[1].y}
                stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="6 3" />
              {/* Tick ends */}
              <line x1={measurePts[0].x - 5} y1={measurePts[0].y} x2={measurePts[0].x + 5} y2={measurePts[0].y}
                stroke="#f59e0b" strokeWidth="1.5" transform={`rotate(${Math.atan2(measurePts[1].y - measurePts[0].y, measurePts[1].x - measurePts[0].x) * 180/Math.PI + 90},${measurePts[0].x},${measurePts[0].y})`} />
              {/* Distance label */}
              {measureDist !== null && (
                <g transform={`translate(${(measurePts[0].x + measurePts[1].x)/2},${(measurePts[0].y + measurePts[1].y)/2 - 10})`}>
                  <rect x="-28" y="-11" width="56" height="16" rx="4" fill="rgba(30,30,30,0.85)" />
                  <text textAnchor="middle" y="2" fontSize="10" fontWeight="700" fill="#fbbf24">{measureDist.toFixed(2)} m</text>
                </g>
              )}
            </>
          )}
        </g>
      )}

      {/* Added custom obstacles */}
      {addedObs.map((o) => {
        const hw = o.w / 2, hh = o.h / 2
        return (
          <g key={o.id}>
            {o.shape === 'circle' && (
              <>
                <circle cx={o.cx} cy={o.cy} r={hw + 6} fill="none" stroke="#a855f7" strokeWidth="1.5" strokeDasharray="5 3" />
                <circle cx={o.cx} cy={o.cy} r={hw} fill="rgba(168,85,247,0.22)" stroke="#a855f7" strokeWidth="2" />
              </>
            )}
            {o.shape === 'square' && (
              <rect x={o.cx - hw} y={o.cy - hw} width={o.w} height={o.w}
                fill="rgba(168,85,247,0.22)" stroke="#a855f7" strokeWidth="2" strokeDasharray="5 3" rx="3" />
            )}
            {o.shape === 'rect' && (
              <rect x={o.cx - hw} y={o.cy - hh} width={o.w} height={o.h}
                fill="rgba(168,85,247,0.22)" stroke="#a855f7" strokeWidth="2" strokeDasharray="5 3" rx="3" />
            )}
            {o.shape === 'triangle' && (
              <polygon
                points={`${o.cx},${o.cy - hh} ${o.cx - hw},${o.cy + hh} ${o.cx + hw},${o.cy + hh}`}
                fill="rgba(168,85,247,0.22)" stroke="#a855f7" strokeWidth="2" strokeDasharray="5 3" />
            )}
            <text x={o.cx} y={o.cy - hh - 10} textAnchor="middle" fontSize="9" fill="#a855f7" fontWeight="700">{o.label}</text>
          </g>
        )
      })}

      {/* Live cursor for add/measure tools */}
      {mousePos && activeTool === 'add' && (
        <g pointerEvents="none">
          <line x1={mousePos.x - 10} y1={mousePos.y} x2={mousePos.x + 10} y2={mousePos.y} stroke="#a855f7" strokeWidth="1.5" />
          <line x1={mousePos.x} y1={mousePos.y - 10} x2={mousePos.x} y2={mousePos.y + 10} stroke="#a855f7" strokeWidth="1.5" />
          <circle cx={mousePos.x} cy={mousePos.y} r={8} fill="none" stroke="#a855f7" strokeWidth="1" strokeDasharray="3 2" opacity="0.7" />
        </g>
      )}
      {mousePos && activeTool === 'measure' && measurePts.length < 2 && (
        <g pointerEvents="none">
          <line x1={mousePos.x - 8} y1={mousePos.y} x2={mousePos.x + 8} y2={mousePos.y} stroke="#f59e0b" strokeWidth="1.5" />
          <line x1={mousePos.x} y1={mousePos.y - 8} x2={mousePos.x} y2={mousePos.y + 8} stroke="#f59e0b" strokeWidth="1.5" />
          {measurePts.length === 1 && (
            <line x1={measurePts[0].x} y1={measurePts[0].y} x2={mousePos.x} y2={mousePos.y}
              stroke="#f59e0b" strokeWidth="1" strokeDasharray="4 3" opacity="0.6" />
          )}
        </g>
      )}
    </svg>
  )
}

// ─── Step 1: Thiết lập ────────────────────────────────────────────────────────

function Step1({ onNext, onImageUpload, tabImages }: {
  onNext: () => void
  onImageUpload: (tabIdx: number, img: string, name: string) => void
  tabImages: Array<{image: string | null, name: string | null}>
}) {
  const [activeTab, setActiveTab] = useState(0)
  const [goal, setGoal] = useState<'max'|'bal'|'dur'>('bal')
  const [overrideDims, setOverrideDims] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const curImage = tabImages[activeTab].image
  const curName = tabImages[activeTab].name

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => onImageUpload(activeTab, ev.target?.result as string, file.name)
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => onImageUpload(activeTab, ev.target?.result as string, file.name)
    reader.readAsDataURL(file)
  }

  const readiness = [
    { label:'Hình học mái nhà', sub:'Từ bản vẽ/ảnh', tone:'green', val:'Cao' },
    { label:'Tỷ lệ & kích thước', sub:'Đoạn tham chiếu', tone:'green', val:'Cao' },
    { label:'Vùng vật cản', sub:'Ống khói, bồn nước, ...', tone:'amber', val:'Trung bình' },
    { label:'Chiều cao vật cản', sub:'', tone:'amber', val:'Trung bình' },
    { label:'Bóng che xung quanh', sub:'Cây xanh, công trình lân cận', tone:'red', val:'Cần bổ sung' },
  ] as const

  return (
    <div className="animate-fade-up">
      <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-[1fr_320px] gap-6 items-start">
        {/* Main */}
        <div className="space-y-5">
          {/* Section 1 */}
          <Card className="p-5">
            <SectionNum n={1} label="Nguồn dữ liệu đầu vào" sub="Tải lên các dữ liệu hiện có. Bạn có thể cung cấp một hoặc nhiều loại dữ liệu, SolarOpt sẽ tự động kết hợp để tạo Digital Roof của mái nhà." />
            <div className="flex gap-1 mb-4">
              {['Bản vẽ kỹ thuật','Ảnh từ trên xuống','Ảnh hiện trường'].map((t,i) => (
                <button key={t} onClick={() => setActiveTab(i)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${activeTab===i ? 'bg-green-50 border-green-300 text-green-800' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
                  {i===0?'📐 ':i===1?'🛰 ':'📷 '}{t}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-[260px_1fr] gap-4">
              {/* Upload zone */}
              <div
                className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center gap-3 transition-colors cursor-pointer ${curImage ? 'border-green-400 bg-green-50' : 'border-gray-200 bg-gray-50 hover:border-green-300 hover:bg-green-50/30'}`}
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
              >
                <input ref={fileInputRef} type="file" accept="image/*,.svg,.pdf" className="hidden" onChange={handleFileChange} />
                {curImage ? (
                  <>
                    <img src={curImage} alt="preview" className="w-full h-28 object-cover rounded-lg" />
                    <div className="text-xs font-medium text-green-700 truncate max-w-full">{curName}</div>
                    <div className="text-[10px] text-green-600">✓ Đã tải lên · click để thay thế</div>
                  </>
                ) : (
                  <>
                    <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
                      <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
                      </svg>
                    </div>
                    <div className="text-center">
                      <div className="text-sm font-medium text-gray-700">Kéo thả hoặc chọn file</div>
                      <div className="text-xs text-gray-400 mt-0.5">PNG, JPG, SVG (tối đa 50 MB)</div>
                    </div>
                    <div className="text-xs font-medium text-gray-600 border border-gray-300 rounded-lg px-4 py-1.5 bg-white hover:bg-gray-50">Chọn file ảnh mái nhà</div>
                  </>
                )}
              </div>
              {/* Uploaded files */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs text-gray-500">Xem trước dữ liệu đã tải lên</div>
                  {curImage && <button className="text-xs text-green-700 hover:underline" onClick={() => onImageUpload(activeTab, '', '')}>Xóa</button>}
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {curImage ? (
                    <div className="border border-green-300 rounded-lg overflow-hidden bg-green-50 col-span-3">
                      <div className="h-20 overflow-hidden">
                        <img src={curImage} alt="roof" className="w-full h-full object-cover" />
                      </div>
                      <div className="p-1.5">
                        <div className="text-[10px] font-medium text-gray-700 truncate">{curName}</div>
                        <div className="flex items-center justify-between mt-0.5">
                          <span className="text-[9px] text-gray-400">Đã tải lên</span>
                          <span className="text-green-600 text-xs">✓</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="col-span-3 flex items-center justify-center h-16 text-xs text-gray-400">
                      Chưa có file nào được tải lên
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Section 2 */}
          <Card className="p-5">
            <SectionNum n={2} label="Hiệu chỉnh kích thước & vị trí" sub="Điều chỉnh các thông số để mô hình phù hợp với thực tế. Các giá trị này giúp xác định quy mô, hướng và vị trí địa lý của công trình." />

            {/* Toggle: only show inputs if user has new data to enter */}
            <label className="flex items-center gap-2.5 cursor-pointer select-none mb-4 w-fit group">
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={overrideDims} onChange={e => setOverrideDims(e.target.checked)} />
                <div className="w-5 h-5 rounded border-2 border-gray-300 bg-white peer-checked:bg-green-600 peer-checked:border-green-600 transition-colors flex items-center justify-center group-hover:border-green-400">
                  {overrideDims && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={2.5}><polyline points="2,6 5,9 10,3" /></svg>}
                </div>
              </div>
              <span className="text-sm text-gray-700">Tôi có thông số mới cần nhập / hiệu chỉnh</span>
            </label>

            {overrideDims ? (
              <div className="grid grid-cols-3 gap-4">
                <InputField label="Đoạn tham chiếu A – B" value="5.40" unit="m" sub="Khoảng cách thực tế giữa hai điểm trên bản vẽ." />
                <InputField label="Vĩ độ" value="10.776" unit="°" sub="Tọa độ địa lý của công trình." />
                <InputField label="Kinh độ" value="106.701" unit="°" sub="Tọa độ địa lý của công trình." />
                <InputField label="Độ nghiêng mái" value="15" unit="°" sub="Góc nghiêng so với mặt phẳng nằm ngang." />
                <InputField label="Hướng mái" value="178" unit="°" sub="0° Bắc – 90° Đông – 180° Nam." />
                <InputField label="Khoảng cách mép mái" value="0.80" unit="m" sub="Lối đi bảo trì / vùng an toàn theo bản vẽ kỹ thuật." />
              </div>
            ) : (
              <div className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                <span className="text-lg">📐</span>
                <div>
                  <div className="text-sm text-gray-600 font-medium">Dùng thông số nhận diện từ ảnh / bản vẽ đã tải lên</div>
                  <div className="text-xs text-gray-400 mt-0.5">Tick vào ô trên nếu bạn muốn nhập hoặc hiệu chỉnh thủ công.</div>
                </div>
                <div className="ml-auto flex gap-3 text-xs font-mono text-gray-500">
                  <span>10 × 8 m</span>
                  <span>·</span>
                  <span>178° Nam</span>
                  <span>·</span>
                  <span>10.776°N 106.701°E</span>
                </div>
              </div>
            )}
          </Card>

          {/* Section 3 */}
          <Card className="p-5">
            <SectionNum n={3} label="Linh kiện & mục tiêu" sub="Chọn thiết bị và mục tiêu tối ưu cho hệ thống. Bạn cũng có thể thêm tấm pin tùy chỉnh nếu chưa có trong danh sách." />
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Tấm pin (PV module)</label>
                <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 bg-white focus:outline-none focus:border-green-400">
                  <option>LONGi Hi-MO 6 580W</option>
                  <option>Jinko Tiger Neo 575W</option>
                  <option>Trina Vertex N 600W</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Inverter</label>
                <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 bg-white focus:outline-none focus:border-green-400">
                  <option>Huawei SUN2000-12K-MAP0</option>
                  <option>SMA Sunny Boy 10.0</option>
                </select>
              </div>
              <InputField label="Ngân sách tham chiếu" value="120" unit="triệu VND" />
            </div>
            <button className="text-xs text-green-700 font-medium hover:underline mb-4">+ Thêm tấm pin tùy chỉnh</button>
            <div className="text-xs text-gray-500 mb-2 font-medium">Mục tiêu thiết kế</div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id:'max' as const, icon:'📊', label:'Tối đa sản lượng', sub:'Ưu tiên điện năng tạo ra' },
                { id:'bal' as const, icon:'⚖️', label:'Cân bằng', sub:'Điện năng · chi phí · độ bền' },
                { id:'dur' as const, icon:'🛡️', label:'Ưu tiên độ bền', sub:'Tăng tuổi thọ, ít nhạy với sai số' },
              ].map(g => (
                <div key={g.id} onClick={() => setGoal(g.id)}
                  className={`border rounded-xl p-3 cursor-pointer transition-all ${goal===g.id ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${goal===g.id ? 'border-green-600 bg-green-600' : 'border-gray-300'}`}>
                      {goal===g.id && <div className="w-2 h-2 bg-white rounded-full" />}
                    </div>
                    <span className="text-base">{g.icon}</span>
                    <span className="text-sm font-semibold text-gray-800">{g.label}</span>
                  </div>
                  <div className="text-xs text-gray-500 ml-6">{g.sub}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="sticky top-[57px] space-y-4">
          {/* House illustration placeholder */}
          <div className="bg-green-50 border border-green-100 rounded-xl p-4 flex items-center gap-3">
            <div className="w-14 h-14 flex-shrink-0">
              <svg viewBox="0 0 56 56" className="w-full h-full">
                <rect x="4" y="28" width="48" height="24" fill="#d1fae5" rx="2"/>
                <polygon points="28,6 52,28 4,28" fill="#6ee7b7"/>
                <rect x="20" y="38" width="10" height="14" fill="#a7f3d0"/>
                <rect x="34" y="38" width="12" height="10" fill="#6ee7b7"/>
              </svg>
            </div>
            <div>
              <div className="text-xs font-semibold text-green-900">Biến dữ liệu thực tế</div>
              <div className="text-xs text-green-700">thành thiết kế tối ưu</div>
            </div>
          </div>

          <Card className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              <div className="font-semibold text-gray-800 text-sm">Mức sẵn sàng dữ liệu</div>
            </div>
            <div className="text-xs text-gray-500 mb-3">Đánh giá độ đầy đủ của dữ liệu cho mô hình Digital Roof.</div>
            <div className="space-y-2.5">
              {readiness.map(r => (
                <div key={r.label} className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-medium text-gray-700">{r.label}</div>
                    {r.sub && <div className="text-[10px] text-gray-400">{r.sub}</div>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Dot tone={r.tone} />
                    <Pill tone={r.tone}>{r.val}</Pill>
                    <svg className="w-3 h-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-xs text-green-700">
            <div className="font-semibold mb-1">💡 Chiến lược dữ liệu giai đoạn nguyên mẫu</div>
            <p className="leading-relaxed text-green-600">Giai đoạn đầu, SolarOpt sử dụng các công cụ mã nguồn mở và dữ liệu do người dùng cung cấp.</p>
          </div>

          <button onClick={onNext}
            className="w-full text-white font-semibold py-3 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
            style={{ background: G }}>
            Tạo Digital Roof & kiểm tra dữ liệu →
          </button>
          <div className="text-[10px] text-gray-400 text-center">Sau khi kiểm tra, bạn sẽ chuyển sang bước hợp nhất dữ liệu để xem Digital Roof và các chi tiết nhận diện.</div>
        </div>
      </div>
    </div>
  )
}

// ─── Add-obstacle popover ─────────────────────────────────────────────────────

const SHAPE_OPTIONS: { id: ObsShape; label: string; svg: React.ReactNode }[] = [
  { id: 'circle',   label: 'Hình tròn',    svg: <circle cx="20" cy="20" r="14" fill="rgba(168,85,247,0.2)" stroke="#a855f7" strokeWidth="2"/> },
  { id: 'square',   label: 'Hình vuông',   svg: <rect x="6" y="6" width="28" height="28" rx="3" fill="rgba(168,85,247,0.2)" stroke="#a855f7" strokeWidth="2"/> },
  { id: 'rect',     label: 'Chữ nhật',     svg: <rect x="3" y="10" width="34" height="20" rx="3" fill="rgba(168,85,247,0.2)" stroke="#a855f7" strokeWidth="2"/> },
  { id: 'triangle', label: 'Tam giác',     svg: <polygon points="20,5 36,34 4,34" fill="rgba(168,85,247,0.2)" stroke="#a855f7" strokeWidth="2"/> },
]

function AddObstaclePopover({ screenX, screenY, canvasRef, onConfirm, onCancel, index }: {
  screenX: number; screenY: number
  canvasRef: React.RefObject<HTMLDivElement | null>
  onConfirm: (shape: ObsShape, wM: number, hM: number, label: string) => void
  onCancel: () => void
  index: number
}) {
  const [shape, setShape] = useState<ObsShape>('circle')
  const [wM, setWM] = useState('1.0')
  const [hM, setHM] = useState('1.0')
  const [label, setLabel] = useState(`Vật thể ${index}`)

  // Position popover relative to canvas container
  const rect = canvasRef.current?.getBoundingClientRect()
  const left = rect ? Math.min(screenX - rect.left + 12, rect.width - 260) : 0
  const top  = rect ? Math.min(screenY - rect.top  - 10, rect.height - 300) : 0
  const isCircle = shape === 'circle'

  return (
    <div className="absolute z-50 bg-white border border-gray-200 rounded-xl shadow-xl p-4 w-60"
      style={{ left, top }}
      onPointerDown={e => e.stopPropagation()}
    >
      <div className="text-xs font-semibold text-gray-700 mb-3">Chọn hình dạng vật cản</div>

      {/* Shape picker */}
      <div className="grid grid-cols-4 gap-1.5 mb-4">
        {SHAPE_OPTIONS.map(s => (
          <button key={s.id} onClick={() => setShape(s.id)}
            className={`flex flex-col items-center gap-1 p-1.5 rounded-lg border transition-all ${shape === s.id ? 'border-purple-400 bg-purple-50' : 'border-gray-200 hover:border-purple-200 hover:bg-purple-50/40'}`}>
            <svg viewBox="0 0 40 40" className="w-9 h-9">{s.svg}</svg>
            <span className="text-[9px] font-medium text-gray-600 leading-tight text-center">{s.label}</span>
          </button>
        ))}
      </div>

      {/* Label */}
      <div className="mb-3">
        <label className="text-[10px] text-gray-500 block mb-1">Nhãn</label>
        <input value={label} onChange={e => setLabel(e.target.value)}
          className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-purple-400" />
      </div>

      {/* Size inputs */}
      <div className="mb-4">
        <label className="text-[10px] text-gray-500 block mb-1">Kích thước</label>
        {isCircle ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:border-purple-400">
              <input type="number" min="0.1" max="5" step="0.1" value={wM}
                onChange={e => { setWM(e.target.value); setHM(e.target.value) }}
                className="flex-1 text-xs px-2 py-1.5 focus:outline-none font-mono" />
              <span className="text-[10px] text-gray-400 pr-2">m Ø</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <div className="flex-1 flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:border-purple-400">
              <input type="number" min="0.1" max="10" step="0.1" value={wM}
                onChange={e => setWM(e.target.value)}
                className="flex-1 text-xs px-2 py-1.5 focus:outline-none font-mono" />
              <span className="text-[10px] text-gray-400 pr-1.5">m</span>
            </div>
            <span className="text-xs text-gray-400">×</span>
            <div className="flex-1 flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:border-purple-400">
              <input type="number" min="0.1" max="10" step="0.1" value={hM}
                onChange={e => setHM(e.target.value)}
                className="flex-1 text-xs px-2 py-1.5 focus:outline-none font-mono" />
              <span className="text-[10px] text-gray-400 pr-1.5">m</span>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button onClick={onCancel}
          className="flex-1 text-xs text-gray-500 border border-gray-200 rounded-lg py-1.5 hover:bg-gray-50">
          Hủy
        </button>
        <button onClick={() => onConfirm(shape, parseFloat(wM) || 1, parseFloat(hM) || 1, label)}
          className="flex-1 text-xs font-semibold text-white rounded-lg py-1.5"
          style={{ background: '#a855f7' }}>
          Thêm vật cản
        </button>
      </div>
    </div>
  )
}

// ─── Step 2: Hợp nhất dữ liệu ────────────────────────────────────────────────

function Step2({ onNext, tabImages, obsPos, onObsMove }: {
  onNext: () => void
  tabImages: Array<{image: string | null, name: string | null}>
  obsPos: Record<string, {cx: number, cy: number}>
  onObsMove: (id: string, cx: number, cy: number) => void
}) {
  const [viewTab, setViewTab] = useState(0) // 0=ảnh drone, 1=lớp AI

  // Image for current view tab (for detection): prefer current tab, fallback to any
  const uploadedImage = tabImages[viewTab]?.image ?? tabImages.find(t => t.image)?.image ?? null
  const blueprintImage = tabImages[0].image
  const droneImage = tabImages[1].image
  const fieldImage = tabImages[2].image
  const [selObs, setSelObs] = useState('bon_nuoc')
  const [activeTool, setActiveTool] = useState('select')
  const [compassAngle, setCompassAngle] = useState(360)
  const [customObs, setCustomObs] = useState<CustomObs[]>([])
  const [pendingAdd, setPendingAdd] = useState<{svgX: number, svgY: number, screenX: number, screenY: number} | null>(null)
  const canvasRef = useRef<HTMLDivElement>(null)
  const [isDetecting, setIsDetecting] = useState(false)
  const [detectStatus, setDetectStatus] = useState<'idle' | 'done' | 'error'>('idle')
  const [detectMsg, setDetectMsg] = useState('')
  const [backendMode, setBackendMode] = useState<'unknown'|'gemini'|'demo'>('unknown')

  const obs = OBS.find(o => o.id === selObs) ?? OBS[1]

  const runDetection = async () => {
    const selected = tabImages.find(t => t.image)
    if (!selected?.image) {
      setDetectMsg('Vui lòng tải ảnh lên ở Bước 1 trước.')
      setDetectStatus('error')
      return
    }

    setIsDetecting(true)
    setDetectStatus('idle')
    setDetectMsg('Đang phân tích ảnh bằng AI qua backend SolarOpt...')
    setViewTab(1)

    try {
      const response = await fetch(selected.image)
      const blob = await response.blob()
      const safeName = selected.name || `solaropt-input.${(blob.type.split('/')[1] || 'png').replace('jpeg','jpg')}`
      const file = new File([blob], safeName, { type: blob.type || 'image/png' })
      const data = await api.analyze(file)
      setBackendMode(data.mode)

      const detectedCustom: CustomObs[] = []
      data.obstacles.forEach((d, idx) => {
        const cx = (d.x_pct / 100) * VW
        const cy = (d.y_pct / 100) * VH
        const existingObs = OBS.find(o =>
          o.id === d.id ||
          o.label.toLowerCase().includes(d.label.toLowerCase().slice(0, 4)) ||
          d.label.toLowerCase().includes(o.label.toLowerCase().slice(0, 4))
        )
        if (existingObs) {
          onObsMove(existingObs.id, cx, cy)
        } else {
          detectedCustom.push({
            id: d.id || `ai-${idx}`,
            cx, cy,
            shape: 'rect',
            w: Math.max(24, (d.width_pct / 100) * VW),
            h: Math.max(20, (d.depth_pct / 100) * VH),
            label: d.label,
          })
        }
      })
      if (detectedCustom.length) {
        setCustomObs(prev => {
          const manual = prev.filter(o => !o.id.startsWith('ai-'))
          return [...manual, ...detectedCustom]
        })
      }

      setDetectStatus('done')
      setDetectMsg(`✓ ${data.mode === 'gemini' ? 'Gemini 2.5 Flash-Lite' : 'Chế độ demo'} phát hiện ${data.obstacles.length} vật cản. Kỹ sư có thể kéo để hiệu chỉnh.`)
    } catch (err) {
      setDetectStatus('error')
      setDetectMsg(`Lỗi backend AI: ${(err as Error).message}`)
    } finally {
      setIsDetecting(false)
    }
  }

  const tools = [
    { id:'select',  icon:'↖', label:'Chọn & kéo vật cản',    desc:'Chọn và di chuyển vật cản' },
    { id:'pan',     icon:'⊕', label:'Di chuyển bản đồ',       desc:'Kéo để di chuyển góc nhìn' },
    { id:'measure', icon:'📏', label:'Đo khoảng cách',         desc:'Nhấn 2 điểm để đo' },
    { id:'add',     icon:'↔', label:'Thêm vật cản',            desc:'Nhấn vào mái để thêm' },
  ]

  const toolDesc: Record<string,string> = {
    select: 'Kéo các ô vật cản để điều chỉnh vị trí',
    pan: 'Kéo bản đồ để di chuyển góc nhìn',
    measure: 'Nhấn 2 điểm trên mái để đo khoảng cách thực tế',
    add: 'Nhấn vào vị trí trống trên mái để thêm vật cản mới',
  }

  return (
    <div className="animate-fade-up">
      <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-[44px_1fr_320px] gap-4">
        {/* Left toolbar — only functional on Tab 1 (Lớp AI) */}
        <div className="flex flex-col gap-2 pt-1">
          {tools.map(t => {
            const isActive = activeTool === t.id
            const disabled = viewTab !== 1
            return (
              <button key={t.id}
                onClick={() => { if (!disabled) { setActiveTool(t.id); setViewTab(1) } else { setActiveTool(t.id); setViewTab(1) } }}
                title={disabled ? `${t.label} (chuyển sang Lớp AI)` : t.label}
                className={`w-10 h-10 rounded-xl flex items-center justify-center text-base transition-all
                  ${isActive && !disabled ? 'bg-green-100 text-green-800 border border-green-300 shadow-sm'
                  : disabled ? 'bg-white border border-gray-200 text-gray-300 hover:text-gray-400 hover:border-gray-300 cursor-pointer'
                  : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
                {t.icon}
              </button>
            )
          })}
          {/* Separator */}
          <div className="w-full h-px bg-gray-200 my-1" />
          {/* Compass angle display */}
          <div className="w-10 flex flex-col items-center gap-0.5 cursor-default" title="Hướng mái — kéo la bàn trong Lớp AI">
            <div className="text-[9px] font-bold text-green-800 leading-none">{compassAngle}°</div>
            <div className="text-[8px] text-gray-400 leading-none">
              {compassAngle < 45 || compassAngle >= 315 ? 'N' : compassAngle < 135 ? 'E' : compassAngle < 225 ? 'S' : 'W'}
            </div>
          </div>
        </div>

        {/* Map area */}
        <div>
          <Card className="overflow-hidden">
            {/* Map tabs */}
            <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-100">
              {['Ảnh drone','Lớp AI'].map((t,i) => (
                <button key={t} onClick={() => setViewTab(i)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${viewTab===i ? 'bg-green-50 text-green-800 border border-green-200' : 'text-gray-500 hover:bg-gray-50'}`}>
                  {i===0?'🛰':'🤖'} {t}
                </button>
              ))}
              <button className="ml-auto flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-2.5 py-1.5">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
                Toàn màn hình
              </button>
            </div>
            {/* Tab 0: Drone / overhead image viewer */}
            {viewTab === 0 && (
              <div className="relative bg-gray-900" style={{ aspectRatio: '650/480' }}>
                {droneImage ? (
                  <>
                    <img src={droneImage} alt="Ảnh từ trên xuống" className="w-full h-full object-contain" />
                    <div className="absolute top-2 left-2 flex gap-1.5">
                      <span className="bg-white/90 text-xs font-medium text-gray-700 px-2 py-1 rounded-md border border-gray-200">🛰 Ảnh drone</span>
                      <button onClick={() => { setViewTab(1); runDetection() }}
                        className="flex items-center gap-1 bg-green-700 text-white text-xs font-semibold px-2.5 py-1 rounded-md">
                        🤖 Phân tích AI →
                      </button>
                    </div>
                  </>
                ) : fieldImage ? (
                  <>
                    <img src={fieldImage} alt="Ảnh hiện trường" className="w-full h-full object-contain" />
                    <div className="absolute top-2 left-2 flex gap-1.5">
                      <span className="bg-white/90 text-xs font-medium text-gray-700 px-2 py-1 rounded-md border border-gray-200">📷 Ảnh hiện trường</span>
                      <button onClick={() => { setViewTab(1); runDetection() }}
                        className="flex items-center gap-1 bg-green-700 text-white text-xs font-semibold px-2.5 py-1 rounded-md">
                        🤖 Phân tích AI →
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-gray-500">
                    <span className="text-4xl">🛰</span>
                    <div className="text-sm font-medium">Chưa có ảnh từ trên xuống</div>
                    <div className="text-xs text-gray-400">Tải lên ở Bước 1 → tab "Ảnh từ trên xuống"</div>
                  </div>
                )}
              </div>
            )}

            {/* Tab 1: AI simulation canvas */}
            {viewTab === 1 && (
              <>
                {/* Detection toolbar */}
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border-b border-gray-100 flex-wrap">
                  {(blueprintImage || droneImage || fieldImage) ? (
                    <button onClick={runDetection} disabled={isDetecting}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-colors disabled:opacity-60"
                      style={{ background: isDetecting ? '#6b7280' : '#1a5c35' }}>
                      {isDetecting ? <><span className="animate-spin">⟳</span> Đang phân tích...</> : '🤖 Chạy lại phân tích AI'}
                    </button>
                  ) : (
                    <span className="text-[11px] text-gray-400">Tải ảnh lên ở Bước 1 để phân tích AI</span>
                  )}
                  {detectMsg && (
                    <span className={`text-[11px] font-medium ${detectStatus === 'error' ? 'text-red-600' : detectStatus === 'done' ? 'text-green-700' : 'text-gray-500'}`}>
                      {detectMsg}
                    </span>
                  )}
                  <span className="ml-auto text-[10px] text-gray-400">🔐 API key được giữ ở backend</span>
                  {backendMode !== 'unknown' && <Pill tone={backendMode === 'gemini' ? 'green' : 'amber'}>{backendMode === 'gemini' ? 'Gemini' : 'Demo fallback'}</Pill>}
                  <span className="text-[10px] text-sky-600 font-medium">{toolDesc[activeTool]}</span>
                </div>

                {/* SVG simulation */}
                <div ref={canvasRef} className="relative bg-gray-900" style={{ aspectRatio: '650/480' }}>
                  <AerialSVG mode="detect" selectedObs={selObs} onSelectObs={setSelObs}
                    obsPos={obsPos}
                    onObsMove={onObsMove}
                    activeTool={activeTool}
                    compassAngle={compassAngle}
                    onCompassChange={setCompassAngle}
                    addedObs={customObs}
                    onAddRequest={(sx, sy, scX, scY) => setPendingAdd({svgX: sx, svgY: sy, screenX: scX, screenY: scY})}
                  />

                  {/* Tool mode banner — context-sensitive instructions */}
                  {activeTool === 'measure' && (
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-amber-50 border border-amber-300 text-amber-800 text-[11px] font-semibold px-3 py-1.5 rounded-lg shadow-sm flex items-center gap-1.5">
                      📏 Nhấn điểm đầu trên mái, rồi nhấn điểm cuối để đo khoảng cách
                    </div>
                  )}
                  {activeTool === 'pan' && (
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-sky-50 border border-sky-300 text-sky-800 text-[11px] font-semibold px-3 py-1.5 rounded-lg shadow-sm flex items-center gap-1.5">
                      ✋ Kéo bản đồ để di chuyển góc nhìn
                    </div>
                  )}
                  {activeTool === 'add' && (
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-purple-50 border border-purple-300 text-purple-800 text-[11px] font-semibold px-3 py-1.5 rounded-lg shadow-sm flex items-center gap-1.5">
                      ➕ Nhấn vào vị trí trên mái để thêm vật cản mới
                    </div>
                  )}
                  {activeTool === 'select' && (
                    <div className="absolute top-2 left-2 bg-white/85 text-[10px] font-semibold text-gray-600 px-2 py-1 rounded-md">
                      🤖 Mô phỏng AI · Kéo ô màu để chỉnh vị trí vật cản
                    </div>
                  )}

                  {/* Compass hint */}
                  <div className="absolute bottom-2 left-2 bg-white/70 text-[9px] text-gray-500 px-1.5 py-1 rounded-md">
                    🧭 Kéo la bàn để xoay hướng mái
                  </div>
                </div>

                {/* Add-obstacle popover */}
                {pendingAdd && (
                  <AddObstaclePopover
                    screenX={pendingAdd.screenX}
                    screenY={pendingAdd.screenY}
                    canvasRef={canvasRef}
                    onConfirm={(shape, wM, hM, label) => {
                      const PX_PER_M = 552 / 10
                      setCustomObs(prev => [...prev, {
                        id: `custom_${Date.now()}`,
                        cx: pendingAdd.svgX,
                        cy: pendingAdd.svgY,
                        shape,
                        w: wM * PX_PER_M,
                        h: hM * PX_PER_M,
                        label,
                      }])
                      setPendingAdd(null)
                    }}
                    onCancel={() => setPendingAdd(null)}
                    index={customObs.length + 1}
                  />
                )}
              </>
            )}
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-3">
          {/* Selected object */}
          <Card className="p-4">
            <div className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">Đối tượng đang chọn</div>
            <div className="flex gap-3 mb-3">
              <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center text-2xl shrink-0">
                {obs.id==='bon_nuoc'?'🪣':obs.id==='ong_thong_gio'?'🌀':obs.id==='dan_nong'?'❄️':'❓'}
              </div>
              <div>
                <div className="font-semibold text-gray-800 text-sm">{obs.label}</div>
                <div className="text-xs text-gray-500">{obs.kind}</div>
              </div>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between"><span className="text-gray-500">Kích thước footprint</span><span className="font-mono text-gray-700">{obs.size}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Chiều cao</span><span className="font-mono text-gray-700">{obs.height}</span></div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">Độ chắc chắn (AI)</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${obs.conf}%`, background: obs.conf>90?'#22c55e':obs.conf>60?'#f59e0b':'#ef4444' }} />
                  </div>
                  <span className="font-mono font-bold text-gray-700">{obs.conf}%</span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">Ảnh hưởng</span>
                <Dot tone={obs.impact==='Cao'?'red':obs.impact==='Trung bình'?'amber':'green'} />
                <Pill tone={obs.impact==='Cao'?'red':obs.impact==='Trung bình'?'amber':'green'}>{obs.impact}</Pill>
              </div>
              {obs.tags.length > 0 && (
                <div className="flex justify-between items-center pt-1">
                  <span className="text-gray-500">Tác động đến thiết kế</span>
                  <div className="flex gap-1 flex-wrap justify-end">{obs.tags.map(t => <Pill key={t} tone="red">{t}</Pill>)}</div>
                </div>
              )}
            </div>
          </Card>

          {/* Compass / roof direction card */}
          <Card className="p-4">
            <div className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">Hướng mái</div>
            <div className="flex items-center gap-3">
              <div className="relative w-14 h-14 shrink-0">
                <svg viewBox="-22 -22 44 44" className="w-full h-full">
                  <circle cx="0" cy="0" r="20" fill="#f0f4f0" stroke="#d1d5db" strokeWidth="1.5" />
                  {[0,90,180,270].map(deg => {
                    const rad = (deg - compassAngle) * Math.PI / 180
                    return <line key={deg} x1={Math.sin(rad)*12} y1={-Math.cos(rad)*12} x2={Math.sin(rad)*18} y2={-Math.cos(rad)*18} stroke="#9ca3af" strokeWidth="1.5" />
                  })}
                  <g transform={`rotate(${compassAngle})`}>
                    <polygon points="0,-14 3,5 0,1 -3,5" fill="#1a5c35" />
                    <polygon points="0,14 3,-5 0,-1 -3,-5" fill="#d1d5db" />
                  </g>
                  <text x="0" y={-(20 * Math.cos((0 - compassAngle) * Math.PI / 180)) - 1}
                    dx={20 * Math.sin((0 - compassAngle) * Math.PI / 180)}
                    textAnchor="middle" fontSize="6" fontWeight="800" fill="#1a5c35">N</text>
                </svg>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-800 leading-none">{compassAngle}°</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {compassAngle < 22.5 || compassAngle >= 337.5 ? 'Bắc' : compassAngle < 67.5 ? 'Đông Bắc' : compassAngle < 112.5 ? 'Đông' : compassAngle < 157.5 ? 'Đông Nam' : compassAngle < 202.5 ? 'Nam' : compassAngle < 247.5 ? 'Tây Nam' : compassAngle < 292.5 ? 'Tây' : 'Tây Bắc'}
                </div>
                <div className="text-[10px] text-gray-400 mt-1">Kéo la bàn trên bản đồ để thay đổi</div>
              </div>
            </div>
          </Card>

          {/* Detection list */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-semibold text-gray-700">Danh sách phát hiện ({OBS.length})</div>
              <select className="text-[10px] text-gray-500 border border-gray-200 rounded-md px-1.5 py-1 bg-white">
                <option>Sắp xếp theo: Độ chắc chắn</option>
              </select>
            </div>
            <div className="space-y-1">
              {OBS.map(o => (
                <div key={o.id} onClick={() => setSelObs(o.id)}
                  className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${selObs===o.id?'bg-green-50 border border-green-200':'hover:bg-gray-50 border border-transparent'}`}>
                  <span className="text-xs">{o.id==='bien_mai'?'🔷':o.id==='bon_nuoc'?'🟡':o.id==='ong_thong_gio'?'🟢':o.id==='dan_nong'?'🟠':'🟡'}</span>
                  <span className="flex-1 text-xs text-gray-700 truncate">{o.label}</span>
                  <Dot tone={o.conf>90?'green':o.conf>60?'amber':'amber'} />
                  <span className="text-xs font-mono font-semibold text-gray-600">{o.conf}%</span>
                  <svg className="w-3 h-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                </div>
              ))}
            </div>
          </Card>

          {/* Uncertainty note */}
          {selObs === 'vat_the_a' && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <div className="flex items-center gap-2 mb-1">
                <Dot tone="amber" /><span className="text-xs font-semibold text-amber-800">Vật thể A ?</span>
                <Pill tone="amber">Độ chắc chắn: 52%</Pill><Pill tone="green">Ảnh hưởng thấp</Pill>
              </div>
              <p className="text-xs text-amber-700 leading-relaxed">Vật thể này có độ chắc chắn thấp nhưng ước tính chỉ ảnh hưởng ~0.7% sản lượng, nên hệ thống có thể tiếp tục.</p>
              <button className="text-xs text-amber-800 font-medium mt-2 hover:underline flex items-center gap-1">
                🔍 Mô phỏng trường hợp phải hỏi kỹ sư
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
              </button>
            </div>
          )}

          <button onClick={onNext}
            className="w-full text-white font-semibold py-3 rounded-xl text-sm transition-colors"
            style={{ background: G }}>
            Xác nhận Digital Roof →
          </button>
          <div className="text-[10px] text-gray-400 text-center">Sau khi xác nhận, hệ thống sẽ tạo mô hình 3D và chuyển sang bước thiết kế.</div>
        </div>
      </div>
    </div>
  )
}

// ─── Step 3: Thiết kế ─────────────────────────────────────────────────────────

function Step3({ onNext }: { onNext: () => void }) {
  const [viewTab, setViewTab] = useState('bố trí')
  const [selPanel, setSelPanel] = useState<number | null>(4)
  const [timeH, setTimeH] = useState(10)
  const [selAlt, setSelAlt] = useState<string | null>(null)
  const [inDesign, setInDesign] = useState(1)

  const viewTabs = ['Bố trí','Bóng che','Bức xạ','So sánh panel','Xem 3D']
  const alternatives = [
    { name:'Jinko Tiger Neo 575W', w:'575 W', eff:'22.3%', icon:'▪' },
    { name:'Trina Vertex N 600W', w:'600 W', eff:'22.8%', icon:'▪' },
  ]

  const panelInfo = selPanel !== null ? {
    loc: `Hàng ${Math.floor(selPanel/5)+1} · Cột ${(selPanel%5)+1}`,
    kwh: (843 + (selPanel % 5) * 12).toFixed(0),
    shadow: '0.0%',
    dir: 'Dọc',
    radiation: 'Top 20%',
  } : null

  return (
    <div className="animate-fade-up">
      <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-[220px_1fr_300px] gap-4">
        {/* Left panel selector */}
        <div className="space-y-3">
          <Card className="p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3">Phương án linh kiện</div>
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs text-gray-500">Phương án tham chiếu</div>
              <Pill tone="green">Đang dùng</Pill>
            </div>
            {/* Current panel */}
            <div className="flex gap-3 p-2 bg-gray-50 rounded-lg mb-4">
              <div className="w-10 h-16 bg-[#1e3a5f] rounded flex-shrink-0 border border-blue-300" />
              <div>
                <div className="text-sm font-semibold text-gray-800">LONGi Hi-MO 6 580W</div>
                <div className="text-xs text-gray-500 mt-1">
                  <div>Công suất &nbsp;&nbsp;<span className="font-mono font-bold">580 W</span></div>
                  <div>Hiệu suất &nbsp;&nbsp;<span className="font-mono font-bold">22.8%</span></div>
                  <div className="font-mono text-[10px]">2278 × 1134 mm</div>
                </div>
              </div>
            </div>
            <div className="text-xs text-gray-500 mb-2">Đề xuất thay thế</div>
            {alternatives.map(a => (
              <div key={a.name} onClick={() => setSelAlt(selAlt===a.name?null:a.name)}
                className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer border transition-colors mb-1.5 ${selAlt===a.name?'border-green-300 bg-green-50':'border-gray-100 hover:bg-gray-50'}`}>
                <div className={`w-4 h-4 rounded-full border-2 ${selAlt===a.name?'border-green-600':'border-gray-300'}`} />
                <div className="w-6 h-10 bg-[#1e3a5f] rounded shrink-0" />
                <div>
                  <div className="text-xs font-medium text-gray-700">{a.name}</div>
                  <div className="text-[10px] text-gray-400">{a.w} | {a.eff}</div>
                </div>
              </div>
            ))}
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-2 mt-2">
              <p className="text-[10px] text-blue-700">SolarOpt sẽ thiết kế lại toàn bộ bố trí cho từng phương án, thay vì chỉ so sánh thông số trong datasheet.</p>
            </div>
          </Card>
        </div>

        {/* Main viewer */}
        <div>
          <Card className="overflow-hidden">
            {/* View tabs */}
            <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-100 flex-wrap">
              {viewTabs.map(t => (
                <button key={t} onClick={() => setViewTab(t.toLowerCase())}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${viewTab===t.toLowerCase()?'bg-green-50 text-green-800 border border-green-200':'text-gray-500 hover:bg-gray-50'}`}>
                  {t==='Bố trí'?'📐 ':t==='Bóng che'?'☀️ ':t==='Bức xạ'?'📊 ':t==='So sánh panel'?'⬛ ':'🧊 '}{t}
                </button>
              ))}
              <div className="ml-auto flex gap-1">
                {['↩','↪'].map(s => <button key={s} className="w-7 h-7 rounded-md bg-gray-100 text-gray-500 text-sm flex items-center justify-center">{s}</button>)}
                <button className="px-2 py-1 rounded-md bg-gray-100 text-gray-500 text-xs">🧊 Xem 3D</button>
              </div>
            </div>

            {/* Map header */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border-b border-gray-100">
              <select className="text-xs border border-gray-200 rounded-md px-2 py-1 bg-white">
                <option>🏠 Mái nhà (v2 – Balanced)</option>
              </select>
            </div>

            {/* SVG canvas — content switches per tab */}
            {viewTab === 'so sánh panel' ? (
              <div className="grid grid-cols-2 divide-x divide-gray-200" style={{ aspectRatio: '650/240' }}>
                {/* Left: reference */}
                <div className="relative bg-gray-900">
                  <div className="absolute top-2 left-2 z-10 bg-green-700/90 text-white text-[10px] px-2 py-0.5 rounded font-semibold">
                    ✓ Tham chiếu · LONGi 580W · 17 tấm
                  </div>
                  <AerialSVG mode="design" selectedPanel={selPanel} onSelectPanel={setSelPanel} panelList={PANELS_17} />
                </div>
                {/* Right: selected alternative */}
                <div className="relative bg-gray-900">
                  <div className="absolute top-2 left-2 z-10 bg-blue-600/90 text-white text-[10px] px-2 py-0.5 rounded font-semibold">
                    ⬛ {selAlt ?? 'Jinko Tiger Neo 575W'} · 18 tấm
                  </div>
                  <AerialSVG mode="design" panelList={PANELS_18} />
                  {/* Diff highlight — extra panel */}
                  <div className="absolute inset-0 pointer-events-none">
                    <svg viewBox="0 0 650 480" className="w-full h-full">
                      <rect x={565} y={220} width={45} height={27} fill="none" stroke="#f59e0b" strokeWidth="3" strokeDasharray="5 3" rx="2" />
                      <text x={588} y={247} textAnchor="middle" fontSize="8" fill="#f59e0b" fontWeight="700">NEW</text>
                    </svg>
                  </div>
                </div>
              </div>
            ) : viewTab === 'xem 3d' ? (
              <div className="flex items-center justify-center bg-gray-950" style={{ aspectRatio: '650/480' }}>
                <div className="text-center text-gray-500">
                  <div className="text-4xl mb-3">🧊</div>
                  <div className="text-sm font-medium text-gray-400">Mô hình 3D đang xử lý…</div>
                  <div className="text-xs text-gray-600 mt-1">Tính năng sẽ ra mắt trong phiên bản tiếp theo</div>
                </div>
              </div>
            ) : (
              <div className="relative bg-gray-900" style={{ aspectRatio: '650/480' }}>
                <AerialSVG
                  mode="design"
                  selectedPanel={selPanel}
                  onSelectPanel={setSelPanel}
                  panelList={PANELS_17}
                  tintMode={viewTab === 'bóng che' ? 'shadow' : viewTab === 'bức xạ' ? 'radiation' : undefined}
                  timeH={timeH}
                />
                {/* Shadow legend */}
                {viewTab === 'bóng che' && (
                  <div className="absolute top-2 right-2 bg-white/90 rounded-lg p-2 text-[10px] space-y-1">
                    {[['#ef4444','> 40% bóng che'],['#f59e0b','10–40%'],['#1e3a5f','< 10%']].map(([c,l]) => (
                      <div key={l} className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: c }} />
                        <span className="text-gray-600">{l}</span>
                      </div>
                    ))}
                  </div>
                )}
                {/* Radiation legend */}
                {viewTab === 'bức xạ' && (
                  <div className="absolute top-2 right-2 bg-white/90 rounded-lg p-2 text-[10px] space-y-1">
                    <div className="text-gray-500 font-semibold mb-1">Bức xạ (kWh/m²)</div>
                    <div className="w-20 h-3 rounded" style={{ background: 'linear-gradient(to right,hsl(40,70%,20%),hsl(80,90%,40%),hsl(120,80%,50%))' }} />
                    <div className="flex justify-between text-gray-500 font-mono"><span>Thấp</span><span>Cao</span></div>
                  </div>
                )}
                {/* View toggle */}
                <div className="absolute bottom-12 left-3 flex gap-1">
                  <button className="px-2 py-1 bg-green-700 text-white text-[10px] rounded-md font-medium">● Ảnh thực tế</button>
                  <button className="px-2 py-1 bg-white/80 text-gray-700 text-[10px] rounded-md font-medium">Mô hình 3D</button>
                </div>
                {/* Zoom */}
                <div className="absolute bottom-3 right-3 flex flex-col gap-1">
                  {['+','−','⛶'].map(s => <button key={s} className="w-7 h-7 bg-white/90 border border-gray-300 rounded-md text-sm font-bold text-gray-700 hover:bg-white flex items-center justify-center">{s}</button>)}
                </div>
              </div>
            )}

            {/* Solar Time Machine */}
            <div className="px-4 py-3 border-t border-gray-100">
              <div className="flex items-center justify-between mb-1.5">
                <div>
                  <div className="text-xs font-semibold text-gray-700">Solar Time Machine</div>
                  <div className="text-[10px] text-gray-400">Xem thay đổi bóng che và bức xạ theo thời gian trong ngày.</div>
                </div>
                <div className="text-xs text-gray-500 font-mono">Tháng 12 · {timeH}:00</div>
              </div>
              <input type="range" min={7} max={17} value={timeH} onChange={e => setTimeH(+e.target.value)}
                className="w-full h-2 rounded-full appearance-none cursor-pointer" style={{ accentColor: G }} />
              <div className="flex justify-between text-[10px] text-gray-400 mt-0.5 font-mono">
                <span>07:00</span><span>09:00</span><span>11:00</span><span>13:00</span><span>15:00</span><span>17:00</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-3">
          {selPanel !== null && panelInfo ? (
            <Card className="p-4">
              <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Vì sao đặt ở đây?</div>
              <div className="text-xs text-gray-500 mb-2 font-mono">Tấm pin #{selPanel+1} · {panelInfo.loc}</div>
              <div className="space-y-1.5 text-xs mb-3">
                <div className="flex justify-between"><span className="text-gray-500">Sản lượng biên</span><span className="font-semibold text-gray-800">{panelInfo.kwh} kWh/năm</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Tổn thất bóng</span><span className="font-semibold text-gray-800">{panelInfo.shadow}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Hướng đặt</span><span className="font-semibold text-gray-800">{panelInfo.dir}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Nhóm bức xạ</span><span className="font-semibold text-gray-800">{panelInfo.radiation}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Hình học & vùng cấm</span><Pill tone="green">Đạt</Pill></div>
              </div>
              <div className="bg-green-50 border border-green-100 rounded-lg p-2 mb-2">
                <div className="flex items-start gap-1.5">
                  <span className="text-green-600 text-sm">✓</span>
                  <p className="text-[11px] text-green-700">Vị trí này có bức xạ cao, không bị bóng che và đáp ứng đầy đủ các ràng buộc kỹ thuật.</p>
                </div>
              </div>
              <div className="text-xs font-semibold text-gray-600 mb-1.5">Vì sao không đặt ở vị trí khác?</div>
              <div className="space-y-1.5">
                {[
                  ['1','Gần vùng bóng','Khu vực phía tây bị bóng che từ cây xanh và nhà lân cận, làm giảm sản lượng đáng kể.'],
                  ['2','Biên hình học không ổn định','Các vị trí sát mép mái có khoảng lùi an toàn nhỏ, không đáp ứng tiêu chuẩn thi công.'],
                ].map(([n,t,s]) => (
                  <div key={n} className="flex gap-2 text-xs">
                    <span className="w-4 h-4 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center shrink-0">{n}</span>
                    <div><span className="font-medium text-gray-700">{t}</span><div className="text-gray-400 text-[10px] mt-0.5">{s}</div></div>
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <Card className="p-4">
              <div className="text-xs text-gray-400 text-center py-4">Nhấn vào một tấm pin để xem giải thích vị trí</div>
            </Card>
          )}

          <Card className="p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Tự vận hành</div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { n:'1', label:'Sinh vị trí khả thi', sub:'Đã tạo 42 vị trí tiềm năng', done:true },
                { n:'2', label:'Tối ưu bố trí', sub:'Đã chọn 17 tấm pin', done:true },
                { n:'3', label:'Mô phỏng bóng', sub:'Đang xử lý...', done:false },
                { n:'4', label:'Tạo phương án', sub:'Chờ thực hiện', done:false },
              ].map(s => (
                <div key={s.n} className={`flex gap-2 p-2 rounded-lg ${s.done?'bg-green-50':'bg-gray-50'}`}>
                  <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${s.done?'bg-green-600 text-white':'bg-gray-300 text-gray-600'}`}>{s.done?'✓':s.n}</div>
                  <div>
                    <div className={`text-[10px] font-semibold ${s.done?'text-green-800':'text-gray-600'}`}>{s.label}</div>
                    <div className={`text-[9px] ${s.done?'text-green-600':'text-gray-400'}`}>{s.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <button onClick={onNext}
            className="w-full text-white font-semibold py-3 rounded-xl text-sm transition-colors"
            style={{ background: G }}>
            Chạy kiểm chứng →
          </button>
          <div className="text-[10px] text-gray-400 text-center">Sau khi chạy, bạn sẽ xem được sản lượng, tổn thất và báo cáo chi tiết.</div>
        </div>
      </div>
    </div>
  )
}

// ─── Step 4: Kiểm chứng ──────────────────────────────────────────────────────

function Step4({ onNext }: { onNext: () => void }) {
  const [sel, setSel] = useState('bal')
  const selectedOpt = DESIGN_OPTIONS.find(o => o.id === sel)!

  return (
    <div className="animate-fade-up">
      <div className="max-w-6xl mx-auto px-6 py-5 space-y-5">
        {/* 3 option cards */}
        <div className="grid grid-cols-3 gap-4">
          {DESIGN_OPTIONS.map(opt => (
            <div key={opt.id} onClick={() => setSel(opt.id)}
              className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${sel===opt.id ? 'border-green-500 bg-white shadow-md' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">{opt.icon}</span>
                <span className="font-semibold text-gray-800 text-sm">{opt.label}</span>
                {(opt as any).rec && <Pill tone="green">Khuyến nghị</Pill>}
              </div>
              <p className="text-[11px] text-gray-500 mb-3 leading-relaxed">{opt.desc}</p>
              <div className="grid grid-cols-2 gap-2">
                {[['Số tấm',`${opt.panels} tấm`],['Sản lượng/năm',`${opt.mwh} MWh`],['Chi phí',`${opt.cost} triệu`],['Stress test',opt.stress]].map(([l,v]) => (
                  <div key={l}>
                    <div className="text-[10px] text-gray-400">{l}</div>
                    <div className={`font-bold text-sm ${sel===opt.id?'text-green-800':'text-gray-800'}`}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-[1fr_340px] gap-5">
          {/* Comparison table + stress tests */}
          <div className="space-y-4">
            <Card className="overflow-hidden">
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-base">📋</span>
                  <span className="font-semibold text-gray-800 text-sm">So sánh phương án</span>
                </div>
                <div className="text-xs text-gray-500">Các chỉ số quan trọng được tổng hợp từ kết quả thiết kế và kiểm chứng.</div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-gray-500 font-medium">Chỉ số</th>
                      {DESIGN_OPTIONS.map(o => <th key={o.id} className={`px-4 py-2 text-center font-semibold ${sel===o.id?'text-green-800 bg-green-50':'text-gray-600'}`}>{o.label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ['Điện năng dự kiến','15.15 MWh/năm','14.32 MWh/năm','12.60 MWh/năm'],
                      ['Số tấm pin','18','17','15'],
                      ['Diện tích mái dùng','53.9 m²','50.9 m²','44.9 m²'],
                      ['Chi phí (ước tính)','75.6 triệu VND','71.4 triệu VND','63.0 triệu VND'],
                      ['Hoàn vốn (ước tính)','4.8 năm','5.2 năm','5.2 năm'],
                      ['Tỷ lệ qua kiểm thử','5/8 (62.5%)','8/8 (100%)','8/8 (100%)'],
                    ].map(([label,...vals]) => (
                      <tr key={label} className="border-t border-gray-50 hover:bg-gray-50/50">
                        <td className="px-4 py-2 text-gray-600">{label}</td>
                        {vals.map((v,i) => (
                          <td key={i} className={`px-4 py-2 text-center font-mono ${sel===DESIGN_OPTIONS[i].id?'text-green-800 font-semibold bg-green-50/50':'text-gray-700'}`}>{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Stress test */}
            <Card className="overflow-hidden">
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-base">🔬</span>
                  <span className="font-semibold text-gray-800 text-sm">Bộ kiểm thử</span>
                </div>
                <div className="text-xs text-gray-500">Kết quả kiểm thử của từng phương án theo 8 kịch bản. Mỗi kịch bản kiểm tra tính ổn định của thiết kế trong các điều kiện thực tế và giả định bất lợi.</div>
              </div>
              <table className="w-full text-xs">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-gray-500 font-medium w-8">#</th>
                    <th className="px-4 py-2 text-left text-gray-500 font-medium">Kịch bản kiểm thử</th>
                    {DESIGN_OPTIONS.map(o => <th key={o.id} className="px-4 py-2 text-center text-gray-500 font-medium">{o.label}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {STRESS.map(s => (
                    <tr key={s.id} className="border-t border-gray-50 hover:bg-gray-50/50">
                      <td className="px-4 py-2 text-gray-400 font-mono">{s.id}</td>
                      <td className="px-4 py-2 text-gray-700">{s.name}</td>
                      {s.r.map((pass,i) => <td key={i} className="px-4 py-2 text-center"><Check pass={pass} /></td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            {/* Dependency chain */}
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-base">🔗</span>
                <span className="font-semibold text-gray-800 text-sm">Tác động phụ thuộc giữa các thành phần</span>
              </div>
              <div className="text-xs text-gray-500 mb-3">Thay đổi ở một thành phần có thể ảnh hưởng đến các bước tiếp theo trong chuỗi thiết kế.</div>
              <div className="flex items-center gap-2 flex-wrap">
                {['Dữ liệu đầu vào','Vị trí khả thi','Bố trí','Bóng che','Sản lượng','Chi phí / ROI'].map((item, i, arr) => (
                  <div key={item} className="flex items-center gap-2">
                    <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-center">
                      <div className="text-[10px] font-semibold text-gray-700">{item}</div>
                      <div className="text-[9px] text-gray-400">{['Bản vẽ, ảnh, thông số','Diện tích, hướng, ràng buộc','Số tấm, layout','Vật cản, che bóng','Mô phỏng & hiệu suất','Tổng chi phí, hoàn vốn'][i]}</div>
                    </div>
                    {i < arr.length-1 && <span className="text-gray-300 text-lg">→</span>}
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Right: verdict + CTA */}
          <div className="space-y-3">
            <div className="bg-green-50 border-2 border-green-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-green-600">✓</span>
                <span className="text-sm font-bold text-green-800">Đã hoàn tất kiểm chứng</span>
              </div>
              <div className="text-xs text-green-700">3 phương án · 8/8 kịch bản</div>
            </div>

            <Card className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-base">💡</span>
                <span className="font-semibold text-gray-800 text-sm">Kết luận kỹ sư</span>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                Phương án <strong className="text-green-800">Cân bằng (khuyến nghị)</strong> đạt hiệu quả tổng thể tốt nhất khi xét đồng thời sản lượng, chi phí và độ bền. Phương án này vượt qua 8/8 kịch bản kiểm thử, đảm bảo tính ổn định trong các điều kiện bất lợi, đồng thời vẫn duy trì sản lượng cao và chi phí hợp lý. Chúng tôi đề xuất chọn phương án này để triển khai chi tiết và bàn giao cho chủ đầu tư.
              </p>
            </Card>

            {/* Selected option summary */}
            <Card className="p-4">
              <div className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Phương án đã chọn</div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{selectedOpt.icon}</span>
                <span className="font-bold text-gray-800">{selectedOpt.label}</span>
                {(selectedOpt as any).rec && <Pill tone="green">Khuyến nghị</Pill>}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[['Tấm pin',`${selectedOpt.panels} tấm`],['MWh/năm',`${selectedOpt.mwh}`],['Chi phí',`${selectedOpt.cost}M`],['Kiểm thử',selectedOpt.stress]].map(([l,v]) => (
                  <div key={l} className="bg-gray-50 rounded-lg p-2">
                    <div className="text-gray-400 text-[10px]">{l}</div>
                    <div className="font-bold text-gray-800">{v}</div>
                  </div>
                ))}
              </div>
            </Card>

            <button onClick={onNext}
              className="w-full text-white font-semibold py-3 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
              style={{ background: G }}>
              → Bàn giao phương án
            </button>
            <div className="text-[10px] text-gray-400 text-center">Chuyển sang bước 5: Bàn giao</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Version History Modal ────────────────────────────────────────────────────

const VERSION_HISTORY = [
  {
    v: 'v1', label: 'Phân tích ban đầu', time: '09:15 · 18/04/2024', status: 'archived',
    change: 'Nhập ảnh drone + phân tích AI. Phát hiện 4 vật cản.',
    panels: 0, mwh: '—', cost: '—', tests: '—',
  },
  {
    v: 'v2', label: 'Thiết kế Cân bằng', time: '10:24 · 18/04/2024', status: 'approved',
    change: 'Hoàn thành bố trí 17 tấm pin, né vật cản, vượt 8/8 kịch bản kiểm thử.',
    panels: 17, mwh: '14.32', cost: '71.4M', tests: '8/8',
  },
  {
    v: 'v3', label: 'Tự phục hồi', time: '10:41 · 18/04/2024', status: 'current',
    change: 'Bồn nước tăng 1.2m→1.8m. Hệ thống tái tối ưu cục bộ: 17→14 tấm, bóng che cập nhật.',
    panels: 14, mwh: '11.79', cost: '63.2M', tests: '8/8',
  },
]

function VersionHistoryModal({ onClose, onExport }: { onClose: () => void; onExport: () => void }) {
  const [compareA, setCompareA] = useState<string | null>(null)
  const [compareB, setCompareB] = useState<string | null>(null)

  const vA = VERSION_HISTORY.find(v => v.v === compareA)
  const vB = VERSION_HISTORY.find(v => v.v === compareB)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.45)' }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <div className="font-bold text-gray-900 text-lg">Lịch sử phiên bản</div>
            <div className="text-xs text-gray-400 mt-0.5">Mỗi thay đổi quan trọng được lưu thành phiên bản độc lập.</div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onExport}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white flex items-center gap-1.5"
              style={{ background: G }}>
              📄 Xuất báo cáo
            </button>
            <button onClick={onClose} className="w-8 h-8 rounded-lg bg-gray-100 text-gray-500 flex items-center justify-center text-lg font-light hover:bg-gray-200">✕</button>
          </div>
        </div>

        {/* Timeline */}
        <div className="px-6 py-4 space-y-3">
          <div className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-2">Chọn 2 phiên bản để so sánh</div>
          {VERSION_HISTORY.map((ver, i) => {
            const isSel = compareA === ver.v || compareB === ver.v
            const toggle = () => {
              if (compareA === ver.v) { setCompareA(null); return }
              if (compareB === ver.v) { setCompareB(null); return }
              if (!compareA) { setCompareA(ver.v); return }
              if (!compareB) { setCompareB(ver.v); return }
              setCompareA(ver.v); setCompareB(null)
            }
            const badgeColor = ver.status === 'current' ? 'bg-green-100 text-green-700 border-green-300'
              : ver.status === 'approved' ? 'bg-blue-50 text-blue-600 border-blue-200'
              : 'bg-gray-100 text-gray-500 border-gray-200'
            return (
              <div key={ver.v} className="flex gap-3">
                {/* Timeline spine */}
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-xs font-bold cursor-pointer transition-all ${isSel ? 'bg-green-600 border-green-600 text-white' : 'bg-white border-gray-300 text-gray-600 hover:border-green-400'}`}
                    onClick={toggle}>
                    {isSel ? '✓' : ver.v}
                  </div>
                  {i < VERSION_HISTORY.length - 1 && <div className="w-0.5 flex-1 bg-gray-200 my-1 min-h-[24px]" />}
                </div>
                {/* Card */}
                <div onClick={toggle} className={`flex-1 mb-2 p-3 rounded-xl border cursor-pointer transition-all ${isSel ? 'border-green-300 bg-green-50' : 'border-gray-200 hover:border-gray-300 bg-white'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-gray-800 text-sm">{ver.label}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${badgeColor}`}>
                      {ver.status === 'current' ? 'Hiện tại' : ver.status === 'approved' ? 'Đã duyệt' : 'Lưu trữ'}
                    </span>
                    <span className="text-[10px] text-gray-400 ml-auto font-mono">{ver.time}</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{ver.change}</p>
                  {ver.panels > 0 && (
                    <div className="flex gap-3 text-[10px] font-mono">
                      <span className="text-gray-600">📋 {ver.panels} tấm</span>
                      <span className="text-amber-600">⚡ {ver.mwh} MWh/năm</span>
                      <span className="text-gray-600">💰 {ver.cost} VND</span>
                      <span className="text-green-600">🛡 {ver.tests} kiểm thử</span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Compare diff panel */}
        {vA && vB && (
          <div className="mx-6 mb-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
            <div className="text-xs font-semibold text-gray-700 mb-3">So sánh {vA.v} ↔ {vB.v}</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {[
                ['Số tấm pin', `${vA.panels}`, `${vB.panels}`, 'tấm'],
                ['Sản lượng', vA.mwh, vB.mwh, 'MWh/năm'],
                ['Chi phí', vA.cost, vB.cost, 'VND'],
                ['Kiểm thử', vA.tests, vB.tests, ''],
              ].map(([label, a, b, unit]) => {
                const diff = parseFloat(b as string) - parseFloat(a as string)
                return (
                  <div key={label} className="col-span-3 grid grid-cols-3 items-center py-1.5 border-b border-gray-200 last:border-0">
                    <span className="text-gray-500">{label}</span>
                    <span className="text-center font-mono text-gray-700">{a} {unit}</span>
                    <div className="flex items-center justify-center gap-1.5">
                      <span className="font-mono text-gray-700">{b} {unit}</span>
                      {!isNaN(diff) && diff !== 0 && (
                        <span className={`text-[10px] font-semibold px-1 py-0.5 rounded ${diff < 0 ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'}`}>
                          {diff > 0 ? '+' : ''}{diff.toFixed(diff % 1 === 0 ? 0 : 2)}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Export Report Modal ──────────────────────────────────────────────────────

function ExportReportModal({ onClose }: { onClose: () => void }) {
  const [printing, setPrinting] = useState(false)

  const handlePrint = () => {
    setPrinting(true)
    setTimeout(() => { window.print(); setPrinting(false) }, 200)
  }

  const sections = [
    { icon: '📍', title: 'Thông tin công trình', rows: [
      ['Địa chỉ', '123 Đường Nguyễn Huệ, Quận 1, TP.HCM'],
      ['Kích thước mái (phủ bì)', '10 × 8 m = 80 m²'],
      ['Chiều cao lan can', '1.1 m'],
      ['Lối đi bảo trì / an toàn', '0.8 m (rộng)'],
      ['Hướng mái', 'Nam (178°)'],
      ['Độ nghiêng', 'Phẳng (0°)'],
      ['Ngày khảo sát', '18/04/2024'],
    ]},
    { icon: '🔍', title: 'Phân tích AI – Vật cản', rows: [
      ['Bồn nước inox', 'Ø 1.5 m (1.77 m²) · Cao 1.20 m · Ảnh hưởng: Cao'],
      ['Ống thông gió (×2)', 'Ø 0.15 m · Cao 0.4 m · Ảnh hưởng: TB'],
      ['Dàn nóng điều hòa', '0.90 × 0.70 m · Cao 0.8 m · Ảnh hưởng: Cao'],
      ['Vật thể A (chưa xác định)', '~0.8 × 0.5 m · Ảnh hưởng: Thấp'],
    ]},
    { icon: '⚖️', title: 'Phương án được chọn: Cân bằng (v3)', rows: [
      ['Số tấm pin', '14 tấm · LONGi Hi-MO 6 580W'],
      ['Điện năng dự kiến', '11.79 MWh/năm'],
      ['Công suất hệ thống', '8.12 kWp'],
      ['Diện tích mái dùng', '41.8 m²'],
      ['Chi phí ước tính', '63.2 triệu VND'],
      ['Hoàn vốn ước tính', '5.2 năm'],
      ['Tỷ lệ qua kiểm thử', '8/8 (100%)'],
    ]},
    { icon: '💰', title: 'Phân tích tài chính (25 năm)', rows: [
      ['Sản lượng tích lũy (25 năm)', '~265 MWh'],
      ['Tiết kiệm điện (25 năm)', '~265 triệu VND'],
      ['IRR ước tính', '~18.5% / năm'],
      ['Lợi nhuận ròng (NPV)', '~142 triệu VND'],
    ]},
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 sticky top-0 bg-white z-10">
          <div>
            <div className="font-bold text-gray-900 text-lg">Xuất báo cáo thiết kế</div>
            <div className="text-xs text-gray-400 mt-0.5">SolarOpt · Phiên bản v3 · 18/04/2024</div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handlePrint} disabled={printing}
              className="px-4 py-2 rounded-lg text-sm font-semibold text-white flex items-center gap-2 disabled:opacity-60"
              style={{ background: G }}>
              {printing ? '⟳ Đang xuất...' : '🖨 In / Tải PDF'}
            </button>
            <button onClick={onClose} className="w-8 h-8 rounded-lg bg-gray-100 text-gray-500 flex items-center justify-center text-lg font-light hover:bg-gray-200">✕</button>
          </div>
        </div>

        {/* Report preview */}
        <div className="px-6 py-5 space-y-5 print:px-0">
          {/* Letterhead */}
          <div className="flex items-center justify-between pb-4 border-b-2 border-green-600">
            <div>
              <div className="text-xl font-black text-green-700 tracking-tight">☀ SolarOpt</div>
              <div className="text-xs text-gray-400">Báo cáo thiết kế hệ thống điện mặt trời áp mái</div>
            </div>
            <div className="text-right text-xs text-gray-400 font-mono">
              <div>Số hiệu: SO-2024-0418-CB</div>
              <div>Ngày phát hành: 18/04/2024</div>
              <div>Kỹ sư duyệt: AI + Review</div>
            </div>
          </div>

          {/* Sections */}
          {sections.map(sec => (
            <div key={sec.title}>
              <div className="flex items-center gap-2 mb-2">
                <span>{sec.icon}</span>
                <span className="text-sm font-bold text-gray-800">{sec.title}</span>
              </div>
              <div className="bg-gray-50 rounded-xl overflow-hidden border border-gray-100">
                {sec.rows.map(([k, v], i) => (
                  <div key={k} className={`grid grid-cols-[180px_1fr] gap-2 px-4 py-2 text-xs ${i % 2 === 0 ? 'bg-white' : ''}`}>
                    <span className="text-gray-500">{k}</span>
                    <span className="text-gray-800 font-medium">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Stress test summary */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span>🛡</span>
              <span className="text-sm font-bold text-gray-800">Kết quả kiểm thử (8/8)</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                ['Base geometry', true],['Winter low sun', true],['Tank +20 cm', true],['Tank +30 cm', true],
                ['Morning low sun', true],['Afternoon low sun', true],['Panel tolerance', true],['Field variance', true],
              ].map(([name, pass]) => (
                <div key={name as string} className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs">
                  <span className="text-green-600">✓</span>
                  <span className="text-gray-700">{name as string}</span>
                  <span className="ml-auto text-green-700 font-semibold">Đạt</span>
                </div>
              ))}
            </div>
          </div>

          {/* Footer disclaimer */}
          <div className="text-[10px] text-gray-400 border-t border-gray-100 pt-4 leading-relaxed">
            Báo cáo này được tạo tự động bởi SolarOpt dựa trên dữ liệu ảnh drone và phân tích AI. Kết quả mang tính ước tính và cần được kỹ sư có chứng chỉ xem xét trước khi thi công. Sản lượng thực tế có thể thay đổi tùy theo điều kiện thời tiết và chất lượng thi công.
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Step 5: Tự phục hồi ─────────────────────────────────────────────────────

function Step5() {
  const [recovering, setRecovering] = useState(false)
  const [done, setDone] = useState(false)
  const [logLines, setLogLines] = useState<string[]>([])
  const [progress, setProgress] = useState(0)
  const [showVersions, setShowVersions] = useState(false)
  const [showExport, setShowExport] = useState(false)

  const LOG_SCRIPT = [
    '10:41 &nbsp;&nbsp;Phát hiện thay đổi: Chiều cao bồn nước 1.2 m → 1.8 m',
    '10:41 &nbsp;&nbsp;Kiểm thử thất bại ở 3 hạng mục (bóng che, sản lượng, chi phí)',
    '10:41 &nbsp;&nbsp;Bắt đầu tự động sửa chữa (auto-repair)',
    '10:41 &nbsp;&nbsp;Hoàn tất: 6 thao tác thay đổi, 13 vị trí giữ nguyên',
    '10:41 &nbsp;&nbsp;Kiểm tra lại: Đạt 8/8 ✓',
  ]

  const startRecovery = () => {
    setRecovering(true)
    setLogLines([])
    setProgress(0)
    let i = 0
    const tick = setInterval(() => {
      setProgress(p => Math.min(p + 22, 100))
      if (i < LOG_SCRIPT.length) {
        setLogLines(l => [...l, LOG_SCRIPT[i]])
        i++
      } else {
        clearInterval(tick)
        setDone(true)
      }
    }, 700)
  }

  const impactNodes = [
    { label:'Chiều cao\nvật cản', affected: true },
    { label:'Bóng che', affected: true },
    { label:'Bố trí', affected: true },
    { label:'Sản lượng', affected: true },
    { label:'Chi phí / ROI', affected: true },
  ]

  return (
    <div className="animate-fade-up">
      <div className="max-w-6xl mx-auto px-6 py-5 space-y-5">
        {/* Change banner */}
        <div className="flex items-center gap-4 bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="bg-amber-100 border border-amber-300 rounded-lg px-3 py-1.5 text-center shrink-0">
            <div className="text-[10px] text-amber-600">Thay đổi hiện trạng</div>
            <div className="text-sm font-bold text-amber-800">Chiều cao bồn nước 1.2 m → 1.8 m</div>
          </div>
          <div className="flex-1">
            <p className="text-xs text-amber-700">SolarOpt duy trì đồ thị phụ thuộc từ dữ liệu đầu vào và ràng buộc đến các vị trí khả thi, bố trí, sản lượng và chi phí, nên khi có thay đổi chỉ tái tối ưu phần liên quan.</p>
          </div>
          <button className="text-xs text-amber-700 font-semibold hover:underline shrink-0 flex items-center gap-1">
            Xem chi tiết <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
          </button>
        </div>

        {/* Version selectors */}
        <div className="grid grid-cols-2 gap-4">
          {[{v:'v2',label:'Trước thay đổi',time:'10:24 · 18/04/2024'},{v:'v3',label:'Sau thay đổi',time:'10:41 · 18/04/2024'}].map(ver => (
            <div key={ver.v} className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl p-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 border border-gray-300 flex items-center justify-center font-mono font-bold text-xs text-gray-600">{ver.v}</div>
              <div>
                <div className="font-semibold text-gray-800 text-sm">{ver.label}</div>
                <div className="text-xs text-gray-400">Tạo lúc {ver.time}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Main 3-column layout */}
        <div className="grid grid-cols-[1fr_280px_1fr] gap-4">
          {/* Before (v2) */}
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 p-3 border-b border-gray-100">
              <div className="w-6 h-6 rounded bg-gray-200 flex items-center justify-center font-mono text-[10px] font-bold text-gray-600">v2</div>
              <span className="text-sm font-semibold text-gray-700">Trước thay đổi</span>
            </div>
            <div className="relative bg-gray-800" style={{ aspectRatio: '4/3' }}>
              <AerialSVG mode="design" panelList={PANELS_17} />
              <div className="absolute bottom-1 left-2 text-[9px] text-white/70 font-mono">Digital Roof · v2</div>
              <div className="absolute top-2 right-2">
                <button className="w-6 h-6 bg-white/80 rounded text-gray-600 flex items-center justify-center">⤢</button>
              </div>
              {/* North */}
              <div className="absolute top-2 left-2 bg-white/80 rounded-full w-8 h-8 flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-5 h-5">
                  <polygon points="12,2 15,12 12,10 9,12" fill="#16a34a"/>
                  <polygon points="12,22 15,12 12,14 9,12" fill="#9ca3af"/>
                  <text x="12" y="7" textAnchor="middle" fontSize="5" fontWeight="700" fill="#111">N</text>
                </svg>
              </div>
            </div>
            <div className="p-3 grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📋</span>
                <div><div className="text-gray-400 text-[10px]">Số tấm</div><div className="font-bold text-gray-800">17 tấm</div></div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-amber-500">⚡</span>
                <div><div className="text-gray-400 text-[10px]">Sản lượng dự kiến</div><div className="font-bold text-gray-800">14.32 MWh/năm</div></div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">💰</span>
                <div><div className="text-gray-400 text-[10px]">Chi phí ước tính</div><div className="font-bold text-gray-800">71.4 triệu VND</div></div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-600">🛡</span>
                <div><div className="text-gray-400 text-[10px]">Kiểm thử</div><div className="font-bold text-gray-800">8/8 đạt</div></div>
              </div>
            </div>
          </Card>

          {/* Trace impact */}
          <div className="space-y-3">
            <Card className="p-4">
              <div className="font-semibold text-gray-800 text-sm mb-1">Trace Impact</div>
              <div className="text-xs text-gray-500 mb-4">Hệ thống lần theo đồ thị phụ thuộc để xác định chính xác những phần bị ảnh hưởng.</div>
              <div className="flex flex-col items-center gap-2">
                {impactNodes.map((n, i) => (
                  <div key={i} className="flex flex-col items-center">
                    <div className={`px-3 py-2 rounded-xl border text-center text-xs font-semibold w-full ${n.affected ? 'bg-red-50 border-red-300 text-red-700' : 'bg-gray-50 border-gray-200 text-gray-500'}`}>
                      <div className="flex items-center justify-center gap-1">
                        {n.affected && <span className="text-red-500">⚠</span>}
                        <span>{n.label.replace('\n', ' ')}</span>
                      </div>
                    </div>
                    {i < impactNodes.length-1 && <div className="w-0.5 h-3 bg-red-300" />}
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-semibold text-gray-700">Nhật ký xử lý thay đổi</div>
                {done && <Pill tone="green">✓ Hoàn tất · 38 giây</Pill>}
              </div>
              <div className="space-y-1 min-h-[100px]">
                {logLines.map((l, i) => (
                  <div key={i} className={`flex gap-1.5 text-[10px] font-mono animate-fade-in ${i===logLines.length-1 && done ? 'text-green-700 font-semibold' : 'text-gray-600'}`}>
                    <span className={i===logLines.length-1 && done ? 'text-green-600' : 'text-green-500'}>✓</span>
                    <span dangerouslySetInnerHTML={{__html: l}} />
                  </div>
                ))}
                {recovering && !done && (
                  <div className="flex gap-1.5 text-[10px] font-mono text-gray-400">
                    <span className="animate-spin">⟳</span><span>Đang xử lý...</span>
                  </div>
                )}
                {!recovering && !done && (
                  <div className="text-[10px] text-gray-400 text-center pt-4">Nhấn nút bên dưới để chạy tự phục hồi</div>
                )}
              </div>
              {done && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-2 mt-2">
                  <p className="text-[10px] text-green-700">💡 Chỉ 5/12 nhóm thành phần bị ảnh hưởng. SolarOpt tái tối ưu cục bộ thay vì chạy lại toàn bộ.</p>
                </div>
              )}
              {!done && (
                <button onClick={startRecovery} disabled={recovering}
                  className="w-full mt-3 text-white font-semibold py-2 rounded-lg text-xs transition-colors disabled:opacity-50"
                  style={{ background: recovering ? '#6b7280' : '#d97706' }}>
                  {recovering ? '⟳ Đang tự phục hồi...' : '▶ Chạy tự phục hồi'}
                </button>
              )}
            </Card>
          </div>

          {/* After (v3) */}
          <Card className={`overflow-hidden transition-all ${done ? '' : 'opacity-40'}`}>
            <div className="flex items-center gap-2 p-3 border-b border-gray-100">
              <div className="w-6 h-6 rounded bg-green-200 flex items-center justify-center font-mono text-[10px] font-bold text-green-700">v3</div>
              <span className="text-sm font-semibold text-gray-700">Sau tự phục hồi</span>
            </div>
            <div className="relative bg-gray-800" style={{ aspectRatio: '4/3' }}>
              <AerialSVG mode="design" panelList={PANELS_15} />
              <div className="absolute bottom-1 left-2 text-[9px] text-white/70 font-mono">Digital Roof · v3</div>
              {done && <div className="absolute inset-0 flex items-center justify-center">
                <div className="bg-green-600/20 border border-green-500 rounded-xl px-4 py-2 text-green-300 text-xs font-semibold animate-fade-in">Auto-repaired ✓</div>
              </div>}
            </div>
            <div className="p-3 grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📋</span>
                <div><div className="text-gray-400 text-[10px]">Số tấm</div><div className={`font-bold ${done?'text-gray-800':'text-gray-300'}`}>14 tấm</div></div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-amber-500">⚡</span>
                <div><div className="text-gray-400 text-[10px]">Sản lượng dự kiến</div><div className={`font-bold ${done?'text-gray-800':'text-gray-300'}`}>11.79 MWh/năm</div></div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">💰</span>
                <div><div className="text-gray-400 text-[10px]">Chi phí ước tính</div><div className={`font-bold ${done?'text-gray-800':'text-gray-300'}`}>63.2 triệu VND</div></div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-600">🛡</span>
                <div><div className="text-gray-400 text-[10px]">Kiểm thử</div><div className={`font-bold ${done?'text-gray-800':'text-gray-300'}`}>8/8 đạt</div></div>
              </div>
            </div>
          </Card>
        </div>

        {/* Bottom note */}
        <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl p-4">
          <span className="text-xl">🔗</span>
          <div>
            <div className="font-semibold text-gray-800 text-sm">SolarOpt không chạy lại toàn bộ quy trình;</div>
            <div className="text-xs text-gray-500">hệ thống lần theo đồ thị phụ thuộc để chỉ tái tối ưu phần liên quan. Cách tiếp cận này giúp tiết kiệm thời gian tính toán, đồng thời đảm bảo kết quả nhất quán và đáng tin cậy.</div>
          </div>
          <div className="ml-auto flex gap-2 shrink-0">
            <button onClick={() => setShowVersions(true)}
              className="text-white font-semibold py-2 px-4 rounded-xl text-sm whitespace-nowrap flex items-center gap-2 hover:opacity-90 transition-opacity"
              style={{ background: '#1e3a5f' }}>
              🕐 Xem phiên bản
            </button>
            <button onClick={() => setShowExport(true)}
              className="text-white font-semibold py-2 px-4 rounded-xl text-sm whitespace-nowrap flex items-center gap-2 hover:opacity-90 transition-opacity"
              style={{ background: G }}>
              📄 Xuất báo cáo
            </button>
          </div>
        </div>
      </div>

      {showVersions && (
        <VersionHistoryModal
          onClose={() => setShowVersions(false)}
          onExport={() => { setShowVersions(false); setShowExport(true) }}
        />
      )}
      {showExport && <ExportReportModal onClose={() => setShowExport(false)} />}
    </div>
  )
}

// ─── Header ───────────────────────────────────────────────────────────────────

function Header({ step, setStep }: { step: AppStep; setStep: (s: AppStep) => void }) {
  const steps: { n: AppStep; label: string }[] = [
    { n:1, label:'Thiết lập' },
    { n:2, label:'Hợp nhất dữ liệu' },
    { n:3, label:'Thiết kế' },
    { n:4, label:'Kiểm chứng' },
    { n:5, label:'Bàn giao' },
  ]

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200 h-14 flex items-center px-5 gap-6">
      {/* Logo */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: G }}>
          <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div className="font-bold text-gray-900 text-sm leading-tight">SolarOpt</div>
          <div className="text-[9px] text-gray-400 leading-tight">Tối ưu hôm nay, năng lượng ngày mai</div>
        </div>
      </div>

      {/* Step breadcrumb */}
      <div className="flex-1 flex items-center justify-center gap-0">
        {steps.map((s, i) => (
          <div key={s.n} className="flex items-center">
            <button
              onClick={() => setStep(s.n)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-gray-50"
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors ${
                step === s.n ? 'text-white' : step > s.n ? 'border-2 border-green-600 text-green-700' : 'bg-gray-100 text-gray-400'
              }`} style={step === s.n ? { background: G } : {}}>
                {step > s.n ? '✓' : s.n}
              </div>
              <span className={`text-xs font-medium ${step === s.n ? 'text-gray-800' : step > s.n ? 'text-green-700' : 'text-gray-400'}`}>
                {s.label}
              </span>
            </button>
            {i < steps.length-1 && <div className="w-6 h-px bg-gray-200 mx-0.5" />}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <button className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 border border-gray-200 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          Hướng dẫn
        </button>
        <button className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 border border-gray-200 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" /></svg>
          Lưu nháp
        </button>
      </div>
    </header>
  )
}

// ─── Page title block ─────────────────────────────────────────────────────────

function PageTitle({ step }: { step: AppStep }) {
  const meta: Record<AppStep, { badge: string; title: string; sub: string; tip: string }> = {
    1: { badge: 'BƯỚC 1 · THIẾT LẬP', title: 'Tạo dự án thiết kế điện mặt trời', sub: 'SolarOpt sử dụng bản vẽ kỹ thuật, ảnh chụp từ trên xuống và ảnh hiện trường để tạo mô hình Digital Roof chính xác, phục vụ thiết kế và tối ưu hệ thống điện mặt trời.', tip: 'Biến dữ liệu thực tế thành thiết kế tối ưu' },
    2: { badge: 'BƯỚC 2 · HỢP NHẤT DỮ LIỆU', title: 'Tạo Digital Roof từ nhiều nguồn dữ liệu', sub: 'SolarOpt tự động căn chỉnh và hợp nhất bản vẽ, ảnh từ trên xuống và ảnh hiện trường để tạo mô hình Digital Roof chính xác.', tip: 'Một mô hình chính xác là nền tảng cho thiết kế tối ưu' },
    3: { badge: 'BƯỚC 3 · THIẾT KẾ', title: 'Thiết kế bố trí có thể giải thích', sub: 'Sắp xếp tấm pin trên mô hình mái, tự động tối ưu theo bức xạ, bóng che và các ràng buộc thực tế.', tip: 'Thiết kế thông minh · Dễ hiểu. Dễ kiểm chứng.' },
    4: { badge: 'BƯỚC 4 · KIỂM CHỨNG', title: 'Kỹ sư duyệt các phương án đã kiểm chứng', sub: 'So sánh kết quả kiểm chứng của các phương án thiết kế, đánh giá ưu nhược điểm và chọn phương án phù hợp để bàn giao.', tip: 'Kiểm chứng tự động · Kỹ sư duyệt lần cuối' },
    5: { badge: 'BƯỚC 5 · TỰ PHỤC HỒI', title: 'Khi dự án thay đổi, SolarOpt chỉ tính lại phần bị ảnh hưởng', sub: 'SolarOpt duy trì đồ thị phụ thuộc từ dữ liệu đầu vào và ràng buộc đến các vị trí khả thi, bố trí, sản lượng và chi phí, nên khi có thay đổi chỉ tái tối ưu phần liên quan.', tip: 'Thay đổi nhỏ → chỉ cập nhật phần liên quan' },
  }
  const m = meta[step]

  return (
    <div className="bg-white border-b border-gray-100 px-6 py-5">
      <div className="max-w-6xl mx-auto flex items-start justify-between gap-6">
        <div className="flex-1">
          <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-1">{m.badge}</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1.5">{m.title}</h1>
          <p className="text-sm text-gray-500 leading-relaxed max-w-2xl">{m.sub}</p>
        </div>
        <div className="shrink-0 flex items-center gap-3 bg-green-50 border border-green-100 rounded-xl px-4 py-3">
          <svg viewBox="0 0 48 48" className="w-12 h-12 shrink-0">
            <rect x="4" y="26" width="40" height="18" fill="#d1fae5" rx="3"/>
            <polygon points="24,4 44,26 4,26" fill="#6ee7b7"/>
            <rect x="22" y="34" width="8" height="10" fill="#a7f3d0"/>
            {/* Solar panels */}
            <rect x="8" y="14" width="8" height="5" fill="#1e40af" rx="0.5" opacity="0.8"/>
            <rect x="18" y="10" width="8" height="5" fill="#1e40af" rx="0.5" opacity="0.8"/>
            <rect x="28" y="10" width="8" height="5" fill="#1e40af" rx="0.5" opacity="0.8"/>
          </svg>
          <div className="text-xs text-green-700 font-medium max-w-[140px] leading-snug">{m.tip}</div>
        </div>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [step, setStep] = useState<AppStep>(1)
  const [tabImages, setTabImages] = useState<Array<{image: string | null, name: string | null}>>([
    {image: null, name: null},
    {image: null, name: null},
    {image: null, name: null},
  ])
  const [obsPos, setObsPos] = useState<Record<string, {cx: number, cy: number}>>(() =>
    Object.fromEntries(OBS.map(o => [o.id, {cx: o.cx, cy: o.cy}]))
  )

  const handleImageUpload = (tabIdx: number, img: string, name: string) => {
    setTabImages(prev => prev.map((t, i) => i === tabIdx ? {image: img || null, name: name || null} : t))
  }

  const handleObsMove = (id: string, cx: number, cy: number) => {
    setObsPos(prev => ({...prev, [id]: {cx, cy}}))
  }

  return (
    <div className="min-h-screen bg-[#f4f6f3]">
      <Header step={step} setStep={setStep} />
      <PageTitle step={step} />
      {step === 1 && <Step1 onNext={() => setStep(2)} onImageUpload={handleImageUpload} tabImages={tabImages} />}
      {step === 2 && <Step2 onNext={() => setStep(3)} tabImages={tabImages} obsPos={obsPos} onObsMove={handleObsMove} />}
      {step === 3 && <Step3 onNext={() => setStep(4)} />}
      {step === 4 && <Step4 onNext={() => setStep(5)} />}
      {step === 5 && <Step5 />}
    </div>
  )
}
