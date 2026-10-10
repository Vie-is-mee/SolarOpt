from __future__ import annotations


try:
    from ortools.sat.python import cp_model
except Exception:  # Cho phép chạy demo tối thiểu trước khi cài OR-Tools
    cp_model = None

from datetime import date

from app.schemas import CandidatePanel, DesignMetrics, DesignRequest, DesignResult, SunRequest
from app.services.geometry import build_context, overlap_ratio, panel_shape
from app.services.solar import sun_position


def _same_position(a: CandidatePanel, b: CandidatePanel, tol: float = 0.02) -> bool:
    return abs(a.x - b.x) <= tol and abs(a.y - b.y) <= tol and abs(a.width_m-b.width_m) <= tol and abs(a.height_m-b.height_m) <= tol


def generate_design(req: DesignRequest) -> DesignResult:
    cfg, spec = req.config, req.panel
    # Hình học vật cản là ràng buộc cứng. Bóng che dùng nhiều thời điểm đại diện trong năm,
    # không phụ thuộc riêng thanh kéo giờ trên giao diện (thanh kéo chỉ để trực quan hóa).
    ctx = build_context(cfg, req.obstacles, None)
    shade_contexts = []
    for d in (date(2026, 3, 21), date(2026, 6, 21), date(2026, 12, 21)):
        for hour in (9.0, 12.0, 15.0):
            sp = sun_position(SunRequest(latitude=cfg.latitude, longitude=cfg.longitude, date=d, hour_local=hour))
            if sp.altitude_deg > 3:
                shade_contexts.append(build_context(cfg, req.obstacles, sp))
    pw, ph = spec.width_m, spec.height_m
    gap = cfg.panel_gap_m

    # Tạo lưới ứng viên cố định để tối ưu 0/1 và dễ giải thích.
    x0 = cfg.setback_m
    y0 = cfg.setback_m
    x_max = cfg.roof_width_m - cfg.setback_m - pw
    y_max = cfg.roof_height_m - cfg.setback_m - ph

    candidates: list[CandidatePanel] = []
    row = 0
    y = y0
    while y <= y_max + 1e-6:
        col = 0
        x = x0
        while x <= x_max + 1e-6:
            shape = panel_shape(x, y, pw, ph)
            if ctx.usable_roof.covers(shape):
                obs_overlap = overlap_ratio(shape, ctx.obstacle_union)
                if obs_overlap <= 1e-9:
                    overlaps = [overlap_ratio(shape, sc.shadow_union) for sc in shade_contexts]
                    mean_overlap = sum(overlaps) / max(1, len(overlaps))
                    max_overlap = max(overlaps, default=0.0)
                    # Tổn thất bóng là tổ hợp trung bình + tình huống bất lợi. Đây là mô hình MVP
                    # có thể kiểm chứng, thay cho việc hard-code điểm số trong frontend.
                    shading_loss = min(70.0, (0.72 * mean_overlap + 0.28 * max_overlap) * 78.0)
                    if mean_overlap < 0.55 and max_overlap < 0.50:
                        annual_kwh = (
                            spec.power_w / 1000.0
                            * cfg.annual_irradiance_kwh_m2
                            * cfg.performance_ratio
                            * (1.0 - shading_loss / 100.0)
                        )
                        cid = f"r{row}c{col}"
                        preserved = any(abs(p.x-x) < 0.02 and abs(p.y-y) < 0.02 for p in req.previous_panels)
                        candidates.append(CandidatePanel(
                            id=cid, x=round(x, 3), y=round(y, 3), width_m=pw, height_m=ph,
                            annual_energy_kwh=round(annual_kwh, 2),
                            shading_loss_pct=round(shading_loss, 2), preserved=preserved,
                        ))
            col += 1
            x += pw + gap
        row += 1
        y += ph + gap

    if not candidates:
        return DesignResult(
            panels=[],
            metrics=DesignMetrics(
                panel_count=0, peak_power_kwp=0, annual_energy_kwh=0, annual_energy_mwh=0,
                estimated_cost_vnd=0, average_shading_loss_pct=0, roof_utilization_pct=0,
                preserved_panel_count=0, layout_preservation_rate_pct=0,
            ),
            warnings=["Không có vị trí khả thi. Hãy giảm setback, chỉnh vật cản hoặc chọn tấm pin nhỏ hơn."],
            solver_status="INFEASIBLE",
        )

    # Ưu tiên CP-SAT. Nếu máy chưa cài OR-Tools, dùng greedy fallback để giao diện vẫn chạy;
    # README hướng dẫn cài OR-Tools trước khi quay/nộp demo chính thức.
    if cp_model is not None:
        model = cp_model.CpModel()
        xs = [model.NewBoolVar(c.id) for c in candidates]
        if spec.price_vnd > 0 and cfg.budget_vnd > 0:
            model.Add(sum(xs) * int(round(spec.price_vnd)) <= int(round(cfg.budget_vnd)))

        terms = []
        for var, c in zip(xs, candidates):
            energy_score = int(round(c.annual_energy_kwh * 100))
            if req.objective == "durability":
                energy_score = int(round(energy_score * (1.0 - min(c.shading_loss_pct, 50) / 120.0)))
            elif req.objective == "balanced":
                energy_score = int(round(energy_score * 0.98))
            preserve_bonus = int(round(req.minimal_repair_weight * 100)) if c.preserved else 0
            terms.append(var * (energy_score + preserve_bonus))
        model.Maximize(sum(terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 3.0
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)
        status_name = solver.StatusName(status)
        selected = [c for var, c in zip(xs, candidates) if solver.Value(var) == 1] if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else []
    else:
        max_count = len(candidates)
        if spec.price_vnd > 0 and cfg.budget_vnd > 0:
            max_count = min(max_count, int(cfg.budget_vnd // spec.price_vnd))
        def score(c):
            base = c.annual_energy_kwh
            if req.objective == "durability":
                base *= 1.0 - min(c.shading_loss_pct, 50) / 120.0
            elif req.objective == "balanced":
                base *= 0.98
            if c.preserved:
                base += req.minimal_repair_weight
            return base
        selected = sorted(candidates, key=score, reverse=True)[:max_count]
        status_name = "GREEDY_FALLBACK"

    energy = sum(p.annual_energy_kwh for p in selected)
    shading = sum(p.shading_loss_pct for p in selected) / max(1, len(selected))
    preserved = 0
    if req.previous_panels:
        for old in req.previous_panels:
            if any(_same_position(old, new) for new in selected):
                preserved += 1
    preservation_rate = 100.0 * preserved / max(1, len(req.previous_panels)) if req.previous_panels else 0.0
    used_area = len(selected) * pw * ph
    roof_area = cfg.roof_width_m * cfg.roof_height_m

    metrics = DesignMetrics(
        panel_count=len(selected),
        peak_power_kwp=round(len(selected) * spec.power_w / 1000.0, 3),
        annual_energy_kwh=round(energy, 1),
        annual_energy_mwh=round(energy / 1000.0, 3),
        estimated_cost_vnd=round(len(selected) * spec.price_vnd, 0),
        average_shading_loss_pct=round(shading, 2),
        roof_utilization_pct=round(100 * used_area / max(1e-6, roof_area), 1),
        preserved_panel_count=preserved,
        layout_preservation_rate_pct=round(preservation_rate, 1),
    )
    warnings: list[str] = []
    if len(selected) == 0:
        warnings.append("Solver không chọn được panel trong ngân sách/ràng buộc hiện tại.")
    return DesignResult(panels=selected, metrics=metrics, warnings=warnings, solver_status=status_name)
