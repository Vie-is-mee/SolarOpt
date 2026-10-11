from __future__ import annotations
import os
import math


try:
    from ortools.sat.python import cp_model
except Exception:  # Cho phép chạy demo tối thiểu trước khi cài OR-Tools
    cp_model = None

from datetime import date
from app.services.layout_search import search_layouts, same_position, score
from app.services.design_policy import capacity, select_for_target

from app.schemas import CandidatePanel, DesignMetrics, DesignRequest, DesignResult, SunRequest
from app.services.geometry import build_context, overlap_ratio, panel_shape
from app.services.solar import sun_position


_same_position = same_position


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
        result.warnings.append(f'Dự phòng: giữ nguyên bố trí và kiểm tra {stress.passed}/{stress.total} tình huống đạt. Có xét mái -2%, tấm +1%, lùi mép +15 cm và ngân sách -15%; chưa bảo đảm mọi sai số ngoài các tình huống đã thử.')
    return result

def generate_design(req: DesignRequest) -> DesignResult:
    cfg, spec = req.config, req.panel
    if (cfg.roof_width_m/(spec.width_m+cfg.panel_gap_m))*(cfg.roof_height_m/(spec.height_m+cfg.panel_gap_m)) > 10000:
        raise ValueError("Lưới ứng viên quá lớn cho bản MVP; giảm phạm vi mái hoặc kiểm tra kích thước tấm pin.")
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

    candidates, layout_trials = search_layouts(req, ctx, shade_contexts)

    if not candidates:
        return describe_goal(req, DesignResult(
            panels=[],
            metrics=DesignMetrics(
                panel_count=0, peak_power_kwp=0, annual_energy_kwh=0, annual_energy_mwh=0,
                estimated_cost_vnd=0, average_shading_loss_pct=0, roof_utilization_pct=0,
                preserved_panel_count=0, layout_preservation_rate_pct=0,
            ),
            warnings=["Không có vị trí khả thi trong phạm vi đã thử. Kiểm tra biên mái, vật cản, số đo và thông số tấm pin; không tự giảm ràng buộc an toàn."],
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
    else:
        max_count = min(len(candidates),capacity(req))
        selected = sorted((c for c in candidates if score(req,c)>0), key=lambda c:score(req,c), reverse=True)[:max_count]
        if req.objective=='min_cost':selected,_=select_for_target(req,candidates)
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
    roof_area = ctx.roof.area

    metrics = DesignMetrics(
        panel_count=len(selected),
        peak_power_kwp=round(len(selected) * spec.power_w / 1000.0, 3),
        annual_energy_kwh=round(energy, 1),
        annual_energy_mwh=round(energy / 1000.0, 3),
        estimated_cost_vnd=round(len(selected) * spec.price_vnd, 0),
        average_shading_loss_pct=round(shading, 2),
        maximum_shading_loss_pct=max((p.shading_loss_pct for p in selected), default=0),
        roof_utilization_pct=round(100 * used_area / max(1e-6, roof_area), 1),
        preserved_panel_count=preserved,
        layout_preservation_rate_pct=round(preservation_rate, 1),
    )
    warnings: list[str] = ["Chi phí chỉ gồm tấm pin, chưa gồm inverter, khung, dây và thi công.", "Sản lượng sơ bộ dùng 9 thời điểm bóng che đại diện; chưa phải mô phỏng năm theo giờ đã đối chuẩn."]
    warnings.append(f"Đã so sánh {len(layout_trials)} lưới xoay/dịch; chọn theo mục tiêu trong các lưới đã thử, chưa phải tối ưu mọi cách xếp.")
    if len(selected) == 0:
        warnings.append("Solver không chọn được panel trong ngân sách/ràng buộc hiện tại.")
    return describe_goal(req, DesignResult(panels=selected, metrics=metrics, warnings=warnings, solver_status=status_name, layout_trials=layout_trials))
