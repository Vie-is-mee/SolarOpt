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
        # Keep each panel's plan footprint (shrunk on slopes), scaled by the scenario's size change.
        p.width_m *= panel.width_m / req.panel.width_m
        p.height_m *= panel.height_m / req.panel.height_m
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


SCENARIOS = {
    'base':'Điều kiện cơ sở', 'obs20':'Vật cản cao hơn 20%', 'obs30':'Vật cản cao hơn 30%',
    'roof2':'Kích thước mái giảm 2%', 'panel1':'Kích thước tấm tăng 1%',
    'irr15':'Nắng năm giảm 15%', 'setback':'Lùi mép tăng 15 cm', 'budget':'Ngân sách giảm 15%',
}


def scenario_inputs(req, sid):
    if sid not in SCENARIOS:raise ValueError('Tình huống không hợp lệ.')
    cfg, obstacles, panel=deepcopy(req.config),deepcopy(req.obstacles),deepcopy(req.panel)
    if sid in ('obs20','obs30'):
        for o in obstacles:o.height_m*=1.2 if sid=='obs20' else 1.3
    elif sid=='roof2':
        cfg.roof_width_m*=.98;cfg.roof_height_m*=.98
        for point in cfg.roof_polygon:point.x*=.98;point.y*=.98
        for face in cfg.roof_faces:
            for point in face.polygon:point.x*=.98;point.y*=.98
        for opening in cfg.roof_openings:
            for point in opening:point.x*=.98;point.y*=.98
    elif sid=='panel1':panel.width_m*=1.01;panel.height_m*=1.01
    elif sid=='irr15':cfg.annual_irradiance_kwh_m2*=.85
    elif sid=='setback':cfg.setback_m+=.15
    elif sid=='budget':cfg.budget_vnd*=.85
    return cfg,obstacles,panel


def run_stress_tests(req: StressRequest) -> StressResult:
    scenarios=[_run(name,sid,req,*scenario_inputs(req,sid),name) for sid,name in SCENARIOS.items()]
    return StressResult(passed=sum(s.status=='PASS' for s in scenarios),
        warned=sum(s.status=='WARN' for s in scenarios),failed=sum(s.status=='FAIL' for s in scenarios),
        total=len(scenarios),scenarios=scenarios)


def preview_stress(req):
    from app.schemas import SceneRequest, SunPosition
    from app.services.scene import simulate_scene
    cfg,obstacles,panel=scenario_inputs(req,req.scenario_id)
    scene=simulate_scene(SceneRequest(config=cfg,obstacles=obstacles,date=req.date,hour_local=req.hour_local))
    current=req.model_copy(update={'sun':SunPosition(**scene['sun'])})
    result=_run(SCENARIOS[req.scenario_id],req.scenario_id,current,cfg,obstacles,panel,SCENARIOS[req.scenario_id])
    design=req.design.model_copy(deep=True)
    for p in design.panels:p.width_m=panel.width_m;p.height_m=panel.height_m
    context,_=recalculate_panels(cfg,panel,obstacles,design.panels)
    design.metrics=summarize(cfg,panel,design.panels,context.geometry.roof.area)
    base_scene=simulate_scene(SceneRequest(config=req.config,obstacles=req.obstacles,date=req.date,hour_local=req.hour_local))
    return {'base_scene':base_scene,'config':cfg,'obstacles':obstacles,'panel':panel,'design':design,'scene':scene,'result':result}
