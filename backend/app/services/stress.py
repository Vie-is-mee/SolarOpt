from __future__ import annotations

from copy import deepcopy

from app.schemas import DesignRequest, StressRequest, StressResult, StressScenarioResult, VerifyRequest
from app.services.optimizer import generate_design
from app.services.verifier import verify_design


def _run(name: str, sid: str, req: StressRequest, cfg, obstacles, panel, detail: str) -> StressScenarioResult:
    design = generate_design(DesignRequest(
        config=cfg, panel=panel, obstacles=obstacles, sun=req.sun,
        objective="durability", previous_panels=req.design.panels, minimal_repair_weight=180,
    ))
    ver = verify_design(VerifyRequest(config=cfg, panel=panel, obstacles=obstacles, design=design, sun=req.sun))
    return StressScenarioResult(
        id=sid, name=name, status="PASS" if ver.valid else "FAIL",
        panel_count=design.metrics.panel_count,
        annual_energy_kwh=design.metrics.annual_energy_kwh,
        detail=detail,
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
    return StressResult(passed=passed, total=len(scenarios), scenarios=scenarios)
