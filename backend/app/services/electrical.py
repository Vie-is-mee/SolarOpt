"""Electrical design for a placed layout: string sizing, inverter choice, limit checks and a bill of materials.

Temperatures move the string voltage: the coldest morning gives the highest open-circuit voltage (the
inverter's DC limit), the hottest cell gives the lowest MPP voltage (the bottom of the MPPT window).
Panels are wired per roof orientation, so one MPPT never mixes faces that see the sun differently.
Catalogue figures are reference values from the makers' datasheets; prices are planning assumptions.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import CandidatePanel, DesignResult, PanelSpec, ProjectConfig, StrictModel
from app.services.geometry import SLOPED_TILT

Phase = Literal["single", "three"]


class InverterSpec(StrictModel):
    id: str = Field(min_length=1, max_length=60)
    manufacturer: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=80)
    phase: Phase = "single"
    ac_rated_w: float = Field(gt=0, le=500_000)
    max_dc_power_w: float = Field(gt=0, le=1_000_000)
    max_dc_voltage_v: float = Field(gt=0, le=1500)
    mppt_min_v: float = Field(gt=0, le=1500)
    mppt_max_v: float = Field(gt=0, le=1500)
    start_voltage_v: float = Field(gt=0, le=1500)
    mppt_count: int = Field(ge=1, le=20)
    strings_per_mppt: int = Field(ge=1, le=8)
    max_current_per_mppt_a: float = Field(gt=0, le=200)
    max_short_circuit_per_mppt_a: float = Field(gt=0, le=300)
    price_vnd: float = Field(ge=0, le=1e10)
    source: str = Field(default="Kỹ sư nhập theo datasheet", max_length=300)


def _inv(id, maker, model, phase, ac, dc, vmax, lo, hi, start, mppts, per, imax, isc, price, source):
    return InverterSpec(id=id, manufacturer=maker, model=model, phase=phase, ac_rated_w=ac, max_dc_power_w=dc,
                        max_dc_voltage_v=vmax, mppt_min_v=lo, mppt_max_v=hi, start_voltage_v=start, mppt_count=mppts,
                        strings_per_mppt=per, max_current_per_mppt_a=imax, max_short_circuit_per_mppt_a=isc,
                        price_vnd=price, source=source)


HUAWEI_L1 = "Huawei FusionSolar, trang thông số SUN2000-2/3/4/5/6KTL-L1"
CATALOG: list[InverterSpec] = [
    _inv("huawei-3ktl-l1", "Huawei", "SUN2000-3KTL-L1", "single", 3000, 4500, 600, 90, 560, 100, 2, 1, 12.5, 18, 13_500_000, HUAWEI_L1),
    _inv("huawei-5ktl-l1", "Huawei", "SUN2000-5KTL-L1", "single", 5000, 7500, 600, 90, 560, 100, 2, 1, 12.5, 18, 17_000_000, HUAWEI_L1),
    _inv("huawei-6ktl-l1", "Huawei", "SUN2000-6KTL-L1", "single", 6000, 9000, 600, 90, 560, 100, 2, 1, 12.5, 18, 19_000_000, HUAWEI_L1),
    _inv("growatt-min-6000tl-x", "Growatt", "MIN 6000TL-X", "single", 6000, 9000, 550, 80, 550, 100, 2, 1, 13.5, 16.9, 13_500_000,
         "Growatt, datasheet MIN 2500-6000TL-X (bản dòng 13,5 A)"),
    _inv("solis-s6-gr1p5k-s", "Solis", "S6-GR1P5K-S", "single", 5000, 7500, 550, 90, 550, 120, 2, 1, 16, 22, 12_500_000,
         "Solis, datasheet S6-GR1P(4-5)K-S 2024"),
    _inv("huawei-10ktl-m1-hc", "Huawei", "SUN2000-10KTL-M1 (High Current)", "three", 10000, 15000, 1100, 140, 980, 200, 2, 1, 13.5, 19.5, 30_000_000,
         "Huawei FusionSolar, thông số SUN2000-3-10KTL-M1 bản High Current"),
    _inv("huawei-20ktl-m2", "Huawei", "SUN2000-20KTL-M2", "three", 20000, 30000, 1080, 160, 950, 200, 2, 2, 22, 30, 45_000_000,
         "Huawei FusionSolar, thông số SUN2000-12-20KTL-M2"),
    # Three-phase range for larger homes, shops and factories (planning prices; check the current datasheet revision).
    _inv("huawei-8ktl-m1", "Huawei", "SUN2000-8KTL-M1", "three", 8000, 12000, 1100, 140, 980, 200, 2, 1, 11, 15, 26_000_000,
         "Huawei FusionSolar, thông số SUN2000-3-10KTL-M1"),
    _inv("growatt-mod-10ktl3-x", "Growatt", "MOD 10KTL3-X", "three", 10000, 15000, 1100, 140, 1000, 160, 2, 1, 13, 16, 20_000_000,
         "Growatt, datasheet MOD 3-15KTL3-X"),
    _inv("huawei-12ktl-m2", "Huawei", "SUN2000-12KTL-M2", "three", 12000, 18000, 1080, 160, 950, 200, 2, 2, 22, 30, 36_000_000,
         "Huawei FusionSolar, thông số SUN2000-12-20KTL-M2"),
    _inv("huawei-15ktl-m2", "Huawei", "SUN2000-15KTL-M2", "three", 15000, 22500, 1080, 160, 950, 200, 2, 2, 22, 30, 40_000_000,
         "Huawei FusionSolar, thông số SUN2000-12-20KTL-M2"),
    _inv("huawei-30ktl-m3", "Huawei", "SUN2000-30KTL-M3", "three", 30000, 45000, 1100, 200, 1000, 200, 4, 2, 26, 40, 60_000_000,
         "Huawei FusionSolar, thông số SUN2000-30/36/40KTL-M3"),
    _inv("huawei-40ktl-m3", "Huawei", "SUN2000-40KTL-M3", "three", 40000, 60000, 1100, 200, 1000, 200, 4, 2, 26, 40, 72_000_000,
         "Huawei FusionSolar, thông số SUN2000-30/36/40KTL-M3"),
    _inv("sungrow-sg50cx", "Sungrow", "SG50CX", "three", 50000, 75000, 1100, 200, 1000, 250, 5, 2, 26, 40, 85_000_000,
         "Sungrow, datasheet SG33/40/50CX"),
    _inv("huawei-100ktl-m1", "Huawei", "SUN2000-100KTL-M1", "three", 100000, 150000, 1100, 200, 1000, 200, 10, 2, 26, 40, 120_000_000,
         "Huawei FusionSolar, thông số SUN2000-100KTL-M1"),
    _inv("sungrow-sg110cx", "Sungrow", "SG110CX", "three", 110000, 165000, 1100, 200, 1000, 200, 9, 2, 26, 40, 135_000_000,
         "Sungrow, datasheet SG110CX"),
]
CATALOG.sort(key=lambda i: (i.phase != "single", i.ac_rated_w))
CATALOG_NOTE = "Thông số inverter lấy từ datasheet hãng để tham khảo; kỹ sư đối chiếu đúng phiên bản thiết bị mua. Giá là giả định lập kế hoạch, chưa phải báo giá."


class ElectricalRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    design: DesignResult
    inverter_id: str | None = Field(default=None, description="None picks the best catalogue inverter")
    custom_inverter: InverterSpec | None = None
    grid_phase: Literal["auto", "single", "three"] = "auto"
    min_ambient_c: float | None = Field(default=None, ge=-40, le=40, description="Coldest morning on site; from latitude when empty")
    max_ambient_c: float = Field(default=40, ge=10, le=60)
    cell_rise_c: float = Field(default=30, ge=0, le=50, description="Cell above ambient at full sun")
    voc_coeff_pct: float = Field(default=-0.27, ge=-1, le=0, description="Voc temperature coefficient, %/°C")
    vmp_coeff_pct: float = Field(default=-0.35, ge=-1, le=0, description="Vmp follows the Pmax coefficient, %/°C")
    isc_a: float | None = Field(default=None, gt=0, le=50, description="Datasheet Isc; Imp × 1.05 when empty")
    home_run_m: float = Field(default=15, ge=0, le=500, description="DC run from the array to the inverter, each polarity")
    ac_run_m: float = Field(default=20, ge=0, le=1000, description="Inverter to the main board")
    max_ac_kw: float | None = Field(default=None, gt=0, le=10_000, description="Grid connection limit (approved or contracted AC capacity)")


class StringPlan(BaseModel):
    id: str
    inverter: int
    mppt: int
    face_id: str
    orientation: str
    panel_ids: list[str]
    length: int
    voc_cold_v: float
    vmp_hot_v: float
    vmp_cold_v: float
    imp_a: float
    shading_spread_pct: float
    cable_m: float


class MpptPlan(BaseModel):
    inverter: int
    mppt: int
    strings: list[str]
    current_a: float
    short_circuit_a: float


class ElectricalCheck(BaseModel):
    id: str
    label: str
    status: Literal["PASS", "WARN", "FAIL"]
    detail: str


class BomItem(BaseModel):
    group: Literal["panel", "inverter", "dc", "ac", "earthing", "mounting"]
    name: str
    spec: str
    quantity: float
    unit: str
    unit_price_vnd: float
    amount_vnd: float


class InverterOption(BaseModel):
    inverter_id: str
    label: str
    phase: Phase = "single"
    ac_kw: float = 0
    count: int
    dc_ac_ratio: float
    feasible: bool
    price_vnd: float
    note: str


class ElectricalResult(BaseModel):
    valid: bool
    inverter: InverterSpec
    inverter_count: int
    phase: Phase
    dc_kwp: float
    ac_kw: float
    dc_ac_ratio: float
    string_min: int
    string_max: int
    strings: list[StringPlan]
    mppts: list[MpptPlan]
    unassigned_panel_ids: list[str]
    checks: list[ElectricalCheck]
    bom: list[BomItem]
    cost_by_group: dict[str, float]
    options: list[InverterOption]
    assumptions: list[str]
    summary: str


def vn(value: float, digits: int = 1) -> str:
    text = f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return text.rstrip("0").rstrip(",") if "," in text else text


def default_min_ambient(latitude: float) -> float:
    """Coldest early morning a string must survive: the North sees frost-near mornings, the South rarely below 15 °C."""
    lat = abs(latitude)
    return 2.0 if lat >= 20 else 8.0 if lat >= 16 else 15.0


# ---- orientation groups and wiring order -------------------------------------------------------

def _orientation(panel: CandidatePanel, config: ProjectConfig) -> tuple[str, str]:
    faces = {f.id: f for f in config.roof_faces}
    face = faces.get(panel.face_id)
    tilt, az = (face.tilt_deg, face.azimuth_deg) if face else (0.0, 180.0) if panel.face_id.startswith("top-") else (config.roof_tilt_deg, config.roof_azimuth_deg)
    if tilt <= SLOPED_TILT and config.mounting == "tilted_rack":
        tilt, az = config.rack_tilt_deg, config.rack_azimuth_deg
    if tilt <= SLOPED_TILT and config.mounting == "tracker":
        return "tracker", "trục xoay"
    if tilt <= SLOPED_TILT:
        return "flat", "nằm ngang"
    az = round(az / 5) * 5 % 360
    tilt = round(tilt)
    return f"{tilt}/{az}", f"nghiêng {tilt}°, hướng {az}°"


def _serpentine(panels: list[CandidatePanel]) -> tuple[list[CandidatePanel], int]:
    """Row by row, alternating direction, so consecutive panels in a string are neighbours."""
    if not panels:
        return [], 0
    tol = min(p.height_m for p in panels) * 0.5
    rows: list[list[CandidatePanel]] = []
    for p in sorted(panels, key=lambda p: p.y + p.height_m / 2):
        cy = p.y + p.height_m / 2
        if rows and abs(cy - (rows[-1][0].y + rows[-1][0].height_m / 2)) <= tol:
            rows[-1].append(p)
        else:
            rows.append([p])
    ordered: list[CandidatePanel] = []
    for i, row in enumerate(rows):
        row.sort(key=lambda p: p.x, reverse=bool(i % 2))
        ordered += row
    return ordered, len(rows)


def _centre(p: CandidatePanel) -> tuple[float, float]:
    return p.x + p.width_m / 2, p.y + p.height_m / 2


# ---- one inverter model, one count -------------------------------------------------------------

class _Plan:
    def __init__(self):
        self.strings: list[StringPlan] = []
        self.mppts: list[MpptPlan] = []
        self.unassigned: list[str] = []
        self.mixed: list[str] = []
        self.slots_short = False


def _voltages(req: ElectricalRequest, t_min: float):
    p = req.panel
    t_hot = req.max_ambient_c + req.cell_rise_c
    voc_cold = p.voc_v * (1 + req.voc_coeff_pct / 100 * (t_min - 25))
    vmp_hot = p.vmp_v * (1 + req.vmp_coeff_pct / 100 * (t_hot - 25))
    vmp_cold = p.vmp_v * (1 + req.vmp_coeff_pct / 100 * (t_min - 25))
    return voc_cold, vmp_hot, vmp_cold


def _range(inv: InverterSpec, voc_cold: float, vmp_hot: float, vmp_cold: float) -> tuple[int, int]:
    hi = min(math.floor(inv.max_dc_voltage_v / voc_cold), math.floor(inv.mppt_max_v / vmp_cold))
    lo = max(1, math.ceil(max(inv.mppt_min_v, inv.start_voltage_v) / vmp_hot))
    return lo, hi


def _wire(req: ElectricalRequest, inv: InverterSpec, count: int, groups, lo: int, hi: int, volts) -> _Plan:
    voc_cold, vmp_hot, vmp_cold = volts
    isc = req.isc_a or req.panel.imp_a * 1.05
    plan = _Plan()
    # Groups too small for a string of their own join the largest group (a mismatch loss, flagged).
    big = [g for g in groups if len(g[2]) >= lo]
    # No face holds a string on its own (a small hip roof): wire every face together and flag the mismatch.
    if not big and lo <= hi and sum(len(g[2]) for g in groups) >= lo:
        first = groups[0]
        merged = (first[0], "nhiều hướng mái", [p for g in groups for p in g[2]])
        plan.mixed += [g[1] for g in groups]
        groups, big = [merged], [merged]
    for key, label, members in groups:
        if len(members) < lo:
            if big and lo <= hi:
                max(big, key=lambda g: len(g[2]))[2].extend(members)
                plan.mixed.append(label)
            else:
                plan.unassigned += [m.id for m in members]
    # Strings per group: any count s with ceil(m/hi) <= s <= floor(m/lo) keeps every length inside [lo, hi].
    work = []
    for key, label, members in big:
        ordered, _ = _serpentine(members)
        m = len(ordered)
        least, most = math.ceil(m / hi), m // lo
        if lo > hi or least > most:
            plan.unassigned += [p.id for p in ordered]
            continue
        work.append([ordered, label, least, most])
    # One string per MPPT where possible (less mismatch, balanced inverters), but beyond one string per inverter
    # only while strings stay at least half the longest allowed: short strings run at a poor, low voltage.
    spare = count * inv.mppt_count - sum(w[2] for w in work)
    comfort = max(lo, math.ceil(hi / 2))
    while spare > 0:
        total = sum(w[2] for w in work)
        growable = [w for w in work if w[2] < w[3] and (total < count or len(w[0]) // (w[2] + 1) >= comfort)]
        if not growable:
            break
        max(growable, key=lambda w: len(w[0]) / w[2])[2] += 1
        spare -= 1
    made: list[StringPlan] = []
    for ordered, label, strings, _ in work:
        base, extra = divmod(len(ordered), strings)
        start = 0
        for length in [base + 1] * extra + [base] * (strings - extra):
            chunk = ordered[start:start + length]
            start += length
            # Panel leads (~1,2 m each pair) bridge neighbours; longer hops and both home runs need cable.
            jumpers = sum(max(0.0, math.dist(_centre(a), _centre(b)) - 1.2) for a, b in zip(chunk, chunk[1:]))
            losses = [p.shading_loss_pct for p in chunk]
            made.append(StringPlan(id=f"C{len(made) + 1}", inverter=0, mppt=0, face_id=chunk[0].face_id, orientation=label,
                                   panel_ids=[p.id for p in chunk], length=length, voc_cold_v=round(voc_cold * length, 1),
                                   vmp_hot_v=round(vmp_hot * length, 1), vmp_cold_v=round(vmp_cold * length, 1),
                                   imp_a=req.panel.imp_a, shading_spread_pct=round(max(losses) - min(losses), 1),
                                   cable_m=round(2 * req.home_run_m + jumpers, 1)))
    # Trackers in round-robin order (first MPPT of every inverter, then the second...) to balance inverters.
    free = [(i, m) for m in range(inv.mppt_count) for i in range(count)]
    # Parallel only within both the short-circuit limit and the working-current limit (+5 % tolerance).
    per = max(1, min(inv.strings_per_mppt, math.floor(inv.max_short_circuit_per_mppt_a / isc),
                     math.floor(inv.max_current_per_mppt_a * 1.05 / req.panel.imp_a)))
    queue = list(made)
    while queue:
        if not free:
            plan.slots_short = True
            plan.unassigned += [pid for s in queue for pid in s.panel_ids]
            break
        first = queue[0]
        # Only strings of the same orientation and length may share a tracker, and only when trackers run short.
        mates = [s for s in queue if s.orientation == first.orientation and s.length == first.length]
        take = 1 if len(free) >= len(queue) else min(per, len(mates))
        group = mates[:take]
        queue = [s for s in queue if s not in group]
        inv_i, mppt_i = free.pop(0)
        for s in group:
            s.inverter, s.mppt = inv_i, mppt_i
        plan.strings += group
        plan.mppts.append(MpptPlan(inverter=inv_i, mppt=mppt_i, strings=[s.id for s in group],
                                   current_a=round(req.panel.imp_a * len(group), 2), short_circuit_a=round(isc * len(group), 2)))
    return plan


def _checks(req, inv, count, plan: _Plan, lo, hi, dc_w, t_min, total_panels) -> list[ElectricalCheck]:
    out: list[ElectricalCheck] = []
    if not plan.strings:
        out.append(ElectricalCheck(id="strings", label="Chia được chuỗi", status="FAIL",
                                   detail=f"Cần {lo}–{hi} tấm mỗi chuỗi cho {inv.model}; bố trí hiện tại không chia được." if lo <= hi
                                   else f"Một tấm đã vượt cửa sổ điện áp của {inv.model}."))
        return out
    worst_voc = max(s.voc_cold_v for s in plan.strings)
    out.append(ElectricalCheck(id="voc_cold", label="Điện áp hở mạch lúc lạnh nhất ≤ giới hạn DC", status="PASS" if worst_voc <= inv.max_dc_voltage_v else "FAIL",
                               detail=f"Chuỗi dài nhất {vn(worst_voc)} V so với giới hạn {vn(inv.max_dc_voltage_v, 0)} V (tính ở {vn(t_min)} °C)."))
    low_vmp = min(s.vmp_hot_v for s in plan.strings)
    floor_v = max(inv.mppt_min_v, inv.start_voltage_v)
    out.append(ElectricalCheck(id="vmp_hot", label="Điện áp làm việc lúc nóng nhất ≥ ngưỡng MPPT", status="PASS" if low_vmp >= floor_v else "FAIL",
                               detail=f"Chuỗi ngắn nhất {vn(low_vmp)} V ở tấm {vn(req.max_ambient_c + req.cell_rise_c, 0)} °C; ngưỡng khởi động/MPPT {vn(floor_v, 0)} V."))
    high_vmp = max(s.vmp_cold_v for s in plan.strings)
    out.append(ElectricalCheck(id="vmp_cold", label="Điện áp làm việc lúc lạnh nằm trong dải MPPT", status="PASS" if high_vmp <= inv.mppt_max_v else "WARN",
                               detail=f"{vn(high_vmp)} V so với đỉnh dải MPPT {vn(inv.mppt_max_v, 0)} V."))
    worst_i = max(m.current_a for m in plan.mppts)
    worst_isc = max(m.short_circuit_a for m in plan.mppts)
    clip = max(0.0, worst_i / inv.max_current_per_mppt_a - 1) * 100
    out.append(ElectricalCheck(id="current", label="Dòng làm việc mỗi MPPT", status="PASS" if clip == 0 else "WARN",
                               detail=f"{vn(worst_i, 2)} A so với {vn(inv.max_current_per_mppt_a)} A." + (f" Inverter giới hạn dòng, mất tối đa khoảng {vn(clip)}% công suất lúc nắng gắt nhất." if clip else "")))
    out.append(ElectricalCheck(id="isc", label="Dòng ngắn mạch mỗi MPPT ≤ giới hạn", status="PASS" if worst_isc <= inv.max_short_circuit_per_mppt_a else "FAIL",
                               detail=f"{vn(worst_isc, 2)} A so với {vn(inv.max_short_circuit_per_mppt_a)} A" + ("" if req.isc_a else " (Isc ước tính bằng Imp × 1,05; nhập Isc từ datasheet để chắc chắn).")))
    ratio = dc_w / (inv.ac_rated_w * count)
    status = "FAIL" if dc_w > inv.max_dc_power_w * count else "PASS" if 0.85 <= ratio <= 1.35 else "WARN"
    out.append(ElectricalCheck(id="dc_ac", label="Tỷ lệ công suất DC/AC", status=status,
                               detail=f"{vn(ratio, 2)} ({vn(dc_w / 1000, 2)} kWp / {vn(inv.ac_rated_w * count / 1000, 1)} kW). Khoảng hợp lý 0,85–1,35; "
                                      + ("vượt công suất DC tối đa của inverter." if status == "FAIL" else "inverter đang dư công suất, có thể chọn loại nhỏ hơn." if ratio < 0.85
                                         else "inverter sẽ cắt đỉnh công suất nhiều vào buổi trưa." if ratio > 1.35 else "đạt.")))
    if plan.mixed:
        out.append(ElectricalCheck(id="orientation", label="Mỗi MPPT một hướng mái", status="WARN",
                                   detail=f"Phần mái {', '.join(plan.mixed)} quá ít tấm để thành chuỗi riêng nên được nối chung chuỗi khác hướng; sản lượng giảm vì lệch dòng. Cân nhắc tối ưu hóa công suất (optimizer) cho các tấm này."))
    else:
        out.append(ElectricalCheck(id="orientation", label="Mỗi MPPT một hướng mái", status="PASS", detail="Không có chuỗi nào nối tấm khác hướng."))
    spread = max(s.shading_spread_pct for s in plan.strings)
    out.append(ElectricalCheck(id="shading", label="Bóng che đồng đều trong chuỗi", status="PASS" if spread <= 10 else "WARN",
                               detail=f"Chênh lệch tổn thất bóng lớn nhất trong một chuỗi là {vn(spread)} điểm %." + (" Tấm bị che nhiều kéo cả chuỗi xuống; cân nhắc optimizer cho các tấm này." if spread > 10 else "")))
    if plan.unassigned:
        out.append(ElectricalCheck(id="unassigned", label="Mọi tấm đều được đấu nối", status="FAIL",
                                   detail=f"{len(plan.unassigned)}/{total_panels} tấm chưa vào chuỗi" + (" vì thiếu MPPT; thêm inverter hoặc chọn loại nhiều MPPT hơn." if plan.slots_short else f" vì không đủ {lo} tấm cùng hướng cho một chuỗi.")))
    return out


# ---- bill of materials -------------------------------------------------------------------------

BREAKERS = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160]
AC_CABLE = [(25, 4, 28_000), (32, 6, 38_000), (45, 10, 62_000), (60, 16, 95_000), (80, 25, 145_000), (110, 35, 200_000), (150, 50, 280_000)]
PRICES = {"dc_cable": 18_000, "mc4": 25_000, "dc_breaker": 450_000, "dc_spd": 650_000, "dc_box": 900_000, "ac_spd": 550_000,
          "ac_box": 700_000, "earth_wire": 22_000, "earth_rod": 1_500_000, "rail": 135_000, "mid": 15_000, "end": 15_000, "foot": 45_000}


def _bom(req, inv, count, phase, plan: _Plan, rows: int, used_panels: int) -> list[BomItem]:
    def item(group, name, spec, qty, unit, price):
        qty = round(qty, 1)
        return BomItem(group=group, name=name, spec=spec, quantity=qty, unit=unit, unit_price_vnd=price, amount_vnd=round(qty * price))

    strings = len(plan.strings)
    mppts = len(plan.mppts)
    dc_cable = math.ceil(sum(s.cable_m for s in plan.strings) * 1.1)
    ac_current = inv.ac_rated_w / (230 if phase == "single" else math.sqrt(3) * 400) * 1.1
    breaker = next((b for b in BREAKERS if b >= ac_current * 1.25), BREAKERS[-1])
    size, cable_price = next(((s, p) for limit, s, p in AC_CABLE if ac_current <= limit), AC_CABLE[-1][1:])
    cores = 3 if phase == "single" else 5
    dc_breaker = max(16, next((b for b in BREAKERS if b >= (req.isc_a or req.panel.imp_a * 1.05) * 1.25), BREAKERS[-1]))
    # Portrait rows: two rails under each row, as long as the row; clamps between and at the ends of panels.
    rail = 2 * used_panels * req.panel.width_m * 1.05 + 0.1 * rows
    bom = [
        item("panel", "Tấm pin", f"{req.panel.manufacturer} {req.panel.model}", used_panels, "tấm", req.panel.price_vnd),
        item("inverter", "Inverter hòa lưới", f"{inv.manufacturer} {inv.model} · {vn(inv.ac_rated_w / 1000, 1)} kW {'1 pha' if phase == 'single' else '3 pha'}", count, "bộ", inv.price_vnd),
        item("dc", "Cáp DC solar", "4 mm², 1,5 kV DC, chống UV", dc_cable, "m", PRICES["dc_cable"]),
        item("dc", "Đầu nối MC4", "cặp đực/cái", 2 * strings + 4, "cặp", PRICES["mc4"]),
        item("dc", "CB DC 2 cực", f"{dc_breaker} A, ≥ {vn(max(s.voc_cold_v for s in plan.strings), 0)} V DC", strings, "cái", PRICES["dc_breaker"]),
        item("dc", "Chống sét DC (SPD loại II)", f"≥ {vn(inv.max_dc_voltage_v, 0)} V DC", mppts, "cái", PRICES["dc_spd"]),
        item("dc", "Tủ điện DC", "vỏ IP65 kèm thanh cái", count, "tủ", PRICES["dc_box"]),
        item("ac", "Cáp AC", f"Cu/XLPE {cores} × {size} mm²", req.ac_run_m * count, "m", cable_price),
        item("ac", "CB AC", f"{breaker} A {'2P' if phase == 'single' else '4P'}", count, "cái", 300_000 + 8_000 * breaker),
        item("ac", "Chống sét AC (SPD loại II)", "275 V AC", count, "bộ", PRICES["ac_spd"]),
        item("ac", "Tủ điện AC", "vỏ IP65", count, "tủ", PRICES["ac_box"]),
        item("earthing", "Dây tiếp địa", "Cu bọc vàng-xanh 6 mm², nối khung và vỏ thiết bị", math.ceil(rail / 2 + 15), "m", PRICES["earth_wire"]),
        item("earthing", "Cọc tiếp địa", "bộ 3 cọc 2,4 m, điện trở ≤ 10 Ω", 1, "bộ", PRICES["earth_rod"]),
        item("mounting", "Ray nhôm", "ray 40 × 40", math.ceil(rail), "m", PRICES["rail"]),
        item("mounting", "Kẹp giữa", "giữa hai tấm", 2 * max(0, used_panels - rows), "cái", PRICES["mid"]),
        item("mounting", "Kẹp biên", "đầu dãy", 4 * rows, "cái", PRICES["end"]),
        item("mounting", "Chân đỡ / móc mái", "bước 1,2 m dọc ray", math.ceil(rail / 1.2), "cái", PRICES["foot"]),
    ]
    return [b for b in bom if b.quantity > 0]


# ---- entry point -------------------------------------------------------------------------------

def _groups(panels: list[CandidatePanel], config: ProjectConfig):
    groups: dict[str, tuple[str, list[CandidatePanel]]] = {}
    for p in panels:
        key, label = _orientation(p, config)
        groups.setdefault(key, (label, []))[1].append(p)
    return [(k, label, list(members)) for k, (label, members) in sorted(groups.items(), key=lambda kv: -len(kv[1][1]))]


def _evaluate(req: ElectricalRequest, inv: InverterSpec, count: int, t_min: float):
    volts = _voltages(req, t_min)
    lo, hi = _range(inv, *volts)
    plan = _wire(req, inv, count, _groups(req.design.panels, req.config), lo, hi, volts)
    dc_w = len(req.design.panels) * req.panel.power_w
    checks = _checks(req, inv, count, plan, lo, hi, dc_w, t_min, len(req.design.panels))
    return plan, lo, hi, checks


def _phase_for(req: ElectricalRequest, dc_w: float) -> list[Phase]:
    if req.grid_phase != "auto":
        return [req.grid_phase]
    # Households above ~8 kWp usually take three-phase supply; below it single-phase is the norm.
    return ["single", "three"] if dc_w <= 8000 else ["three", "single"]


def design_electrical(req: ElectricalRequest) -> ElectricalResult:
    if not req.design.panels:
        raise ValueError("Chưa có tấm pin nào trong phương án để thiết kế điện.")
    t_min = req.min_ambient_c if req.min_ambient_c is not None else default_min_ambient(req.config.latitude)
    dc_w = len(req.design.panels) * req.panel.power_w
    phases = _phase_for(req, dc_w)
    if req.custom_inverter:
        pool = [req.custom_inverter]
    elif req.inverter_id:
        pool = [i for i in CATALOG if i.id == req.inverter_id]
        if not pool:
            raise ValueError("Không có inverter này trong danh mục.")
    else:
        pool = [i for i in CATALOG if i.phase in phases]
    fixed = bool(req.custom_inverter or req.inverter_id)

    def tries(inv: InverterSpec):
        """Counts of one model, smallest first, until one passes every check (or three were tried)."""
        out = []
        first = max(1, math.ceil(dc_w / (inv.ac_rated_w * 1.35)))
        if first > 30:
            return out          # far too small for this system: thirty boxes on a wall is not a design
        for count in range(first, first + 3):
            plan, lo, hi, checks = _evaluate(req, inv, count, t_min)
            ac_kw = inv.ac_rated_w * count / 1000
            if req.max_ac_kw:
                over = ac_kw > req.max_ac_kw + 1e-9
                checks = checks + [ElectricalCheck(id="ac_limit", label="Công suất AC trong giới hạn đấu nối", status="FAIL" if over else "PASS",
                                                   detail=f"{vn(ac_kw, 1)} kW so với giới hạn {vn(req.max_ac_kw, 1)} kW" + (" — chọn inverter nhỏ hơn hoặc giảm số bộ." if over else "."))]
            fails = sum(c.status == "FAIL" for c in checks)
            warns = sum(c.status == "WARN" for c in checks)
            ratio = dc_w / (inv.ac_rated_w * count)
            phase_rank = phases.index(inv.phase) if inv.phase in phases else 1
            # Feasible first, then fewest warnings, preferred supply, a DC/AC near 1,15, and price.
            score = (fails, warns, phase_rank, round(abs(ratio - 1.15) * 4), inv.price_vnd * count)
            out.append((score, inv, count, plan, lo, hi, checks, ratio))
            if fails == 0:
                break
        return out

    # Every model is sized for this project, so the engineer can compare and pick by capacity; the automatic
    # choice still only draws from the supply phases that fit (or the one model the engineer named).
    every = [*CATALOG, *([req.custom_inverter] if req.custom_inverter else [])]
    tried = {inv.id: tries(inv) for inv in every}
    candidates = sorted((c for inv in pool for c in tried.get(inv.id) or tries(inv)), key=lambda c: c[0])
    if not candidates:
        raise ValueError("Inverter này quá nhỏ so với hệ (cần hơn 30 bộ); chọn loại công suất lớn hơn.")
    score, inv, count, plan, lo, hi, checks, ratio = candidates[0]
    options = []
    for runs in tried.values():
        if not runs:
            continue
        sc, i, cnt, _, _, _, chk, r = min(runs, key=lambda c: c[0])
        fails = [c.label for c in chk if c.status == "FAIL"]
        warns = [c.label for c in chk if c.status == "WARN"]
        options.append((sc, InverterOption(inverter_id=i.id, label=f"{i.manufacturer} {i.model}", phase=i.phase, ac_kw=round(i.ac_rated_w * cnt / 1000, 2),
                                           count=cnt, dc_ac_ratio=round(r, 2), feasible=not fails, price_vnd=i.price_vnd * cnt,
                                           note="Đạt mọi giới hạn" + (f"; lưu ý: {'; '.join(warns)}" if warns else "") if not fails else "Chưa đạt: " + "; ".join(fails))))
    options = [o for _, o in sorted(options, key=lambda x: x[0])]

    phase = inv.phase
    _, rows = _serpentine(req.design.panels)
    used = len(req.design.panels) - len(plan.unassigned)
    bom = _bom(req, inv, count, phase, plan, rows, used) if plan.strings else []
    cost: dict[str, float] = {}
    for b in bom:
        cost[b.group] = cost.get(b.group, 0) + b.amount_vnd
    valid = not any(c.status == "FAIL" for c in checks)
    lengths = sorted({s.length for s in plan.strings})
    summary = (f"{count} × {inv.manufacturer} {inv.model}, {len(plan.strings)} chuỗi "
               f"({' và '.join(str(n) for n in lengths)} tấm/chuỗi) trên {len(plan.mppts)} MPPT; DC/AC {vn(ratio, 2)}."
               if plan.strings else f"Chưa chia được chuỗi cho {inv.model}.")
    assumptions = [
        f"Nhiệt độ thấp nhất {vn(t_min)} °C" + (" (mặc định theo vĩ độ)" if req.min_ambient_c is None else "") + f"; nóng nhất {vn(req.max_ambient_c)} °C, tấm nóng hơn môi trường {vn(req.cell_rise_c)} °C.",
        f"Hệ số nhiệt Voc {vn(req.voc_coeff_pct, 2)} %/°C, Vmp {vn(req.vmp_coeff_pct, 2)} %/°C; Isc " + (f"{vn(req.isc_a, 2)} A theo datasheet." if req.isc_a else f"ước tính {vn(req.panel.imp_a * 1.05, 2)} A (Imp × 1,05)."),
        f"Cáp DC: {vn(req.home_run_m)} m mỗi cực từ dàn pin tới inverter; cáp AC {vn(req.ac_run_m)} m tới tủ điện chính.",
        "Chuỗi đi theo từng hàng, đổi chiều mỗi hàng; mỗi MPPT chỉ nhận chuỗi cùng hướng mái và cùng số tấm.",
        "Cỡ cáp, CB và SPD là đề xuất sơ bộ theo dòng định mức; kỹ sư điện kiểm tra sụt áp và tiêu chuẩn áp dụng trước khi thi công.",
        CATALOG_NOTE if not req.custom_inverter else "Inverter do kỹ sư nhập; thông số lấy theo datasheet kỹ sư cung cấp.",
    ]
    if fixed and not valid:
        assumptions.append("Inverter đã được chỉ định nên SolarOpt không tự đổi; xem các lựa chọn khác trong bảng so sánh.")
    return ElectricalResult(valid=valid, inverter=inv, inverter_count=count, phase=phase, dc_kwp=round(dc_w / 1000, 3),
                            ac_kw=round(inv.ac_rated_w * count / 1000, 2), dc_ac_ratio=round(ratio, 3), string_min=lo, string_max=hi,
                            strings=plan.strings, mppts=plan.mppts, unassigned_panel_ids=plan.unassigned, checks=checks, bom=bom,
                            cost_by_group={k: round(v) for k, v in cost.items()}, options=options[:12], assumptions=assumptions, summary=summary)
