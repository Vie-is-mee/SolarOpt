from __future__ import annotations

from shapely.geometry import box

from app.schemas import CheckResult, VerifyRequest, VerifyResult
from app.services.geometry import build_context, panel_shape, overlap_ratio


def verify_design(req: VerifyRequest) -> VerifyResult:
    ctx = build_context(req.config, req.obstacles, req.sun)
    checks: list[CheckResult] = []
    panels = req.design.panels

    outside = []
    obstacle_hits = []
    shadow_heavy = []
    shapes = []
    for p in panels:
        s = panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg)
        shapes.append(s)
        if not ctx.usable_roof.covers(s) or not any(
            face.installable and face.polygon.buffer(-req.config.setback_m,join_style=2).covers(s)
            for face in ctx.surfaces
        ):
            outside.append(p.id)
        if overlap_ratio(s,ctx.obstacle_union) > 1e-8:
            obstacle_hits.append(p.id)
        if (overlap_ratio(s,ctx.shadow_union) > .4 if req.sun is not None else p.shading_loss_pct > 40):
            shadow_heavy.append(p.id)

    overlap_pairs = []
    for i in range(len(shapes)):
        for j in range(i+1, len(shapes)):
            if shapes[i].intersection(shapes[j]).area > 1e-6:
                overlap_pairs.append((panels[i].id, panels[j].id))

    actual_cost = len(panels)*req.panel.price_vnd
    cost_ok = actual_cost <= req.config.budget_vnd + 1
    power_ok = req.panel.power_w > 0 and req.panel.voc_v > 0 and req.panel.imp_a > 0
    energy_ok = req.design.metrics.annual_energy_kwh > 0

    checks.extend([
        CheckResult(id="geometry_confirmation", label="Kỹ sư xác nhận dữ liệu", status="PASS" if req.config.geometry_confirmed and all(o.confirmed for o in req.obstacles) else "WARN", detail="Đã xác nhận dữ liệu đầu vào" if req.config.geometry_confirmed and all(o.confirmed for o in req.obstacles) else "Còn dữ liệu ước lượng/chưa xác nhận; chưa cho lưu bản duyệt."),
        CheckResult(id="roof_boundary", label="Tấm pin nằm trong vùng mái hợp lệ", status="PASS" if not outside else "FAIL", detail="Đạt" if not outside else f"Ngoài mái: {', '.join(outside[:5])}", affected_panel_ids=outside),
        CheckResult(id="obstacle_clearance", label="Không giao vùng vật cản/an toàn", status="PASS" if not obstacle_hits else "FAIL", detail="Đạt" if not obstacle_hits else f"Va chạm: {', '.join(obstacle_hits[:5])}", affected_panel_ids=obstacle_hits),
        CheckResult(id="panel_overlap", label="Không chồng lấn giữa các tấm pin", status="PASS" if not overlap_pairs else "FAIL", detail="Đạt" if not overlap_pairs else f"Có {len(overlap_pairs)} cặp chồng lấn", affected_panel_ids=sorted({id for pair in overlap_pairs for id in pair})),
        CheckResult(id="shadow", label="Bóng che tại thời điểm kiểm tra" if req.sun else "Tổn thất bóng sơ bộ", status="PASS" if not shadow_heavy else "WARN", detail="Không vượt ngưỡng cảnh báo 40%" if not shadow_heavy else f"{len(shadow_heavy)} tấm vượt ngưỡng cảnh báo 40%"),
        CheckResult(id="budget", label="Chi phí tấm pin không vượt ngân sách", status="PASS" if cost_ok else "FAIL", detail=f"{actual_cost:,.0f} / {req.config.budget_vnd:,.0f} VND; chưa phải tổng mức đầu tư"),
        CheckResult(id="panel_data", label="Thông số điện tấm pin hợp lệ", status="PASS" if power_ok else "FAIL", detail=f"P={req.panel.power_w}W, Voc={req.panel.voc_v}V, Imp={req.panel.imp_a}A"),
        CheckResult(id="energy", label="Mô phỏng sản lượng có kết quả", status="PASS" if energy_ok else "FAIL", detail=f"{req.design.metrics.annual_energy_kwh:,.0f} kWh/năm"),
        CheckResult(id="solver", label="Bộ tối ưu trả phương án khả thi", status="PASS" if req.design.metrics.panel_count > 0 else "FAIL", detail=req.design.solver_status),
    ])
    consistent = req.design.metrics.panel_count == len(panels) and abs(req.design.metrics.estimated_cost_vnd-actual_cost)<=1
    consistent = consistent and all(abs(p.width_m-req.panel.width_m)<1e-5 and abs(p.height_m-req.panel.height_m)<1e-5 for p in panels)
    checks.append(CheckResult(id="result_consistency",label="Kết quả khớp dữ liệu tấm pin",status="PASS" if consistent else "FAIL",detail="Số lượng, kích thước và chi phí được đối chiếu lại." if consistent else "Kết quả không khớp số lượng/kích thước/đơn giá hiện tại; cần tính lại."))
    if req.design.objective=='min_cost':
        target=req.config.target_energy_kwh_year
        actual=sum(p.annual_energy_kwh for p in panels)
        met=target is not None and actual+1e-7>=target
        checks.append(CheckResult(id='energy_target',label='Đáp ứng điện năng mục tiêu',status='PASS' if met else 'FAIL',detail=f'{actual:,.2f} / {target:,.2f} kWh/năm' if target is not None else 'Chưa nhập điện năng mục tiêu.'))
    valid = all(c.status != "FAIL" for c in checks)
    return VerifyResult(valid=valid, checks=checks)
