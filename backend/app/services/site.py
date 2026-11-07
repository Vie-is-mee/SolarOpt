"""Site survey screening: roof structure, wind, corrosion, fire safety, legal path and data quality.

These are screening rules for a preliminary design, not a replacement for the structural engineer, the
electrician on site or the permits. Every figure names its source; values that are planning assumptions say so.
The mounting plan (attachment spacing, materials) is shared with the electrical bill of materials.

Sources
- Wind: basic pressure W0 per zone I–V (65/95/125/155/185 daN/m²) and height factor k(z) by terrain A/B/C in
  the style of TCVN 2737; the zone of each commune is in the national table of natural conditions for
  construction (QCVN 02). Edge zones e/10 with e = min(b, 2h) as in EN 1991-1-4. Net pressure coefficients for
  panels parallel to the roof are screening values.
- Fire: Fire Police guidance 3288/C07-P4 (08/9/2020), replaced by 207/C07-P4 (09/8/2024) which keeps the 40 × 40 m groups and
  1,5 m gaps — services/geometry.py holds the layout rules.
- Legal: Nghị định 58/2025/NĐ-CP (Điều 10, 12, 14, 15, 16, 17, 18, 23, 37 and forms 01–05), surplus cap 50 %
  per Nghị định 243/2026/NĐ-CP.
- Corrosion: ISO 9223 categories by distance to the sea; anodising classes and A4 (316) fasteners by category.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.schemas import DesignResult, PanelSpec, ProjectConfig, RectObstacle
from app.site_evidence import SiteSurvey

Status = Literal["PASS", "WARN", "FAIL", "INFO"]
Zone = Literal["I", "II", "III", "IV", "V"]



# ---- wind -----------------------------------------------------------------------------------------

W0_KPA = {"I": .65, "II": .95, "III": 1.25, "IV": 1.55, "V": 1.85}
_K_HEIGHTS = (3, 5, 10, 15, 20, 30, 40, 50, 60)
_K = {"A": (1.00, 1.07, 1.18, 1.24, 1.29, 1.37, 1.43, 1.47, 1.51),
      "B": (.80, .88, 1.00, 1.08, 1.13, 1.22, 1.28, 1.34, 1.38),
      "C": (.47, .54, .66, .74, .80, .89, .97, 1.03, 1.08)}
GAMMA_WIND = 1.2
# Net uplift coefficients (centre, edge) for panels; flush arrays are partly pressure-equalised.
C_NET = {"flush": (.9, 1.5), "rack": (1.3, 2.0)}
RACK_MASS = {"flush": 2.5, "rack": 5.0}           # kg/m² of panel: rails, clamps, feet (no ballast)
FOOT_CAPACITY = {("metal", "steel"): 2.0, ("metal", "wood"): 1.2, ("metal", "concrete"): 2.0, ("tile", None): 1.0,
                 ("concrete", None): 3.0}
DEFAULT_FOOT_KN = 1.5
LEGACY_SPACING = 1.2                              # rail span without a survey
MAX_SPACING, MIN_SPACING = 1.2, .4
REAR_TEST_PA, TEST_SAFETY = 2400, 1.5
# Light roofs that are not walked on carry 30 daN/m² live load, flat concrete roofs 75 (TCVN 2737 tables).
ROOF_LIVE = {"metal": 30, "tile": 30, "concrete": 75}
ZONE_HINT = ("TP.HCM thường thuộc vùng II (W0 = 95 daN/m²). Tra vùng theo xã/phường trong bảng phân vùng áp lực gió "
             "theo địa danh hành chính (QCVN 02, dùng cùng TCVN 2737:2023); ven biển Bắc Bộ, Bắc Trung Bộ và hải đảo thường vùng III–V.")


def k_height(z: float, terrain: str) -> float:
    z = min(max(z, _K_HEIGHTS[0]), _K_HEIGHTS[-1])
    values = _K[terrain]
    for i in range(1, len(_K_HEIGHTS)):
        if z <= _K_HEIGHTS[i]:
            z0, z1 = _K_HEIGHTS[i - 1], _K_HEIGHTS[i]
            return values[i - 1] + (values[i] - values[i - 1]) * (z - z0) / (z1 - z0)
    return values[-1]


def suggested_zone(latitude: float, longitude: float) -> Zone | None:
    """Only where the zone is known to SolarOpt (Hồ Chí Minh City area); elsewhere the engineer looks it up."""
    return "II" if math.hypot(latitude - 10.78, (longitude - 106.70) * math.cos(math.radians(10.8))) <= .4 else None


class MountingPlan(BaseModel):
    surveyed: bool
    wind_zone: Zone
    zone_assumed: bool
    w0_kpa: float
    k_z: float
    q_center_kpa: float
    q_edge_kpa: float
    edge_zone_m: float
    foot_capacity_kn: float
    foot_spacing_center_m: float
    foot_spacing_edge_m: float
    panel_design_load_pa: float
    recommended_setback_m: float
    corrosion_class: Literal["C2", "C3", "C4", "C5"]
    corrosion_assumed: bool
    price_factor: float
    rail_spec: str
    fastener_spec: str
    notes: list[str]


def _rack(config: ProjectConfig) -> bool:
    flat = not config.roof_faces or all(f.tilt_deg <= 1 for f in config.roof_faces if f.installable)
    return config.mounting != "flush" and flat and config.roof_tilt_deg <= 1


def _spacing(capacity: float, q: float, trib: float) -> float:
    raw = capacity / max(q * trib, 1e-6)
    return round(min(MAX_SPACING, max(MIN_SPACING, math.floor(raw * 10) / 10)), 1)


def corrosion(survey: SiteSurvey) -> tuple[str, bool]:
    if survey.coast_km is None:
        cls, assumed = "C3", True
    else:
        km = survey.coast_km
        cls, assumed = ("C5" if km < .5 else "C4" if km < 3 else "C3" if km < 10 else "C2"), False
    if survey.industrial_air:
        cls = {"C2": "C3", "C3": "C4"}.get(cls, cls)
    return cls, assumed


MATERIALS = {
    "C2": (1.0, "nhôm 6005-T5 anod ≥ 15 µm (AA15)", "bulông, kẹp inox 304 (A2)"),
    "C3": (1.0, "nhôm 6005-T5 anod ≥ 15 µm (AA15)", "bulông, kẹp inox 304 (A2); vít mái có ron EPDM"),
    "C4": (1.15, "nhôm anod ≥ 20 µm (AA20)", "inox 316 (A4); đệm cách điện giữa nhôm và thép/kẽm"),
    "C5": (1.3, "nhôm anod ≥ 25 µm (AA25) hoặc anod + sơn tĩnh điện", "inox 316 (A4); đệm cách điện giữa nhôm và thép/kẽm"),
}


def mounting_plan(config: ProjectConfig, panel: PanelSpec, survey: SiteSurvey | None, rear_load_pa: float | None = None) -> MountingPlan:
    """Attachment spacing and materials. Without a survey: the legacy 1,2 m span and standard materials, labelled."""
    s = survey or SiteSurvey()
    zone = s.wind_zone or suggested_zone(config.latitude, config.longitude) or "II"
    zone_assumed = s.wind_zone is None
    rack = _rack(config)
    c_center, c_edge = C_NET["rack" if rack else "flush"]
    z = max([config.roof_elevation_m, *(f.elevation_m for f in config.roof_faces)])
    k = k_height(z, s.terrain)
    w0 = W0_KPA[zone]
    q_center, q_edge = w0 * k * c_center * GAMMA_WIND, w0 * k * c_edge * GAMMA_WIND
    roof = Polygon([(p.x, p.y) for p in config.roof_polygon]) if len(config.roof_polygon) >= 3 else None
    minx, miny, maxx, maxy = roof.bounds if roof is not None else (0, 0, config.roof_width_m, config.roof_height_m)
    e = min(min(maxx - minx, maxy - miny), 2 * max(z, 3))
    edge = round(max(.5, e / 10), 2)
    key = (s.roof_material, s.purlin if s.roof_material == "metal" else None)
    capacity = s.foot_capacity_kn or FOOT_CAPACITY.get(key, DEFAULT_FOOT_KN)
    trib = max(panel.width_m, panel.height_m) / 2
    rear = (rear_load_pa or REAR_TEST_PA) / TEST_SAFETY
    notes = []
    if survey is None:
        center = edge_spacing = LEGACY_SPACING
        notes.append("Chưa khảo sát: bước chân đỡ 1,2 m là giả định cho mái thường ở vùng gió I–II, chưa tăng chân ở vùng mép.")
    else:
        center, edge_spacing = _spacing(capacity, q_center, trib), _spacing(capacity, q_edge, trib)
    setback = config.setback_m
    if zone in ("IV", "V") or q_edge * 1000 > rear:
        setback = max(setback, edge)
        notes.append(f"Nên lùi tấm ra khỏi vùng mép {edge:g} m: áp lực hút ở mép lớn và tấm chịu tải mặt sau thiết kế khoảng {rear:,.0f} Pa.".replace(",", "."))
    cls, cls_assumed = corrosion(s)
    factor, rail, fastener = MATERIALS[cls]
    return MountingPlan(surveyed=survey is not None, wind_zone=zone, zone_assumed=zone_assumed, w0_kpa=w0, k_z=round(k, 3),
                        q_center_kpa=round(q_center, 3), q_edge_kpa=round(q_edge, 3), edge_zone_m=edge, foot_capacity_kn=capacity,
                        foot_spacing_center_m=center, foot_spacing_edge_m=edge_spacing, panel_design_load_pa=round(rear),
                        recommended_setback_m=round(setback, 2), corrosion_class=cls, corrosion_assumed=cls_assumed,
                        price_factor=factor if survey else 1.0, rail_spec=rail, fastener_spec=fastener, notes=notes)


def edge_panel_ids(config: ProjectConfig, design: DesignResult, width: float) -> set[str]:
    """Panels that reach into the edge strip of the roof outline."""
    from app.services.geometry import panel_shape, roof_polygon
    inner = roof_polygon(config).buffer(-width, join_style=2)
    return {p.id for p in design.panels if not inner.covers(panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg))}


# ---- review --------------------------------------------------------------------------------------

class ReviewItem(BaseModel):
    id: str
    label: str
    status: Status
    detail: str
    source: str = ""


class ReviewSection(BaseModel):
    id: Literal["structure", "wind", "corrosion", "fire", "legal", "data"]
    title: str
    items: list[ReviewItem]


class SiteReviewRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = Field(default_factory=list, max_length=100)
    design: DesignResult | None = None
    survey: SiteSurvey | None = Field(default=None, description="None: not surveyed yet; the electrical design then uses the legacy mounting")
    # Datasheet figures of the panel (they belong to the panel, not the site).
    panel_mass_kg: float | None = Field(default=None, gt=0, le=100)
    panel_rear_load_pa: float | None = Field(default=None, ge=1000, le=10000, description="Rear (uplift) test load")
    customer_type: Literal["residential", "business", "industrial"] = "residential"
    sell_surplus: bool = True
    ac_kw: float | None = Field(default=None, gt=0, le=100_000)
    input_kind: Literal["drone", "plan", "partial"] | None = None
    today: str | None = Field(default=None, max_length=7)


class SiteReview(BaseModel):
    sections: list[ReviewSection]
    mounting: MountingPlan
    dead_load_kg_m2: float
    array_mass_kg: float
    legal_path: str
    counts: dict[str, int]


def vn(v: float, d: int = 1) -> str:
    text = f"{v:,.{d}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return text.rstrip("0").rstrip(",") if "," in text else text


def _structure(req: SiteReviewRequest, plan: MountingPlan, n: int):
    s, p = req.survey, req.panel
    area = p.width_m * p.height_m
    mass = req.panel_mass_kg or 11.0 * area
    rack = "rack" if _rack(req.config) else "flush"
    dead = mass / area + RACK_MASS[rack]
    total = n * (mass + RACK_MASS[rack] * area)
    items = []
    src_mass = "khối lượng tấm theo datasheet" if req.panel_mass_kg else "khối lượng tấm ước 11 kg/m² (chưa có datasheet)"
    live = ROOF_LIVE.get(s.roof_material)
    share = dead / live * 100 if live else None
    detail = (f"Hệ pin thêm khoảng {vn(dead)} daN/m² ({src_mass}, ray và kẹp {vn(RACK_MASS[rack])} kg/m²); tổng {vn(total, 0)} kg cho {n} tấm."
              + (f" Bằng khoảng {vn(share, 0)}% hoạt tải thiết kế của mái loại này ({live} daN/m²), nên xà gồ phải được kiểm tra." if share else ""))
    if s.roof_material == "unknown":
        items.append(ReviewItem(id="material", label="Vật liệu mái", status="WARN", detail="Chưa khảo sát loại mái. " + detail,
                                source="TCVN 2737 (hoạt tải mái)"))
    elif s.roof_material == "combustible":
        items.append(ReviewItem(id="material", label="Vật liệu mái", status="FAIL",
                                detail="Không lắp tấm pin trên mái làm bằng hoặc hoàn thiện bằng vật liệu cháy được.", source="Hướng dẫn 207/C07-P4 (09/8/2024, thay 3288/C07-P4)"))
    else:
        status = "WARN" if s.roof_material == "tile" or (share or 0) > 50 else "PASS"
        extra = {"tile": " Mái ngói dễ vỡ khi đi lại và cần móc ngói chuyên dụng; kỹ sư kết cấu kiểm tra hệ li tô, cầu phong.",
                 "metal": " Dùng vít tự khoan có ron EPDM bắt vào xà gồ, không bắt vào tôn.",
                 "concrete": " Khoan neo hóa chất hoặc đổ chân bê tông; xử lý chống thấm tại mỗi chân."}[s.roof_material]
        items.append(ReviewItem(id="material", label="Tải trọng thêm lên mái", status=status, detail=detail + extra, source="TCVN 2737 (hoạt tải mái)"))
    if s.purlin == "wood" or (s.roof_material == "metal" and s.purlin == "unknown"):
        items.append(ReviewItem(id="purlin", label="Xà gồ", status="WARN",
                                detail="Xà gồ gỗ hoặc chưa rõ loại: cần kỹ sư kết cấu kiểm tra tiết diện, bước xà gồ và liên kết trước khi lắp."))
    if s.roof_defects:
        items.append(ReviewItem(id="defects", label="Hiện trạng mái", status="FAIL",
                                detail="Mái có rỉ, dột, võng hoặc nứt: sửa hoặc thay trước khi lắp; tháo hệ pin để sửa mái sau này rất tốn kém."))
    if s.roof_age_years is not None and s.roof_material in ("metal", "tile"):
        life = 25 if s.roof_material == "metal" else 40
        left = life - s.roof_age_years
        status = "FAIL" if left < 10 else "WARN" if left < 25 else "PASS"
        items.append(ReviewItem(id="age", label="Tuổi mái so với tuổi thọ hệ (25 năm)", status=status,
                                detail=f"Mái {vn(s.roof_age_years, 0)} năm; {'tôn' if s.roof_material == 'metal' else 'ngói'} thường bền khoảng {life} năm, còn khoảng {vn(max(0, left), 0)} năm."
                                + (" Nên thay mái trước khi lắp." if status == "FAIL" else " Dự trù chi phí tháo và lắp lại hệ khi thay mái." if status == "WARN" else "")))
    if rack == "rack":
        ballast = plan.q_center_kpa * 1000 / 9.81 * 1.5
        items.append(ReviewItem(id="ballast", label="Giá nghiêng: neo hay đối trọng", status="WARN" if s.roof_material != "concrete" or ballast > 75 else "INFO",
                                detail=f"Không khoan neo thì cần đối trọng khoảng {vn(ballast, 0)} kg/m² để chống lật ở vùng gió {plan.wind_zone} (hệ số an toàn 1,5); "
                                       "thường vượt khả năng chịu tải của mái, nên dùng neo hóa chất hoặc kết hợp."))
    return items, dead, total


def _wind(req: SiteReviewRequest, plan: MountingPlan):
    s = req.survey
    items = [ReviewItem(id="zone", label="Vùng áp lực gió", status="WARN" if plan.zone_assumed else "PASS",
                        detail=(f"Vùng {plan.wind_zone}, W0 = {vn(plan.w0_kpa * 100, 0)} daN/m²; hệ số độ cao k = {vn(plan.k_z, 2)} (địa hình {s.terrain}, cao {vn(req.config.roof_elevation_m)} m). "
                                + ("Chưa chọn vùng: đang lấy " + ("theo vị trí TP.HCM." if suggested_zone(req.config.latitude, req.config.longitude) else "vùng II tạm tính.") + " " + ZONE_HINT if plan.zone_assumed else "")),
                        source="TCVN 2737:2023; bảng phân vùng theo địa danh (QCVN 02)")]
    items.append(ReviewItem(id="uplift", label="Áp lực hút lên tấm", status="FAIL" if plan.q_center_kpa * 1000 > plan.panel_design_load_pa else "WARN" if plan.q_edge_kpa * 1000 > plan.panel_design_load_pa else "PASS",
                            detail=f"Giữa mái khoảng {vn(plan.q_center_kpa * 1000, 0)} Pa, vùng mép rộng {vn(plan.edge_zone_m, 2)} m khoảng {vn(plan.q_edge_kpa * 1000, 0)} Pa (đã nhân hệ số 1,2); "
                                   f"tấm chịu tải mặt sau thiết kế {vn(plan.panel_design_load_pa, 0)} Pa (tải thử {vn(plan.panel_design_load_pa * TEST_SAFETY, 0)} Pa chia 1,5).",
                            source="Vùng mép e/10, e = min(b, 2h) theo EN 1991-1-4; hệ số áp lực là giá trị sàng lọc"))
    items.append(ReviewItem(id="feet", label="Bước chân đỡ dọc ray", status="WARN" if plan.foot_spacing_edge_m < .6 or not plan.surveyed else "PASS",
                            detail=(f"{vn(plan.foot_spacing_center_m)} m ở giữa mái, {vn(plan.foot_spacing_edge_m)} m ở vùng mép; mỗi chân chịu {vn(plan.foot_capacity_kn)} kN"
                                    + (" (theo kỹ sư nhập)." if s.foot_capacity_kn else " (giả định theo loại mái; lấy theo catalogue ray và thử kéo tại chỗ).")
                                    + (" Bước dưới 0,6 m: cần thêm xà gồ phụ." if plan.foot_spacing_edge_m < .6 else "")) if plan.surveyed else plan.notes[0],
                            source="Khả năng chịu kéo của chân đỡ: catalogue nhà sản xuất ray"))
    gap = plan.recommended_setback_m - req.config.setback_m
    items.append(ReviewItem(id="setback", label="Khoảng lùi mép mái", status="WARN" if gap > 1e-6 else "PASS",
                            detail=(f"Đề xuất lùi {vn(plan.recommended_setback_m, 2)} m (đang {vn(req.config.setback_m, 2)} m). " + " ".join(plan.notes[1:] if not plan.surveyed else plan.notes))
                            if gap > 1e-6 else f"Lùi {vn(req.config.setback_m, 2)} m; vùng mép được tăng mật độ chân đỡ thay vì bỏ trống."))
    return items


def _corrosion(req: SiteReviewRequest, plan: MountingPlan):
    s = req.survey
    where = "chưa nhập khoảng cách tới biển, tạm tính C3" if plan.corrosion_assumed else f"cách biển {vn(s.coast_km)} km" + (", gần khu công nghiệp" if s.industrial_air else "")
    items = [ReviewItem(id="class", label="Cấp ăn mòn khí quyển", status="WARN" if plan.corrosion_assumed or plan.corrosion_class in ("C4", "C5") else "PASS",
                        detail=f"{plan.corrosion_class} ({where}). Ray {plan.rail_spec}; {plan.fastener_spec}."
                               + (f" Giá khung, ray tăng khoảng {vn((plan.price_factor - 1) * 100, 0)}% so với vật tư thường." if plan.price_factor > 1 else ""),
                        source="ISO 9223 (cấp ăn mòn), ISO 7599 (lớp anod)")]
    if plan.corrosion_class in ("C4", "C5"):
        items.append(ReviewItem(id="salt", label="Tấm và thiết bị vùng ven biển", status="WARN",
                                detail="Chọn tấm có chứng nhận sương muối IEC 61701 (mức 6 cho vùng sát biển), inverter IP66 đặt nơi khuất gió biển" + ("; tủ điện vỏ composite hoặc inox 316" if plan.corrosion_class == "C5" else "") + "; kiểm tra, siết lại bulông 6 tháng một lần."))
    return items


def _fire(req: SiteReviewRequest):
    from app.services.geometry import FIRE_BLOCK_M, FIRE_BREAK_M, FIRE_EXIT_M, FIRE_PARAPET_M, is_roof_exit, obstacle_polygon, panel_shape, roof_polygon
    s, cfg = req.survey, req.config
    src = "Hướng dẫn 207/C07-P4 (09/8/2024, thay 3288/C07-P4 ngày 08/9/2020) của Cục Cảnh sát PCCC & CNCH"
    hard = s.pccc_listed
    items = []
    if hard:
        items.append(ReviewItem(id="approval", label="Thẩm duyệt thiết kế PCCC", status="WARN",
                                detail="Công trình thuộc danh mục phải thẩm duyệt: nộp hồ sơ thiết kế PCCC phần điện mặt trời trước khi thi công và nghiệm thu PCCC trước khi sử dụng. Nhà thuê thì chủ công trình đứng tên.",
                                source="Luật PCCC và nghị định hướng dẫn; " + src))
    shapes = [(p.id, panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg)) for p in (req.design.panels if req.design else [])]
    exits = [o for o in req.obstacles if is_roof_exit(o)]
    if exits:
        near = {pid for pid, sh in shapes for o in exits if sh.distance(obstacle_polygon(o)) < FIRE_EXIT_M - 1e-6}
        items.append(ReviewItem(id="exits", label=f"Cách lối ra mái {vn(FIRE_EXIT_M, 0)} m", status=("FAIL" if hard else "WARN") if near else "PASS",
                                detail=(f"{len(near)} tấm nằm trong {vn(FIRE_EXIT_M, 0)} m quanh {', '.join(o.label for o in exits)}." if near else f"Không tấm nào trong {vn(FIRE_EXIT_M, 0)} m quanh {', '.join(o.label for o in exits)}.")
                                + (" Bật “Bố trí theo khuyến cáo PCCC” ở bước Phương án rồi tính lại." if near and not cfg.fire_code else ""), source=src))
    if shapes:
        groups = unary_union([sh.buffer(FIRE_BREAK_M / 2 - 1e-3) for _, sh in shapes])
        parts = list(getattr(groups, "geoms", [groups]))
        big = [g for g in parts if max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]) - FIRE_BREAK_M > FIRE_BLOCK_M]
        items.append(ReviewItem(id="blocks", label=f"Nhóm tấm ≤ {vn(FIRE_BLOCK_M, 0)} × {vn(FIRE_BLOCK_M, 0)} m, cách nhau ≥ {vn(FIRE_BREAK_M)} m", status=("FAIL" if hard else "WARN") if big else "PASS",
                                detail=(f"{len(big)} nhóm tấm dài hơn {vn(FIRE_BLOCK_M, 0)} m chưa có dải ngăn cháy." if big else f"{len(parts)} nhóm tấm, nhóm lớn nhất trong giới hạn."), source=src))
        if cfg.parapet:
            inner = roof_polygon(cfg).buffer(-FIRE_PARAPET_M, join_style=2)
            close = [pid for pid, sh in shapes if not inner.covers(sh)]
            items.append(ReviewItem(id="parapet", label=f"Cách lan can mái {vn(FIRE_PARAPET_M)} m", status=("FAIL" if hard else "WARN") if close else "PASS",
                                    detail=f"{len(close)} tấm cách lan can dưới {vn(FIRE_PARAPET_M)} m." if close else "Đạt.", source=src))
    items.append(ReviewItem(id="shutdown", label="Thiết bị ngắt khẩn cấp", status="INFO",
                            detail="Đặt thiết bị ngắt khẩn cấp ở cả vị trí inverter và tủ đóng cắt, niêm yết hướng dẫn vận hành; treo sơ đồ bố trí tấm và sơ đồ đấu nối gần lối lên mái (đã đưa vào bảng vật tư khi có khảo sát).",
                            source=src))
    items.append(ReviewItem(id="room", label="Vị trí inverter, tủ điện", status="INFO",
                            detail="Đặt inverter và tủ điện nơi thông thoáng, không để vật liệu cháy xung quanh; không che quạt tăng áp, hút khói và lối tiếp cận hệ thống chữa cháy trên mái.", source=src))
    return items


def legal_path(req: SiteReviewRequest, kwp: float) -> tuple[str, list[ReviewItem]]:
    s = req.survey
    src = "Nghị định 58/2025/NĐ-CP"
    household = req.customer_type == "residential"
    sell = req.sell_surplus and s.grid_connected
    items: list[ReviewItem] = []
    if s.public_property and req.sell_surplus:
        items.append(ReviewItem(id="public", label="Tài sản công không được bán điện dư", status="FAIL",
                                detail="Điện mặt trời mái nhà lắp trên tài sản công không được bán điện dư; chọn “Không bán điện dư” trong phần kinh tế.", source=src + ", Điều 14 khoản 5"))
    if not s.grid_connected:
        path = "Không đấu nối lưới: thông báo"
        items.append(ReviewItem(id="notify", label="Thông báo trước khi lắp", status="INFO",
                                detail="Gửi Sở Công Thương và đơn vị điện lực cấp tỉnh: tên, loại, công suất, mục đích, địa điểm, thời gian bắt đầu và hoàn thành.", source=src + ", Điều 12 khoản 1"))
    elif kwp >= 1000:
        path = "Từ 1.000 kW: đăng ký, cấp giấy chứng nhận"
        items.append(ReviewItem(id="register", label="Đăng ký phát triển (Mẫu số 03)", status="WARN",
                                detail="Từ 1.000 kW phải đăng ký với Sở Công Thương dù bán hay không bán điện dư; Giấy chứng nhận (Mẫu số 04) cấp trong 10 ngày khi đủ hồ sơ. Xin giấy phép hoạt động điện lực nếu bán điện, trừ trường hợp được miễn.",
                                source=src + ", Điều 16 khoản 1 điểm a; Điều 17, 18"))
    elif household and kwp < 100:
        path = "Hộ gia đình dưới 100 kW: thông báo Mẫu số 01"
        items.append(ReviewItem(id="notify", label="Thông báo trước khi lắp (Mẫu số 01)", status="INFO",
                                detail="Gửi Sở Công Thương, đơn vị điện lực, cơ quan quản lý xây dựng và PCCC địa phương; đánh dấu "
                                       + ("có bán điện dư. Không cần giấy chứng nhận đăng ký, không phải đổi đăng ký hộ kinh doanh." if sell else "không bán điện dư."),
                                source=src + ", Điều 15 khoản 2; Điều 13 khoản 2"))
    elif sell:
        path = "Tổ chức dưới 1.000 kW có bán điện dư: đăng ký Mẫu số 03"
        items.append(ReviewItem(id="register", label="Đăng ký lắp đặt (Mẫu số 03)", status="WARN",
                                detail="Nộp Sở Công Thương trước khi thi công; Giấy chứng nhận (Mẫu số 04) trong 10 ngày; điện lực trả lời khả năng quá tải lưới trong 3 ngày làm việc. Không lắp trong 60 ngày có thể bị thu hồi. "
                                       "Bán điện cần giấy phép hoạt động điện lực trừ trường hợp được miễn.",
                                source=src + ", Điều 16 khoản 1 điểm c; Điều 17, 18; Điều 20 khoản 1 điểm d"))
    else:
        path = "Tổ chức dưới 1.000 kW không bán điện dư: thông báo Mẫu số 02"
        items.append(ReviewItem(id="notify", label="Thông báo trước khi lắp (Mẫu số 02)", status="INFO",
                                detail="Gửi Sở Công Thương, đơn vị điện lực, cơ quan quản lý xây dựng và PCCC địa phương; báo Sở Công Thương sau khi hoàn thành lắp đặt, chạy thử.",
                                source=src + ", Điều 15 khoản 3; Điều 37 khoản 2 điểm a"))
    if household and kwp >= 100 and s.grid_connected and kwp < 1000:
        items.append(ReviewItem(id="household100", label="Hộ gia đình từ 100 kW", status="WARN",
                                detail="Điều 15 khoản 2 chỉ áp dụng cho hộ dưới 100 kW; hệ lớn hơn làm theo thủ tục của tổ chức, cá nhân (Mẫu số 02 hoặc đăng ký nếu bán điện).", source=src))
    if s.grid_connected:
        items.append(ReviewItem(id="acceptance", label="Nghiệm thu trước khi sử dụng", status="INFO",
                                detail="Nghiệm thu và kiểm tra an toàn điện trước khi vận hành" + ("; lắp và nghiệm thu công tơ đo đếm điện dư." if sell else "; không phải lắp hệ thống đo đếm khi không bán điện dư."),
                                source=src + ", Điều 23"))
    if sell:
        items.append(ReviewItem(id="sale", label="Hợp đồng bán điện dư (Mẫu số 05)", status="INFO",
                                detail="Bên mua ký hợp đồng trong 5 ngày làm việc khi đủ hồ sơ. Được thanh toán tối đa 50% sản lượng đầu ra inverter, giá bằng giá thị trường điện bình quân năm trước (công bố tháng 1), không cao hơn giá trần điện mặt trời mặt đất.",
                                source=src + ", Điều 14, Điều 24; Nghị định 243/2026/NĐ-CP"))
    elif s.grid_connected:
        items.append(ReviewItem(id="zero_export", label="Không phát điện dư lên lưới", status="INFO",
                                detail="Cài chế độ không phát lên lưới bằng đồng hồ đo và CT nối với inverter (đã đưa vào bảng vật tư), đúng với cam kết trong thông báo."))
    if s.grid_connected and kwp >= 100:
        items.append(ReviewItem(id="dispatch", label="Kết nối điều độ phân phối (từ 100 kW)", status="WARN",
                                detail="Trang bị thiết bị kết nối hệ thống thu thập, giám sát, điều khiển của cấp điều độ phân phối theo yêu cầu kỹ thuật của EVN; điều độ có thể ra lệnh giảm hoặc ngừng phát khi an ninh cung cấp điện bị đe dọa.",
                                source=src + ", Điều 10 khoản 5; Điều 37 khoản 2 điểm d"))
    return path, items


def _data(req: SiteReviewRequest):
    s, cfg = req.survey, req.config
    source = s.image_source or {"drone": "drone", "plan": "drawing", "partial": "drone"}.get(req.input_kind or "", None)
    items = []
    if source == "satellite":
        items.append(ReviewItem(id="resolution", label="Độ phân giải ảnh vệ tinh", status="WARN",
                                detail="Ảnh vệ tinh thường chỉ rõ 15–50 cm mỗi điểm ảnh: ống thông hơi, dây cáp, chỗ võng mái nhỏ hơn mức này có thể không thấy. Kiểm tra lại tại chỗ."))
    if s.image_date and req.today:
        y0, m0 = map(int, s.image_date.split("-"))
        y1, m1 = map(int, req.today.split("-"))
        months = (y1 - y0) * 12 + m1 - m0
        items.append(ReviewItem(id="age", label="Thời điểm chụp ảnh", status="WARN" if months > 24 else "PASS",
                                detail=f"Ảnh chụp {s.image_date}, cách nay {months} tháng." + (" Nhà bên, cây và vật cản có thể đã thay đổi." if months > 24 else "")))
    elif source in ("satellite", "drone"):
        items.append(ReviewItem(id="age", label="Thời điểm chụp ảnh", status="WARN", detail="Chưa ghi tháng chụp ảnh; ảnh vệ tinh có thể đã cũ vài năm."))
    sloped = any(f.installable and f.tilt_deg > 1 for f in cfg.roof_faces) or cfg.roof_tilt_deg > 1
    if sloped:
        items.append(ReviewItem(id="tilt", label="Độ dốc mái", status="PASS" if s.tilt_measured else "WARN",
                                detail="Độ dốc đã đo tại chỗ." if s.tilt_measured else
                                "Ảnh chụp từ trên xuống không cho biết độ dốc; đo bằng ứng dụng thước nghiêng trên điện thoại đặt trên mặt tôn rồi nhập lại cho từng mặt mái."))
    trees = [o for o in req.obstacles if (o.kind or "").startswith("tree")]
    if trees:
        items.append(ReviewItem(id="trees", label="Cây quanh nhà", status="WARN",
                                detail=f"{len(trees)} cây: cây có thể cao thêm 0,5–1 m mỗi năm; dùng thử độ nhạy chiều cao và thỏa thuận cắt tỉa."))
    if cfg.dimensions_source == "assumed":
        items.append(ReviewItem(id="dimensions", label="Kích thước mái", status="WARN", detail="Kích thước mái đang là giả định, chưa theo số đo."))
    items.append(ReviewItem(id="visit", label="Khảo sát hiện trường", status="PASS" if s.site_visit else "WARN",
                            detail="Đã khảo sát tại chỗ." if s.site_visit else
                            "Đây là thiết kế sơ bộ từ ảnh. Trước khi ký hợp đồng cần khảo sát: kết cấu, chống thấm, điện áp lưới lúc trưa, vị trí tủ điện, tiếp địa."))
    return items


def review_site(req: SiteReviewRequest) -> SiteReview:
    # The plan follows the electrical design (legacy mounting until surveyed); the checks read empty answers as unknown.
    plan = mounting_plan(req.config, req.panel, req.survey, req.panel_rear_load_pa)
    req = req.model_copy(update={"survey": req.survey or SiteSurvey()})
    n = len(req.design.panels) if req.design else 0
    kwp = req.design.metrics.peak_power_kwp if req.design else 0.0
    structure, dead, total = _structure(req, plan, n)
    path, legal = legal_path(req, max(kwp, req.ac_kw or 0))
    sections = [
        ReviewSection(id="structure", title="Kết cấu mái", items=structure),
        ReviewSection(id="wind", title="Gió bão và chân đỡ", items=_wind(req, plan)),
        ReviewSection(id="corrosion", title="Ăn mòn và vật liệu", items=_corrosion(req, plan)),
        ReviewSection(id="fire", title="Phòng cháy chữa cháy", items=_fire(req)),
        ReviewSection(id="legal", title="Thủ tục pháp lý", items=legal),
        ReviewSection(id="data", title="Độ tin cậy dữ liệu đầu vào", items=_data(req)),
    ]
    counts = {k: sum(i.status == k for s in sections for i in s.items) for k in ("PASS", "WARN", "FAIL", "INFO")}
    return SiteReview(sections=sections, mounting=plan, dead_load_kg_m2=round(dead, 1), array_mass_kg=round(total), legal_path=path, counts=counts)
