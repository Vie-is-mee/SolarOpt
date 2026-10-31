from __future__ import annotations

import math

from app.schemas import CheckResult, VerifyRequest, VerifyResult
from app.services.geometry import build_context, panel_shape, overlap_ratio, installable_regions, footprint_dims
from app.services.energy import EnergyContext, summarize


def verify_design(req: VerifyRequest, *, energy_context=None) -> VerifyResult:
    ctx = build_context(req.config, req.obstacles, req.sun)
    checks: list[CheckResult] = []
    panels = req.design.panels
    energy_context = energy_context if energy_context is not None else EnergyContext(req.config, req.obstacles, geometry=ctx)
    recalculated = []
    face_regions = [region for _, region in installable_regions(ctx.surfaces, req.config.setback_m)]

    outside = []
    obstacle_hits = []
    shadow_heavy = []
    sample_heavy = []
    shapes = []
    for p in panels:
        s = panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg)
        shapes.append(s)
        value = energy_context.evaluate(s, req.panel.power_w)
        recalculated.append(p.model_copy(update={
            'annual_energy_kwh': value.annual_kwh, 'shading_loss_pct': value.loss_pct,
            'face_id': value.face_id or 'outside',
        }))
        if value.worst_cover > .4:
            sample_heavy.append(p.id)
        if not ctx.usable_roof.covers(s) or not any(region.covers(s) for region in face_regions):
            outside.append(p.id)
        if overlap_ratio(s,ctx.obstacle_union) > 1e-8:
            obstacle_hits.append(p.id)
        if (overlap_ratio(s,ctx.shadow_union) > .4 if req.sun is not None else value.loss_pct > 40):
            shadow_heavy.append(p.id)

    overlap_pairs = []
    gap_pairs = []
    for i in range(len(shapes)):
        for j in range(i+1, len(shapes)):
            if shapes[i].intersection(shapes[j]).area > 1e-6:
                overlap_pairs.append((panels[i].id, panels[j].id))
            elif shapes[i].distance(shapes[j]) + 3e-6 < req.config.panel_gap_m:
                gap_pairs.append((panels[i].id, panels[j].id))

    actual_cost = len(panels)*req.panel.price_vnd
    cost_ok = actual_cost <= req.config.budget_vnd + 1
    power_ok = req.panel.power_w > 0 and req.panel.voc_v > 0 and req.panel.imp_a > 0
    actual_energy = sum(p.annual_energy_kwh for p in recalculated)
    energy_ok = actual_energy > 0

    checks.extend([
        CheckResult(id="geometry_confirmation", label="Kỹ sư xác nhận dữ liệu", status="PASS" if req.config.geometry_confirmed and all(o.confirmed for o in req.obstacles) else "WARN", detail="Đã xác nhận dữ liệu đầu vào" if req.config.geometry_confirmed and all(o.confirmed for o in req.obstacles) else "Còn dữ liệu ước lượng/chưa xác nhận; chưa cho lưu bản duyệt."),
        CheckResult(id="roof_boundary", label="Tấm pin nằm trong vùng mái hợp lệ", status="PASS" if not outside else "FAIL", detail="Đạt" if not outside else f"Ngoài mái: {', '.join(outside[:5])}", affected_panel_ids=outside),
        CheckResult(id="obstacle_clearance", label="Không giao vùng vật cản/an toàn", status="PASS" if not obstacle_hits else "FAIL", detail="Đạt" if not obstacle_hits else f"Va chạm: {', '.join(obstacle_hits[:5])}", affected_panel_ids=obstacle_hits),
        CheckResult(id="panel_overlap", label="Không chồng lấn giữa các tấm pin", status="PASS" if not overlap_pairs else "FAIL", detail="Đạt" if not overlap_pairs else f"Có {len(overlap_pairs)} cặp chồng lấn", affected_panel_ids=sorted({id for pair in overlap_pairs for id in pair})),
        CheckResult(id="panel_gap", label="Đủ khe giữa các tấm pin", status="PASS" if not gap_pairs else "FAIL", detail=f"Yêu cầu tối thiểu {req.config.panel_gap_m:.3f} m; xét cả tấm xoay." if not gap_pairs else f"Có {len(gap_pairs)} cặp không đủ khe {req.config.panel_gap_m:.3f} m.", affected_panel_ids=sorted({id for pair in gap_pairs for id in pair})),
        CheckResult(id="shadow", label="Bóng che tại thời điểm kiểm tra" if req.sun else "Tổn thất bóng sơ bộ", status="PASS" if not shadow_heavy else "WARN", detail="Không vượt ngưỡng cảnh báo 40%" if not shadow_heavy else f"{len(shadow_heavy)} tấm vượt ngưỡng cảnh báo 40%", affected_panel_ids=shadow_heavy),
        CheckResult(id="shadow_samples", label="Bóng tại các thời điểm đại diện", status="WARN" if sample_heavy else "PASS", detail=f"{len(sample_heavy)} tấm chịu bóng trên 40% ở ít nhất một thời điểm đại diện." if sample_heavy else "Không vượt 40% ở các thời điểm đã thử; chưa kiểm tra mọi giờ trong năm.", affected_panel_ids=sample_heavy),
        CheckResult(id="budget", label="Chi phí tấm pin không vượt ngân sách", status="PASS" if cost_ok else "FAIL", detail=f"{actual_cost:,.0f} / {req.config.budget_vnd:,.0f} VND; chưa phải tổng mức đầu tư"),
        CheckResult(id="panel_data", label="Thông số điện tấm pin hợp lệ", status="PASS" if power_ok else "FAIL", detail=f"P={req.panel.power_w}W, Voc={req.panel.voc_v}V, Imp={req.panel.imp_a}A"),
        CheckResult(id="energy", label="Mô phỏng sản lượng có kết quả", status="PASS" if energy_ok else "FAIL", detail=f"Máy chủ tính lại: {actual_energy:,.1f} kWh/năm"),
        CheckResult(id="solver", label="Bộ tối ưu trả phương án khả thi", status="PASS" if panels and req.design.solver_status in {'OPTIMAL','FEASIBLE','GREEDY_FALLBACK'} else "FAIL", detail=req.design.solver_status),
    ])
    expected = summarize(req.config, req.panel, recalculated, ctx.roof.area)
    tolerances = {'peak_power_kwp':.00051, 'annual_energy_kwh':.051,
                  'annual_energy_mwh':.00051, 'estimated_cost_vnd':.51,
                  'average_shading_loss_pct':.0051, 'maximum_shading_loss_pct':.0051,
                  'roof_utilization_pct':.051}
    consistent = req.design.metrics.panel_count == len(panels) and len({p.id for p in panels}) == len(panels)
    consistent = consistent and all(math.isclose(getattr(req.design.metrics, key), getattr(expected, key), abs_tol=tol, rel_tol=0) for key,tol in tolerances.items())
    faces = {s.id: s for s in ctx.surfaces}
    def footprint_ok(p, face_id):
        # Plan footprint must equal the physical panel, shrunk by cos(tilt) along the fall line on sloped faces.
        dims = footprint_dims(req.panel.width_m, req.panel.height_m, p.rotation_deg % 180, faces.get(face_id), req.config)
        return dims is not None and abs(p.width_m-dims[0]) < 1e-5 and abs(p.height_m-dims[1]) < 1e-5
    consistent = consistent and all(footprint_ok(p, r.face_id) for p, r in zip(panels, recalculated))
    consistent = consistent and all(abs(a.annual_energy_kwh-b.annual_energy_kwh)<=.0051 and abs(a.shading_loss_pct-b.shading_loss_pct)<=.0051 and a.face_id==b.face_id for a,b in zip(panels,recalculated))
    checks.append(CheckResult(id="result_consistency",label="Kết quả khớp dữ liệu tấm pin",status="PASS" if consistent else "FAIL",detail="Máy chủ đã tính lại công suất, sản lượng từng tấm, bóng đại diện, diện tích, số lượng và chi phí." if consistent else "Số liệu hoặc mặt mái của tấm không khớp phép tính độc lập trên máy chủ; cần tính lại phương án."))
    if req.design.objective=='min_cost':
        target=req.config.target_energy_kwh_year
        actual=actual_energy
        met=target is not None and actual+1e-7>=target
        checks.append(CheckResult(id='energy_target',label='Đáp ứng điện năng mục tiêu',status='PASS' if met else 'FAIL',detail=f'{actual:,.2f} / {target:,.2f} kWh/năm' if target is not None else 'Chưa nhập điện năng mục tiêu.'))
    valid = all(c.status != "FAIL" for c in checks)
    return VerifyResult(valid=valid, checks=checks)
