from shapely.affinity import rotate
from shapely.geometry import box
from app.schemas import ProjectConfig, PanelSpec, DesignRequest, VerifyRequest, StressRequest
from app.services.optimizer import generate_design
from app.services.verifier import verify_design
from app.services.stress import run_stress_tests
from app.services.layout_search import same_position


def diagonal_roof(**kwargs):
    polygon=rotate(box(9,6,10.4,14),45,origin='center')
    return ProjectConfig(roof_width_m=20,roof_height_m=20,roof_polygon=[{'x':x,'y':y} for x,y in list(polygon.exterior.coords)[:-1]],
        setback_m=.05,budget_vnd=100_000_000,geometry_confirmed=True,**kwargs)


def test_diagonal_strip_adapts_when_axis_grid_cannot_fit():
    spec=PanelSpec()
    baseline=generate_design(DesignRequest(config=diagonal_roof(layout_angle_deg=0),panel=spec))
    result=generate_design(DesignRequest(config=diagonal_roof(),panel=spec))
    assert baseline.metrics.panel_count==0
    assert result.metrics.panel_count>0
    assert all(p.rotation_deg in (45,135) for p in result.panels)
    assert all(p.width_m==spec.width_m and p.height_m==spec.height_m for p in result.panels)
    assert verify_design(VerifyRequest(config=diagonal_roof(),panel=spec,design=result)).valid
    assert len([t for t in result.layout_trials if t.selected])==1
    chosen=next(t for t in result.layout_trials if t.selected)
    assert chosen.objective_score==max(t.objective_score for t in result.layout_trials)


def test_manual_angle_and_budget_are_respected():
    cfg=diagonal_roof(layout_angle_deg=45)
    spec=PanelSpec()
    cfg.budget_vnd=2*spec.price_vnd
    result=generate_design(DesignRequest(config=cfg,panel=spec))
    assert len(result.panels)==2
    assert {p.rotation_deg for p in result.panels}=={45}
    assert verify_design(VerifyRequest(config=cfg,panel=spec,design=result)).valid


def test_verifier_and_stress_use_rotated_footprints():
    cfg=diagonal_roof();spec=PanelSpec()
    result=generate_design(DesignRequest(config=cfg,panel=spec))
    stress=run_stress_tests(StressRequest(config=cfg,panel=spec,design=result))
    assert stress.scenarios[0].status=='PASS'
    forged=result.model_copy(deep=True)
    for p in forged.panels:p.rotation_deg=0
    checks=verify_design(VerifyRequest(config=cfg,panel=spec,design=forged)).checks
    assert next(c for c in checks if c.id=='roof_boundary').status=='FAIL'


def test_repair_reuses_rotated_positions_and_rotation_matters():
    cfg=diagonal_roof();spec=PanelSpec()
    old=generate_design(DesignRequest(config=cfg,panel=spec))
    new=generate_design(DesignRequest(config=cfg,panel=spec,previous_panels=old.panels,minimal_repair_weight=250))
    assert new.metrics.preserved_panel_count==len(old.panels)
    p=old.panels[0]
    changed=p.model_copy(update={'rotation_deg':p.rotation_deg+90})
    assert not same_position(p,changed)


def test_fallback_agrees_on_best_grid(monkeypatch):
    import app.services.optimizer as optimizer
    req=DesignRequest(config=diagonal_roof(),panel=PanelSpec())
    exact=optimizer.generate_design(req)
    monkeypatch.setattr(optimizer,'cp_model',None)
    fallback=optimizer.generate_design(req)
    assert fallback.metrics.panel_count==exact.metrics.panel_count
    assert fallback.metrics.annual_energy_kwh==exact.metrics.annual_energy_kwh


def test_refinement_improves_a_concave_rotated_roof():
    from shapely.geometry import Polygon
    from shapely.affinity import translate
    from app.schemas import RectObstacle
    polygon=rotate(Polygon([(0,0),(10,0),(10,3),(6,3),(6,8),(0,8)]),37,origin=(0,0))
    polygon=translate(polygon,xoff=1-polygon.bounds[0],yoff=1-polygon.bounds[1])
    cfg=ProjectConfig(roof_width_m=20,roof_height_m=20,setback_m=.2,budget_vnd=500_000_000,
        roof_polygon=[{'x':x,'y':y} for x,y in list(polygon.exterior.coords)[:-1]])
    obstacle=RectObstacle(id='o',x=5.6,y=5,width_m=2,depth_m=2,height_m=0)
    result=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),obstacles=[obstacle]))
    coarse=max((t for t in result.layout_trials if t.search_stage=='coarse'),key=lambda t:t.objective_score)
    chosen=next(t for t in result.layout_trials if t.selected)
    assert coarse.panel_count==7 and chosen.panel_count==8
    assert chosen.objective_score>coarse.objective_score
    assert verify_design(VerifyRequest(config=cfg,panel=PanelSpec(),obstacles=[obstacle],design=result)).valid


def test_stress_failures_identify_panels_and_give_actions_without_mutation():
    cfg=diagonal_roof();spec=PanelSpec()
    result=generate_design(DesignRequest(config=cfg,panel=spec))
    req=StressRequest(config=cfg,panel=spec,design=result)
    before=req.model_dump()
    stress=run_stress_tests(req)
    failed=[s for s in stress.scenarios if s.status=='FAIL']
    assert failed
    for scenario in failed:
        assert scenario.failed_checks and scenario.recommendations
        if any(c.id=='roof_boundary' for c in scenario.failed_checks):
            assert scenario.affected_panel_ids
            assert set(scenario.affected_panel_ids)<=set(p.id for p in result.panels)
    assert req.model_dump()==before


def test_edge_reserve_is_packing_margin_not_a_new_verification_constraint():
    from app.services.geometry import panel_shape,build_context
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,setback_m=.35,layout_edge_reserve_m=.5,budget_vnd=500_000_000)
    result=generate_design(DesignRequest(config=cfg,panel=PanelSpec()))
    region=build_context(cfg,[],None).roof.buffer(-.85,join_style=2)
    assert result.panels
    assert all(region.covers(panel_shape(p.x,p.y,p.width_m,p.height_m,p.rotation_deg)) for p in result.panels)
    stress=run_stress_tests(StressRequest(config=cfg,panel=PanelSpec(),design=result))
    assert next(s for s in stress.scenarios if s.id=='setback').status=='PASS'
