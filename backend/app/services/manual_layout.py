"""Re-evaluate a layout after the engineer moved or removed panels by hand.

The optimiser's layout is a starting point; on site an engineer shifts a row to clear a walkway, a gutter
or a cable route. Each panel is re-measured exactly as the verifier does (face under it, plan footprint
on that face's slope, hourly shading, energy), so the numbers and checks shown after a drag are the same
ones a fresh verification would produce, and panels that now collide or overhang are named.
"""
from __future__ import annotations

from app.schemas import VerifyRequest
from app.services.energy import EnergyContext, monthly_energy, summarize
from app.services.geometry import build_context, footprint_dims, panel_shape
from app.services.verifier import verify_design


def evaluate_layout(req: VerifyRequest):
    ctx = build_context(req.config, req.obstacles, None)
    energy = EnergyContext(req.config, req.obstacles, geometry=ctx)
    faces = {s.id: s for s in ctx.surfaces}
    panels = []
    for p in req.design.panels:
        value = energy.evaluate(panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg), req.panel.power_w)
        # Moved onto a face with another slope: keep the centre, take that face's plan footprint.
        dims = footprint_dims(req.panel.width_m, req.panel.height_m, p.rotation_deg % 180, faces.get(value.face_id), req.config) if value.face_id else None
        if dims and (abs(dims[0] - p.width_m) > 1e-5 or abs(dims[1] - p.height_m) > 1e-5):
            cx, cy = p.x + p.width_m / 2, p.y + p.height_m / 2
            p = p.model_copy(update={"x": cx - dims[0] / 2, "y": cy - dims[1] / 2, "width_m": dims[0], "height_m": dims[1]})
            value = energy.evaluate(panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg), req.panel.power_w)
        panels.append(p.model_copy(update={"annual_energy_kwh": value.annual_kwh, "shading_loss_pct": value.loss_pct,
                                           "face_id": value.face_id or "outside"}))
    old = req.design.metrics
    metrics = summarize(req.config, req.panel, panels, ctx.roof.area).model_copy(
        update={"usable_area_m2": old.usable_area_m2, "area_upper_bound_panels": old.area_upper_bound_panels})
    note = "Kỹ sư đã chỉnh tay vị trí tấm pin; sản lượng, bóng che và kiểm tra được tính lại cho từng tấm sau khi dời."
    target = req.config.target_energy_kwh_year
    design = req.design.model_copy(update={
        "panels": panels, "metrics": metrics, "monthly_energy_kwh": monthly_energy(req.config, req.obstacles, panels),
        "warnings": [w for w in req.design.warnings if w != note] + [note],
        "target_met": (metrics.annual_energy_kwh + 1e-7 >= target) if req.design.objective == "min_cost" and target else req.design.target_met,
    })
    verification = verify_design(req.model_copy(update={"design": design}), energy_context=energy)
    return {"design": design, "verification": verification}
