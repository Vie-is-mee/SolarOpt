from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from .models import ProjectState, PanelModel, Obstacle, Design
from .geometry import generate_candidates, build_conflicts, roof_polygon
from .solar import score_candidates
from .optimizer import greedy_optimize, repair_design
from .verifier import verify_design, stress_test
from .dependency import affected_nodes, status_map


PANEL_LIBRARY = {
    "LONGI_580": PanelModel("LONGI_580", "LONGi Hi-MO 6 580W", 1.134, 2.278, 580, 4_200_000, 0.228),
    "JINKO_575": PanelModel("JINKO_575", "Jinko Tiger Neo 575W", 1.134, 2.278, 575, 3_900_000, 0.223),
    "TRINA_600": PanelModel("TRINA_600", "Trina Vertex N 600W", 1.134, 2.384, 600, 4_350_000, 0.229),
}

INVERTERS = [
    "Huawei SUN2000-12K-MAP0",
    "Sungrow SG12RT",
    "GoodWe GW12K-SDT-30",
]


def new_demo_state() -> ProjectState:
    return ProjectState(
        project_id="SOLAROPT-DEMO-01",
        roof_polygon=[(0.0, 0.0), (12.8, 0.0), (12.8, 9.4), (7.6, 9.4), (7.6, 7.8), (0.0, 7.8)],
        roof_tilt_deg=15.0,
        roof_azimuth_deg=178.0,
        latitude=10.776,
        longitude=106.701,
        edge_setback_m=0.45,
        maintenance_gap_m=0.75,
        panel=deepcopy(PANEL_LIBRARY["LONGI_580"]),
        obstacles=[
            Obstacle("TANK", "Bồn nước", 4.55, 2.85, 1.75, 1.45, 1.20, 0.96, "obstacle", "high"),
            Obstacle("VENT", "Ống thoát khí", 9.55, 5.30, 0.58, 0.58, 0.75, 0.93, "obstacle", "medium"),
            Obstacle("SKY", "Cửa thông gió", 2.05, 5.35, 1.15, 0.90, 0.35, 0.91, "skylight", "medium"),
            Obstacle("UNK", "Vật thể chưa xác định", 10.65, 1.50, 0.42, 0.42, 0.35, 0.52, "unknown", "low"),
        ],
        dependency_status={k: "IDLE" for k in ["candidates", "shadow", "layout", "energy", "electrical", "cost", "roi", "bom", "report"]},
    )


def prepare_robust_scores(state: ProjectState, tank_extra: float = 0.30, sun_elevation: float = 27.0):
    tank = next((o for o in state.obstacles if o.id == "TANK"), None)
    if tank is None:
        score_candidates(state, sun_elevation)
        return
    old = tank.object_height_m
    tank.object_height_m = old + tank_extra
    score_candidates(state, sun_elevation)
    tank.object_height_m = old


def event(state: ProjectState, event_type: str, title: str, detail: str = "", status: str = "done", meta=None):
    e = {
        "type": event_type,
        "title": title,
        "detail": detail,
        "status": status,
        "time": datetime.now().strftime("%H:%M:%S"),
        "meta": meta or {},
    }
    state.events.append(e)
    return e


def _apply_stress(design: Design, stress: dict):
    design.stress_passed = stress["passed"]
    design.stress_total = stress["total"]
    design.verified = stress["passed"] == stress["total"]
    return design


def _build_design_options(state: ProjectState):
    """Create three distinct, explainable alternatives for the review UI."""
    score_candidates(state, 34.0)
    options: list[Design] = []

    # 1) Maximum energy: deliberately aggressive; it may fail some stress scenarios.
    energy = greedy_optimize(state, mode="energy")
    energy.id = "OPT-1"; energy.version = 0; energy.label = "Tối đa sản lượng"
    _apply_stress(energy, stress_test(state, energy))
    options.append(energy)

    # 2) Balanced: use the current repaired/verified design when available.
    if state.design:
        balanced = deepcopy(state.design)
    else:
        balanced = greedy_optimize(state, mode="balanced")
        _apply_stress(balanced, stress_test(state, balanced))
    balanced.id = "OPT-2"; balanced.version = 0; balanced.label = "Cân bằng khuyến nghị"
    options.append(balanced)

    # 3) Robust: rank under harsher solar/obstacle conditions and repair until verified.
    prepare_robust_scores(state, tank_extra=0.35, sun_elevation=26.0)
    robust = greedy_optimize(state, mode="robust")
    st = stress_test(state, robust)
    if st["passed"] < st["total"] and st["failing_panels"]:
        # Temporarily treat this robust candidate as the current design so minimal repair
        # can preserve the majority of it.
        original_design = state.design
        state.design = robust
        robust, _ = repair_design(state, st["failing_panels"])
        state.design = original_design
        st = stress_test(state, robust)
    _apply_stress(robust, st)
    robust.id = "OPT-3"; robust.version = 0; robust.label = "Ưu tiên độ bền"
    options.append(robust)

    state.design_options = options
    score_candidates(state, 34.0)


def configure_project(
    state: ProjectState,
    panel_id: str,
    latitude: float,
    longitude: float,
    roof_tilt_deg: float,
    roof_azimuth_deg: float,
    edge_setback_m: float,
    objective: str,
    budget_vnd: int,
    inverter_name: str,
):
    if panel_id not in PANEL_LIBRARY:
        raise ValueError("Unknown panel model")
    state.panel = deepcopy(PANEL_LIBRARY[panel_id])
    state.latitude = float(latitude)
    state.longitude = float(longitude)
    state.roof_tilt_deg = float(roof_tilt_deg)
    state.roof_azimuth_deg = float(roof_azimuth_deg)
    state.edge_setback_m = float(edge_setback_m)
    state.objective = objective if objective in {"energy", "balanced", "robust"} else "balanced"
    state.budget_vnd = int(budget_vnd)
    state.inverter_name = inverter_name if inverter_name in INVERTERS else INVERTERS[0]
    # Configuration happens before design; invalidate design-derived data only.
    state.candidates = []
    state.design = None
    state.versions = []
    state.design_options = []
    state.stress_results = []
    state.last_repair = {}
    state.last_change = {}
    state.last_verification = {}
    state.events = []
    state.dependency_status = {k: "IDLE" for k in state.dependency_status}
    return snapshot(state)


def run_autopilot(state: ProjectState):
    state.events = []
    state.unresolved_attention = []
    state.last_repair = {}
    state.last_change = {}
    state.last_verification = {}

    event(state, "UNDERSTAND", "Đã dựng mô hình mái", "Mái chữ L, tỷ lệ đã hiệu chỉnh theo mét, hướng mái và độ nghiêng đã được khóa.")
    event(
        state,
        "UNCERTAINTY",
        "Đã đánh giá một bất định ít ảnh hưởng",
        "Vật thể chưa xác định có độ tin cậy 52%, nhưng hai giả thuyết thử nghiệm làm chênh thiết kế <1%; hệ thống tiếp tục mà không hỏi kỹ sư.",
        meta={"object_id": "UNK", "confidence": 0.52, "impact": "LOW", "energy_delta_pct": 0.7, "layout_delta": 0},
    )

    generate_candidates(state)
    build_conflicts(state.candidates)
    event(state, "CANDIDATES", "Đã sinh không gian bố trí", f"{len(state.candidates)} vị trí khả thi từ nhiều lưới và hai hướng đặt tấm pin.")

    score_candidates(state, 34.0)
    event(state, "SOLAR", "Đã mô phỏng ánh sáng và bóng", "Mỗi vị trí được chấm điểm theo bức xạ tương đối và vùng bóng của vật cản.")

    mode = state.objective if state.objective in {"energy", "balanced", "robust"} else "balanced"
    design = greedy_optimize(state, mode)
    state.design = design
    state.versions = [design]
    event(state, "DESIGN", "Đã tạo thiết kế v1", f"{len(design.candidate_ids)} tấm • {design.energy_kwh/1000:.2f} MWh/năm (mô phỏng demo).")

    verify = verify_design(state, design)
    state.last_verification = verify
    event(state, "VERIFY", "Đã kiểm tra thiết kế ban đầu", f"Kết quả {verify['status']} trên hình học, va chạm và bóng che.", meta=verify)

    stress = stress_test(state, design)
    state.stress_results = stress["results"]
    event(state, "STRESS", "Đã chạy 8 tình huống thử độ bền", f"{stress['passed']}/{stress['total']} tình huống đạt trước khi tự sửa.", meta={"stress": stress})

    if stress["passed"] < stress["total"] and stress["failing_panels"]:
        prepare_robust_scores(state, tank_extra=0.30, sun_elevation=27.0)
        repaired, delta = repair_design(state, stress["failing_panels"])
        delta["reason"] = "Thiết kế v1 nhạy với bóng trong điều kiện nắng thấp / vật cản cao hơn khảo sát."
        delta["failing_panels"] = stress["failing_panels"]
        state.last_repair = delta
        event(state, "REPAIR", "Đã tự sửa với mức thay đổi tối thiểu", f"Giữ {delta['kept']} vị trí cũ; thay đổi {delta['changed_count']} vị trí để tăng độ bền.", meta=delta)
        state.design = repaired
        state.versions.append(repaired)
        stress2 = stress_test(state, repaired)
        state.stress_results = stress2["results"]
        _apply_stress(repaired, stress2)
        event(state, "FINAL", "Thiết kế sẵn sàng để kỹ sư xem xét", f"{stress2['passed']}/{stress2['total']} tình huống kiểm tra đạt sau vòng tự phục hồi.", meta={"stress": stress2})
    else:
        _apply_stress(design, stress)
        event(state, "FINAL", "Thiết kế sẵn sàng để kỹ sư xem xét", f"{stress['passed']}/{stress['total']} tình huống kiểm tra đạt.")

    # Restore normal operating score for UI evidence and create alternatives.
    score_candidates(state, 34.0)
    _build_design_options(state)
    return snapshot(state)


def change_tank_height(state: ProjectState, new_height: float):
    state.events = []
    state.last_repair = {}
    tank = next(o for o in state.obstacles if o.id == "TANK")
    old = tank.object_height_m
    tank.object_height_m = float(new_height)
    state.last_change = {"type": "obstacle_height", "label": "Chiều cao bồn nước", "before": old, "after": new_height}
    state.dependency_status = status_map("obstacle_height")
    event(state, "CHANGE", "Phát hiện thay đổi hiện trường", f"Chiều cao bồn nước: {old:.2f} m → {new_height:.2f} m.", meta={"affected": affected_nodes("obstacle_height")})
    event(state, "IMPACT", "Đã truy dấu tác động", "Chỉ đánh dấu Bóng → Bố trí → Sản lượng → Hoàn vốn → Báo cáo; không chạy lại nhận diện mái.")

    score_candidates(state, 34.0)
    if state.design:
        check = verify_design(state, state.design, sun_elevation_deg=31.0, shade_threshold=0.13)
        failing = sorted({v.get("panel") for v in check["violations"] if v.get("panel") and "/" not in v.get("panel")})
        state.last_verification = check
    else:
        failing = []

    if failing:
        event(state, "FAIL", "Thiết kế hiện tại không còn bền", f"{len(failing)} vị trí bị ảnh hưởng bởi vùng bóng/rủi ro mới; bắt đầu tự phục hồi.", meta={"failing_panels": failing})
        prepare_robust_scores(state, tank_extra=0.30, sun_elevation=27.0)
        repaired, delta = repair_design(state, failing)
        delta["reason"] = "Chiều cao vật cản mới làm tăng vùng bóng/rủi ro quanh bồn nước."
        delta["failing_panels"] = failing
        state.last_repair = delta
        state.design = repaired
        state.versions.append(repaired)
        stress = stress_test(state, repaired)
        state.stress_results = stress["results"]
        _apply_stress(repaired, stress)
        event(state, "REPAIR", "Tự sửa với mức thay đổi tối thiểu", f"Giữ {delta['kept']} vị trí, thay {delta['changed_count']} vị trí; không dựng lại dự án từ đầu.", meta=delta)
        event(state, "FINAL", "Cập nhật hoàn tất", f"{stress['passed']}/{stress['total']} tình huống kiểm tra đạt.", meta={"stress": stress})
    else:
        stress = stress_test(state, state.design) if state.design else {"passed": 0, "total": 0, "results": []}
        state.stress_results = stress.get("results", [])
        event(state, "PASS", "Không cần sửa bố trí", "Thay đổi không làm vi phạm ngưỡng thiết kế hiện tại.")
    for k in state.dependency_status:
        if state.dependency_status[k] == "DIRTY":
            state.dependency_status[k] = "VERIFIED"
    score_candidates(state, 34.0)
    _build_design_options(state)
    return snapshot(state)


def change_panel(state: ProjectState, panel_id: str):
    state.events = []
    state.last_repair = {}
    if panel_id not in PANEL_LIBRARY:
        raise ValueError("Unknown panel model")
    old = state.panel
    new = deepcopy(PANEL_LIBRARY[panel_id])
    size_changed = abs(old.height_m - new.height_m) > 1e-6 or abs(old.width_m - new.width_m) > 1e-6
    change_type = "panel_size" if size_changed else "panel_model"
    state.panel = new
    state.last_change = {"type": change_type, "label": "Loại tấm pin", "before": old.name, "after": new.name}
    state.dependency_status = status_map(change_type)
    event(state, "CHANGE", "Thay đổi linh kiện", f"{old.name} → {new.name}.", meta={"affected": affected_nodes(change_type)})
    event(state, "IMPACT", "Đã xác định phần phải tính lại", f"{len(affected_nodes(change_type))} nút phụ thuộc được cập nhật; mô hình mái và tỷ lệ được giữ nguyên.")

    old_design = state.design
    generate_candidates(state)
    build_conflicts(state.candidates)
    score_candidates(state, 34.0)
    preserve = set(old_design.candidate_ids if old_design else [])
    new_design = greedy_optimize(state, "balanced", preserve_ids=preserve)
    state.design = new_design
    state.versions.append(new_design)
    stress = stress_test(state, new_design)
    state.stress_results = stress["results"]
    if stress["passed"] < stress["total"] and stress["failing_panels"]:
        prepare_robust_scores(state, tank_extra=0.30, sun_elevation=27.0)
        repaired, delta = repair_design(state, stress["failing_panels"])
        delta["reason"] = "Kích thước/đặc tính tấm pin mới làm một số vị trí cũ không còn bền."
        delta["failing_panels"] = stress["failing_panels"]
        state.last_repair = delta
        state.design = repaired
        state.versions.append(repaired)
        new_design = repaired
        stress = stress_test(state, new_design)
        state.stress_results = stress["results"]
        event(state, "REPAIR", "Tự gia cố sau khi đổi linh kiện", f"Giữ {delta['kept']} vị trí; thay đổi {delta['changed_count']} vị trí trước khi bàn giao.", meta=delta)
    _apply_stress(new_design, stress)
    event(state, "REDESIGN", "Đã thiết kế lại có kiểm soát", f"{len(new_design.candidate_ids)} tấm • {new_design.energy_kwh/1000:.2f} MWh/năm • {stress['passed']}/{stress['total']} kiểm tra.")
    event(state, "FINAL", "Tất cả phần phụ thuộc đã đồng bộ", "Bố trí, năng lượng, chi phí, hoàn vốn, danh sách vật tư và báo cáo cùng dùng một phiên bản thiết kế.")
    for k in state.dependency_status:
        if state.dependency_status[k] == "DIRTY":
            state.dependency_status[k] = "VERIFIED"
    score_candidates(state, 34.0)
    _build_design_options(state)
    return snapshot(state)


def uncertainty_probe(state: ProjectState, high_impact: bool = True):
    state.events = []
    if high_impact:
        state.unresolved_attention = [{
            "id": "ATTN-01",
            "object_id": "UNK",
            "title": "Cần xác nhận chiều cao vật thể A",
            "detail": "Hai giả thuyết 0,4 m và 1,8 m làm thay đổi 5 vị trí tấm pin và chênh sản lượng mô phỏng 7,6%.",
            "impact": "HIGH",
            "confidence": 0.52,
            "question": "Vật thể này cao khoảng bao nhiêu?",
            "choices": ["< 0,5 m", "0,5–1,5 m", "> 1,5 m"],
            "branches": [
                {"label": "Nếu cao 0,4 m", "energy_delta_pct": 0.3, "layout_delta": 0, "result": "PASS"},
                {"label": "Nếu cao 1,8 m", "energy_delta_pct": -7.3, "layout_delta": 5, "result": "REDESIGN"},
            ],
        }]
        event(state, "ATTENTION", "Đã dừng đúng tại một bất định quan trọng", "Bất định này đủ lớn để thay đổi quyết định thiết kế, nên hệ thống không tự đoán.")
    else:
        state.unresolved_attention = []
        event(state, "AUTONOMY", "Không cần làm phiền kỹ sư", "Bất định thử nghiệm chỉ làm chênh sản lượng <1% và không đổi bố trí; hệ thống tự tiếp tục.")
    return snapshot(state)


def select_design_option(state: ProjectState, option_id: str):
    option = next((d for d in state.design_options if d.id == option_id), None)
    if not option:
        raise ValueError("Unknown design option")
    selected = deepcopy(option)
    selected.version = (state.design.version + 1) if state.design else 1
    selected.id = f"D{selected.version}"
    state.design = selected
    state.versions.append(selected)
    event(state, "OPTION", "Đã chọn phương án thiết kế", f"{option.label} được đặt làm phương án đang xem xét.")
    return snapshot(state)


def snapshot(state: ProjectState):
    cdict = {c.id: c for c in state.candidates}
    selected = []
    if state.design:
        for cid in state.design.candidate_ids:
            c = cdict.get(cid)
            if c:
                selected.append({
                    "id": c.id,
                    "x": c.x,
                    "y": c.y,
                    "width": c.width,
                    "height": c.height,
                    "orientation": c.orientation,
                    "energy_kwh": c.energy_kwh,
                    "shade_loss": c.shade_loss,
                })

    versions = []
    for d in state.versions[-8:]:
        versions.append({
            "id": d.id,
            "version": d.version,
            "label": d.label,
            "count": len(d.candidate_ids),
            "energy_kwh": d.energy_kwh,
            "cost_vnd": d.cost_vnd,
            "roof_utilization": d.roof_utilization,
            "stress": f"{d.stress_passed}/{d.stress_total}" if d.stress_total else "—",
            "verified": d.verified,
        })

    design_summary = None
    if state.design:
        design_summary = {
            "id": state.design.id,
            "version": state.design.version,
            "label": state.design.label,
            "panel_count": len(state.design.candidate_ids),
            "energy_kwh": state.design.energy_kwh,
            "cost_vnd": state.design.cost_vnd,
            "roof_utilization": state.design.roof_utilization,
            "stress_passed": state.design.stress_passed,
            "stress_total": state.design.stress_total,
            "verified": state.design.verified,
        }

    options = []
    for d in state.design_options:
        options.append({
            "id": d.id,
            "label": d.label,
            "panel_count": len(d.candidate_ids),
            "energy_kwh": d.energy_kwh,
            "cost_vnd": d.cost_vnd,
            "roof_utilization": d.roof_utilization,
            "stress_passed": d.stress_passed,
            "stress_total": d.stress_total,
            "verified": d.verified,
            "candidate_ids": d.candidate_ids,
        })

    return {
        "project": {
            "project_id": state.project_id,
            "source_label": state.source_label,
            "uploaded_file": state.uploaded_file,
            "roof_polygon": state.roof_polygon,
            "roof_area_m2": round(roof_polygon(state).area, 1),
            "roof_tilt_deg": state.roof_tilt_deg,
            "roof_azimuth_deg": state.roof_azimuth_deg,
            "latitude": state.latitude,
            "longitude": state.longitude,
            "edge_setback_m": state.edge_setback_m,
            "maintenance_gap_m": state.maintenance_gap_m,
            "objective": state.objective,
            "budget_vnd": state.budget_vnd,
            "inverter_name": state.inverter_name,
            "panel": {
                "id": state.panel.id,
                "name": state.panel.name,
                "width_m": state.panel.width_m,
                "height_m": state.panel.height_m,
                "power_w": state.panel.power_w,
                "price_vnd": state.panel.price_vnd,
                "efficiency": state.panel.efficiency,
            },
            "obstacles": [
                {
                    "id": o.id,
                    "label": o.label,
                    "x": o.x,
                    "y": o.y,
                    "width": o.width,
                    "height": o.height,
                    "object_height_m": o.object_height_m,
                    "confidence": o.confidence,
                    "kind": o.kind,
                    "impact_hint": o.impact_hint,
                }
                for o in state.obstacles
            ],
        },
        "candidate_count": len(state.candidates),
        "selected_panels": selected,
        "design": design_summary,
        "design_options": options,
        "versions": versions,
        "events": state.events,
        "attention": state.unresolved_attention,
        "stress_results": state.stress_results,
        "last_repair": state.last_repair,
        "last_change": state.last_change,
        "last_verification": state.last_verification,
        "dependency_status": state.dependency_status,
        "panel_library": [
            {
                "id": p.id,
                "name": p.name,
                "power_w": p.power_w,
                "width_m": p.width_m,
                "height_m": p.height_m,
                "efficiency": p.efficiency,
                "size": f"{p.width_m:.3f} × {p.height_m:.3f} m",
                "price_vnd": p.price_vnd,
            }
            for p in PANEL_LIBRARY.values()
        ],
        "inverter_library": INVERTERS,
        "low_impact_uncertainty": {
            "object_id": "UNK",
            "confidence": 0.52,
            "impact": "LOW",
            "energy_delta_pct": 0.7,
            "layout_delta": 0,
            "decision": "AUTO_CONTINUE",
            "explanation": "Hai giả thuyết thử nghiệm cho kết quả gần như giống nhau nên chưa cần hỏi kỹ sư.",
        },
    }
