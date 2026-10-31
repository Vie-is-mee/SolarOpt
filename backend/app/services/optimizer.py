from __future__ import annotations
import os
import math


try:
    from ortools.sat.python import cp_model
except Exception:  # Cho phép chạy demo tối thiểu trước khi cài OR-Tools
    cp_model = None

from app.services.layout_search import search_layouts, same_position, score
from app.services.design_policy import capacity, select_for_target
from app.services.energy import representative_contexts, summarize, MODEL_NOTE

from app.schemas import DesignMetrics, DesignRequest, DesignResult
from app.services.geometry import build_context


_same_position = same_position


def area_upper_bound(cfg, spec, ctx):
    """Panels that could fit by area alone: usable roof minus obstacle clearance, ignoring gaps,
    shading caps and budget. No layout can exceed it, so selected/bound is a conservative fill ratio."""
    free = ctx.usable_roof.buffer(-cfg.layout_edge_reserve_m, join_style=2) if cfg.layout_edge_reserve_m else ctx.usable_roof
    if ctx.obstacle_union is not None and not ctx.obstacle_union.is_empty:
        free = free.difference(ctx.obstacle_union)
    area = max(0.0, free.area)
    # Panels on slopes or tilted racks occupy only cos(tilt) of their area in plan; use the smallest
    # footprint so the bound stays an upper bound on every face.
    tilts = [s.mount_tilt if getattr(s, "mount", None) == "tilted_rack" else 0.0 if getattr(s, "mount", None) else s.tilt
             for s in ctx.surfaces if s.installable] or [0.0]
    footprint = spec.width_m * spec.height_m * min(math.cos(math.radians(t)) for t in tilts)
    return round(area, 2), int(area // footprint)


def describe_goal(req, result):
    result.objective=req.objective
    if req.objective=='min_cost':
        result.target_energy_kwh_year=req.config.target_energy_kwh_year
        result.target_met=sum(round(p.annual_energy_kwh*100) for p in result.panels)>=math.ceil(req.config.target_energy_kwh_year*100-1e-7)
        if not result.target_met:
            result.warnings.append('Chưa đáp ứng điện năng mục tiêu trong ngân sách và các lưới đã thử. Kết quả hiển thị là sản lượng khả thi tìm được, không phải phương án đã đáp ứng nhu cầu.')
    if req.objective=='robust':
        from app.schemas import StressRequest, RobustnessCheck
        from app.services.stress import run_stress_tests
        stress=run_stress_tests(StressRequest(config=req.config,panel=req.panel,obstacles=req.obstacles,design=result,sun=req.sun))
        result.robustness_checks=[RobustnessCheck(id=s.id,name=s.name,status=s.status,detail=s.detail) for s in stress.scenarios]
        result.warnings.append(f'Dự phòng: {stress.passed}/{stress.total} tình huống đạt không cảnh báo; {stress.warned} có cảnh báo, {stress.failed} không đạt. Có xét mái -2%, tấm +1%, lùi mép +15 cm và ngân sách -15%; chưa bảo đảm mọi sai số ngoài các tình huống đã thử.')
    return result

def generate_design(req: DesignRequest) -> DesignResult:
    cfg, spec = req.config, req.panel
    if (cfg.roof_width_m/(spec.width_m+cfg.panel_gap_m))*(cfg.roof_height_m/(spec.height_m+cfg.panel_gap_m)) > 10000:
        raise ValueError("Lưới ứng viên quá lớn cho bản MVP; giảm phạm vi mái hoặc kiểm tra kích thước tấm pin.")
    # Hình học vật cản là ràng buộc cứng. Bóng che dùng nhiều thời điểm đại diện trong năm,
    # không phụ thuộc riêng thanh kéo giờ trên giao diện (thanh kéo chỉ để trực quan hóa).
    ctx = build_context(cfg, req.obstacles, None)
    shade_contexts = representative_contexts(cfg, req.obstacles)
    search_info={}
    candidates, layout_trials = search_layouts(req, ctx, shade_contexts, diagnostics=search_info)
    search_warnings=(["Đã đạt giới hạn thời gian tìm kiếm; chỉ so sánh các lưới đã tính hoàn tất. Có thể chọn góc xếp thủ công để tập trung tìm kiếm."] if search_info.get('limited') else [])

    if not candidates:
        return describe_goal(req, DesignResult(
            panels=[],
            metrics=DesignMetrics(
                panel_count=0, peak_power_kwp=0, annual_energy_kwh=0, annual_energy_mwh=0,
                estimated_cost_vnd=0, average_shading_loss_pct=0, roof_utilization_pct=0,
                preserved_panel_count=0, layout_preservation_rate_pct=0,
            ),
            warnings=search_warnings+["Không có vị trí khả thi trong phạm vi đã thử. Kiểm tra biên mái, vật cản, số đo và thông số tấm pin; không tự giảm ràng buộc an toàn."],
            solver_status="INFEASIBLE", layout_trials=layout_trials,
        ))

    # Ưu tiên CP-SAT. Nếu máy chưa cài OR-Tools, dùng greedy fallback để giao diện vẫn chạy;
    # README hướng dẫn cài OR-Tools trước khi quay/nộp demo chính thức.
    if cp_model is not None:
        model = cp_model.CpModel()
        xs = [model.NewBoolVar(c.id) for c in candidates]
        if spec.price_vnd > 0:
            model.Add(sum(xs) <= capacity(req))

        terms = []
        for var, c in zip(xs, candidates):
            terms.append(var * score(req,c))
        if req.objective=='min_cost' and select_for_target(req,candidates)[1]:
            cents=[round(c.annual_energy_kwh*100) for c in candidates]
            energy_expr=sum(var*e for var,e in zip(xs,cents))
            model.Add(energy_expr>=math.ceil(cfg.target_energy_kwh_year*100-1e-7))
            # Fewest equal-price panels first; energy is only the tie breaker.
            model.Minimize(sum(xs)*(sum(cents)+1)-energy_expr)
        else:
            model.Maximize(sum(terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 3.0
        solver.parameters.num_search_workers = max(1, min(8, int(os.getenv("SOLAROPT_SOLVER_WORKERS", "2"))))
        status = solver.Solve(model)
        status_name = solver.StatusName(status)
        selected = [c for var, c in zip(xs, candidates) if solver.Value(var) == 1] if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else []
    if cp_model is None or status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        max_count = min(len(candidates),capacity(req))
        selected = sorted((c for c in candidates if score(req,c)>0), key=lambda c:score(req,c), reverse=True)[:max_count]
        if req.objective=='min_cost':selected,_=select_for_target(req,candidates)
        if cp_model is not None:
            search_warnings.append(f'Bộ chọn kết thúc với trạng thái {status_name}; dùng bố trí khả thi theo thứ tự điện năng trên lưới đã chọn.')
        status_name = "GREEDY_FALLBACK"

    preserved = 0
    if req.previous_panels:
        for old in req.previous_panels:
            if any(_same_position(old, new) for new in selected):
                preserved += 1
    roof_area = ctx.roof.area

    metrics = summarize(cfg, spec, selected, roof_area, preserved, len(req.previous_panels))
    metrics.usable_area_m2, metrics.area_upper_bound_panels = area_upper_bound(cfg, spec, ctx)
    warnings: list[str] = search_warnings + ["Chi phí chỉ gồm tấm pin, chưa gồm inverter, khung, dây và thi công.", MODEL_NOTE]
    warnings.append(f"Đã so sánh {len(layout_trials)} lưới xoay/dịch; chọn theo mục tiêu trong các lưới đã thử, chưa phải tối ưu mọi cách xếp.")
    if len(selected) == 0:
        warnings.append("Solver không chọn được panel trong ngân sách/ràng buộc hiện tại.")
    on_tops = sum(1 for p in selected if (p.face_id or "").startswith("top-"))
    if on_tops:
        warnings.append(f"{on_tops} tấm đặt trên nóc vật cản: cần kỹ sư xác nhận kết cấu chịu tải, lối lên bảo trì, chống gió và chi phí khung riêng.")
    return describe_goal(req, DesignResult(panels=selected, metrics=metrics, warnings=warnings, solver_status=status_name, layout_trials=layout_trials))
