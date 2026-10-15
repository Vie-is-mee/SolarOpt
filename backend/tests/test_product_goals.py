import math
import pytest
from pydantic import ValidationError
from app.schemas import ProjectConfig, PanelSpec, DesignRequest, StressRequest, VerifyRequest, RectObstacle
from app.services.optimizer import generate_design
from app.services.stress import run_stress_tests
from app.services.verifier import verify_design


def config(**kw):
    return ProjectConfig(roof_width_m=12,roof_height_m=9,geometry_confirmed=True,**kw)


def test_min_cost_requires_an_explicit_target():
    with pytest.raises(ValidationError,match='điện năng mục tiêu'):
        DesignRequest(config=config(),panel=PanelSpec(),objective='min_cost')


def test_three_goals_are_distinct_even_without_shadows():
    cfg=config(budget_vnd=120_000_000,target_energy_kwh_year=10_000)
    spec=PanelSpec()
    results={o:generate_design(DesignRequest(config=cfg,panel=spec,objective=o)) for o in ('max_energy','min_cost','robust')}
    assert results['min_cost'].target_met
    assert results['max_energy'].metrics.panel_count>results['min_cost'].metrics.panel_count
    assert results['max_energy'].metrics.panel_count>results['robust'].metrics.panel_count
    assert results['min_cost'].metrics.panel_count==math.ceil(10_000/results['min_cost'].panels[0].annual_energy_kwh)
    assert results['robust'].metrics.estimated_cost_vnd<=cfg.budget_vnd*.85
    assert len(results['robust'].robustness_checks)==8
    assert all(c.status=='PASS' for c in results['robust'].robustness_checks)
    for result in results.values():
        assert verify_design(VerifyRequest(config=cfg,panel=spec,design=result)).valid


def test_unmet_target_is_reported_and_fails_verification():
    cfg=config(budget_vnd=8_400_000,target_energy_kwh_year=20_000)
    result=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective='min_cost'))
    assert result.metrics.panel_count==2
    assert result.target_met is False
    assert any('Chưa đáp ứng' in w for w in result.warnings)
    verification=verify_design(VerifyRequest(config=cfg,panel=PanelSpec(),design=result))
    assert not verification.valid
    assert next(c for c in verification.checks if c.id=='energy_target').status=='FAIL'


def test_tiny_target_still_needs_one_panel():
    cfg=config(budget_vnd=500_000_000,target_energy_kwh_year=.01)
    result=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective='min_cost'))
    assert result.target_met and result.metrics.panel_count==1


def test_infeasible_roof_does_not_claim_robust_or_target_met():
    cfg=ProjectConfig(roof_width_m=1,roof_height_m=1,target_energy_kwh_year=100)
    cost=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective='min_cost'))
    robust=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective='robust'))
    assert cost.target_met is False
    assert robust.robustness_checks and any(c.status=='FAIL' for c in robust.robustness_checks)


@pytest.mark.parametrize('objective',['min_cost','robust'])
def test_fallback_respects_new_goal(objective,monkeypatch):
    import app.services.optimizer as optimizer
    cfg=config(budget_vnd=120_000_000,target_energy_kwh_year=10_000)
    req=DesignRequest(config=cfg,panel=PanelSpec(),objective=objective)
    exact=generate_design(req)
    monkeypatch.setattr(optimizer,'cp_model',None)
    fallback=generate_design(req)
    assert fallback.metrics.panel_count==exact.metrics.panel_count
    assert fallback.metrics.annual_energy_kwh==exact.metrics.annual_energy_kwh
    assert fallback.target_met==exact.target_met
    assert [c.status for c in fallback.robustness_checks]==[c.status for c in exact.robustness_checks]


def test_robust_rotated_roof_and_obstacles_pass_fixed_layout_geometry_tests():
    from shapely.geometry import Polygon
    from shapely.affinity import rotate,translate
    poly=rotate(Polygon([(0,0),(12,0),(12,4),(8,4),(8,12),(0,12)]),35,origin=(0,0))
    poly=translate(poly,xoff=1-poly.bounds[0],yoff=1-poly.bounds[1])
    cfg=ProjectConfig(roof_width_m=20,roof_height_m=20,budget_vnd=500_000_000,panel_gap_m=.02,geometry_confirmed=True,
        roof_polygon=[{'x':x,'y':y} for x,y in list(poly.exterior.coords)[:-1]])
    obstacles=[RectObstacle(id='tank',x=8,y=6,width_m=1.5,depth_m=1.5,height_m=1)]
    req=DesignRequest(config=cfg,panel=PanelSpec(),obstacles=obstacles,objective='robust')
    before=req.model_dump()
    result=generate_design(req)
    assert result.panels and req.model_dump()==before
    stress=run_stress_tests(StressRequest(config=cfg,panel=req.panel,obstacles=obstacles,design=result))
    assert all(s.status=='PASS' for s in stress.scenarios if s.id in ('base','roof2','panel1','setback','budget'))


def test_api_new_goal_roundtrip_and_unmet_target_cannot_be_approved(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main
    monkeypatch.setattr(main,'save_version',lambda *args,**kwargs:123)
    client=TestClient(main.app)
    cfg=config(budget_vnd=120_000_000,target_energy_kwh_year=100_000).model_dump()
    spec=PanelSpec().model_dump()
    missing=client.post('/api/design/generate',json={'config':{**cfg,'target_energy_kwh_year':None},'panel':spec,'objective':'min_cost'})
    assert missing.status_code==422
    response=client.post('/api/design/generate',json={'config':cfg,'panel':spec,'objective':'min_cost'})
    assert response.status_code==200 and response.json()['target_met'] is False
    payload={'config':cfg,'panel':spec,'design':response.json(),'obstacles':[]}
    rejected=client.post('/api/projects/approve',json=payload)
    assert rejected.status_code==409
    assert 'chưa đạt' in rejected.json()['detail']
    response=client.post('/api/design/generate',json={'config':cfg,'panel':spec,'objective':'robust'})
    assert response.status_code==200
    assert len(response.json()['robustness_checks'])==8
