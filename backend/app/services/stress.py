from __future__ import annotations

from copy import deepcopy
from app.services.stress_advice import recommendations

from app.schemas import StressRequest, StressResult, StressScenarioResult, VerifyRequest
from app.services.verifier import verify_design
from app.services.energy import recalculate_panels, summarize


def _run(name: str, sid: str, req: StressRequest, cfg, obstacles, panel, detail: str) -> StressScenarioResult:
    # Test the ORIGINAL layout; do not optimize a different design and call it robust.
    design = req.design.model_copy(deep=True)
    for p in design.panels:
        p.width_m = panel.width_m
        p.height_m = panel.height_m
    context, _ = recalculate_panels(cfg, panel, obstacles, design.panels)
    design.metrics = summarize(cfg, panel, design.panels, context.geometry.roof.area)
    ver = verify_design(VerifyRequest(config=cfg, panel=panel, obstacles=obstacles, design=design, sun=req.sun), energy_context=context)
    failed=[c for c in ver.checks if c.status=='FAIL']
    warnings=[c for c in ver.checks if c.status=='WARN']
    # Recalculating scenario numbers must not silently legitimize a forged input.
    if sid=='base':
        original=verify_design(VerifyRequest(config=cfg,panel=panel,obstacles=obstacles,design=req.design,sun=req.sun), energy_context=context)
        failed.extend(c for c in original.checks if c.id=='result_consistency' and c.status=='FAIL')
    relevant=failed+warnings
    return StressScenarioResult(
        failed_checks=failed,warning_checks=warnings,recommendations=recommendations(sid,req,cfg,panel,relevant),
        affected_panel_ids=sorted({id for c in relevant for id in c.affected_panel_ids}),
        id=sid, name=name, status="FAIL" if failed else "WARN" if warnings else "PASS",
        panel_count=design.metrics.panel_count,
        annual_energy_kwh=design.metrics.annual_energy_kwh,
        detail=detail + "; giữ vị trí/góc của bố trí gốc, tính lại bóng đại diện và điện năng. " + "; ".join(c.label for c in relevant),
    )


def run_stress_tests(req: StressRequest) -> StressResult:
    scenarios: list[StressScenarioResult] = []

    scenarios.append(_run("Base geometry", "base", req, deepcopy(req.config), deepcopy(req.obstacles), deepcopy(req.panel), "Điều kiện cơ sở"))

    obs20 = deepcopy(req.obstacles)
    for o in obs20:
        o.height_m *= 1.2
    scenarios.append(_run("Obstacle height +20%", "obs20", req, deepcopy(req.config), obs20, deepcopy(req.panel), "Tăng 20% chiều cao vật cản"))

    obs30 = deepcopy(req.obstacles)
    for o in obs30:
        o.height_m *= 1.3
    scenarios.append(_run("Obstacle height +30%", "obs30", req, deepcopy(req.config), obs30, deepcopy(req.panel), "Tăng 30% chiều cao vật cản"))

    cfg_small = deepcopy(req.config)
    cfg_small.roof_width_m *= 0.98
    cfg_small.roof_height_m *= 0.98
    # Shrink the surveyed geometry while keeping original panel positions.
    for point in cfg_small.roof_polygon:
        point.x *= .98
        point.y *= .98
    for face in cfg_small.roof_faces:
        for point in face.polygon:
            point.x *= .98
            point.y *= .98
    for opening in cfg_small.roof_openings:
        for point in opening:
            point.x *= .98
            point.y *= .98
    scenarios.append(_run("Roof measurement -2%", "roof2", req, cfg_small, deepcopy(req.obstacles), deepcopy(req.panel), "Sai số đo mái -2%"))

    panel_plus = deepcopy(req.panel)
    panel_plus.width_m *= 1.01
    panel_plus.height_m *= 1.01
    scenarios.append(_run("Panel dimension +1%", "panel1", req, deepcopy(req.config), deepcopy(req.obstacles), panel_plus, "Dung sai kích thước tấm +1%"))

    cfg_irrad = deepcopy(req.config)
    cfg_irrad.annual_irradiance_kwh_m2 *= 0.85
    scenarios.append(_run("Irradiance -15%", "irr15", req, cfg_irrad, deepcopy(req.obstacles), deepcopy(req.panel), "Kịch bản bức xạ thấp hơn 15%"))

    cfg_setback = deepcopy(req.config)
    cfg_setback.setback_m += 0.15
    scenarios.append(_run("Safety setback +15cm", "setback", req, cfg_setback, deepcopy(req.obstacles), deepcopy(req.panel), "Tăng khoảng cách an toàn 15 cm"))

    cfg_budget = deepcopy(req.config)
    cfg_budget.budget_vnd *= 0.85
    scenarios.append(_run("Budget -15%", "budget", req, cfg_budget, deepcopy(req.obstacles), deepcopy(req.panel), "Giảm ngân sách 15%"))

    passed = sum(1 for s in scenarios if s.status == "PASS")
    return StressResult(passed=passed, warned=sum(s.status=='WARN' for s in scenarios),
                        failed=sum(s.status=='FAIL' for s in scenarios), total=len(scenarios), scenarios=scenarios)
