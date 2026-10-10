from __future__ import annotations

from shapely.geometry import box

from app.schemas import CheckResult, VerifyRequest, VerifyResult
from app.services.geometry import build_context, panel_shape


def verify_design(req: VerifyRequest) -> VerifyResult:
    ctx = build_context(req.config, req.obstacles, req.sun)
    checks: list[CheckResult] = []
    panels = req.design.panels

    outside = []
    obstacle_hits = []
    shadow_heavy = []
    shapes = []
    for p in panels:
        s = panel_shape(p.x, p.y, p.width_m, p.height_m)
        shapes.append(s)
        if not ctx.usable_roof.covers(s):
            outside.append(p.id)
        if ctx.obstacle_union is not None and s.intersects(ctx.obstacle_union):
            obstacle_hits.append(p.id)
        if p.shading_loss_pct > 40:
            shadow_heavy.append(p.id)

    overlap_pairs = []
    for i in range(len(shapes)):
        for j in range(i+1, len(shapes)):
            if shapes[i].intersection(shapes[j]).area > 1e-6:
                overlap_pairs.append((panels[i].id, panels[j].id))

    cost_ok = req.design.metrics.estimated_cost_vnd <= req.config.budget_vnd + 1
    power_ok = req.panel.power_w > 0 and req.panel.voc_v > 0 and req.panel.imp_a > 0
    energy_ok = req.design.metrics.annual_energy_kwh > 0

    checks.extend([
        CheckResult(id="roof_boundary", label="Tấm pin nằm trong vùng mái hợp lệ", status="PASS" if not outside else "FAIL", detail="Đạt" if not outside else f"Ngoài mái: {', '.join(outside[:5])}"),
        CheckResult(id="obstacle_clearance", label="Không giao vùng vật cản/an toàn", status="PASS" if not obstacle_hits else "FAIL", detail="Đạt" if not obstacle_hits else f"Va chạm: {', '.join(obstacle_hits[:5])}"),
        CheckResult(id="panel_overlap", label="Không chồng lấn giữa các tấm pin", status="PASS" if not overlap_pairs else "FAIL", detail="Đạt" if not overlap_pairs else f"Có {len(overlap_pairs)} cặp chồng lấn"),
        CheckResult(id="shadow", label="Không có tấm chịu bóng che rất cao tại thời điểm kiểm tra", status="PASS" if not shadow_heavy else "WARN", detail="Đạt" if not shadow_heavy else f"{len(shadow_heavy)} tấm có tổn thất bóng >40%"),
        CheckResult(id="budget", label="Không vượt ngân sách", status="PASS" if cost_ok else "FAIL", detail=f"{req.design.metrics.estimated_cost_vnd:,.0f} / {req.config.budget_vnd:,.0f} VND"),
        CheckResult(id="panel_data", label="Thông số điện tấm pin hợp lệ", status="PASS" if power_ok else "FAIL", detail=f"P={req.panel.power_w}W, Voc={req.panel.voc_v}V, Imp={req.panel.imp_a}A"),
        CheckResult(id="energy", label="Mô phỏng sản lượng có kết quả", status="PASS" if energy_ok else "FAIL", detail=f"{req.design.metrics.annual_energy_kwh:,.0f} kWh/năm"),
        CheckResult(id="solver", label="Bộ tối ưu trả phương án khả thi", status="PASS" if req.design.metrics.panel_count > 0 else "FAIL", detail=req.design.solver_status),
    ])
    valid = all(c.status != "FAIL" for c in checks)
    return VerifyResult(valid=valid, checks=checks)
