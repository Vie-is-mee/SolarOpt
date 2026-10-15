"""Regressions for the five failures reproduced in the 15 October review."""
import math
import pytest
from pydantic import ValidationError
from shapely.geometry import box

from app.schemas import (ProjectConfig, PanelSpec, CandidatePanel, DesignResult,
    DesignRequest, VerifyRequest, StressRequest, RectObstacle, SunPosition)
from app.services.energy import EnergyContext, recalculate_panels, summarize
from app.services.geometry import panel_shape
from app.services.optimizer import generate_design
from app.services.verifier import verify_design
from app.services.stress import run_stress_tests


def config(**kw):
    return ProjectConfig(geometry_confirmed=True,roof_width_m=12,roof_height_m=9,
                         budget_vnd=100_000_000,layout_angle_deg=0,**kw)


def fixed_design(cfg, spec, positions, obstacles=(), angle=0):
    panels=[CandidatePanel(id=str(i),x=x,y=y,width_m=spec.width_m,height_m=spec.height_m,
        rotation_deg=angle,annual_energy_kwh=0,shading_loss_pct=0) for i,(x,y) in enumerate(positions)]
    ctx,_=recalculate_panels(cfg,spec,list(obstacles),panels)
    return DesignResult(panels=panels,metrics=summarize(cfg,spec,panels,ctx.geometry.roof.area),solver_status='FEASIBLE')


def check(cfg,spec,design,obstacles=(),sun=None):
    return verify_design(VerifyRequest(config=cfg,panel=spec,design=design,obstacles=list(obstacles),sun=sun))


def test_flat_reference_matches_physical_units_without_orientation_penalty():
    cfg=config();spec=PanelSpec()
    value=EnergyContext(cfg,[]).evaluate(box(2,2,3,4),spec.power_w)
    # 1 kWp times irradiation-equivalent hours times performance ratio.
    assert value.annual_kwh==pytest.approx(round(.58*1581*.82,2))
    assert value.loss_pct==0


def test_generation_changes_annual_energy_when_only_roof_tilt_changes():
    flat=config()
    tilted=flat.model_copy(update={'roof_tilt_deg':40,'roof_azimuth_deg':0})
    a=generate_design(DesignRequest(config=flat,panel=PanelSpec(),objective='max_energy'))
    b=generate_design(DesignRequest(config=tilted,panel=PanelSpec(),objective='max_energy'))
    assert len(a.panels)==len(b.panels)>0
    assert b.metrics.annual_energy_kwh<a.metrics.annual_energy_kwh*.95
    assert check(tilted,PanelSpec(),b).valid


def test_each_roof_face_uses_its_own_orientation():
    cfg=config(roof_faces=[dict(id='north',polygon=[{'x':6,'y':0},{'x':12,'y':0},
        {'x':12,'y':9},{'x':6,'y':9}],elevation_m=6,tilt_deg=40,azimuth_deg=0)])
    ctx=EnergyContext(cfg,[])
    assert ctx.annual['north']<ctx.annual['base']*.95


def test_reference_plane_is_not_transposed_twice():
    cfg=config(roof_tilt_deg=40,roof_azimuth_deg=0,
               irradiance_reference_tilt_deg=40,irradiance_reference_azimuth_deg=0)
    value=EnergyContext(cfg,[]).evaluate(box(2,2,3,4),580)
    assert value.annual_kwh==pytest.approx(round(.58*1581*.82,2))


@pytest.mark.parametrize('angle',[0,31,90])
@pytest.mark.parametrize('gap,expected',[(0,False),(.079,False),(.08,True),(.081,True)])
def test_gap_check_uses_actual_distance_between_rotated_panels(angle,gap,expected):
    cfg=config();spec=PanelSpec(width_m=1,height_m=2)
    # Collinear centres keep exactly the requested edge-to-edge distance.
    a=(4,3)
    b=(a[0]+(1+gap)*math.cos(math.radians(angle)),a[1]+(1+gap)*math.sin(math.radians(angle)))
    design=fixed_design(cfg,spec,[a,b],angle=angle)
    validation=check(cfg,spec,design)
    assert (next(c for c in validation.checks if c.id=='panel_gap').status=='PASS') is expected
    assert validation.valid is expected


@pytest.mark.parametrize('field,value',[
    ('annual_energy_kwh',999999),('annual_energy_mwh',999),('peak_power_kwp',999),
    ('estimated_cost_vnd',1),('average_shading_loss_pct',90),('maximum_shading_loss_pct',90),
    ('roof_utilization_pct',99),('panel_count',99),
])
def test_server_rejects_changed_aggregate_fields(field,value):
    cfg=config();spec=PanelSpec();design=fixed_design(cfg,spec,[(2,2)])
    assert check(cfg,spec,design).valid
    setattr(design.metrics,field,value)
    validation=check(cfg,spec,design)
    assert not validation.valid
    assert next(c for c in validation.checks if c.id=='result_consistency').status=='FAIL'


def test_changing_panel_energy_and_its_total_together_cannot_bypass_check():
    cfg=config();spec=PanelSpec();design=fixed_design(cfg,spec,[(2,2)])
    design.panels[0].annual_energy_kwh=999999
    design.metrics.annual_energy_kwh=999999
    design.metrics.annual_energy_mwh=999.999
    assert not check(cfg,spec,design).valid


def test_same_footprint_with_wrong_face_id_is_rejected():
    cfg=config();spec=PanelSpec();design=fixed_design(cfg,spec,[(2,2)])
    design.panels[0].face_id='invented-face'
    assert not check(cfg,spec,design).valid


def test_non_finite_energy_is_rejected_at_input_boundary():
    with pytest.raises(ValidationError):
        CandidatePanel(id='bad',x=1,y=1,width_m=1,height_m=2,annual_energy_kwh=float('nan'),shading_loss_pct=0)


def test_stress_warning_is_not_counted_as_pass_and_preserves_input():
    cfg=config(setback_m=.1);spec=PanelSpec()
    obs=[RectObstacle(id='tank',x=5,y=2,width_m=1,depth_m=3,height_m=1)]
    sun=SunPosition(altitude_deg=45,azimuth_deg=90,zenith_deg=45)
    design=fixed_design(cfg,spec,[(3.1,2.2)],obs)
    request=StressRequest(config=cfg,panel=spec,obstacles=obs,design=design,sun=sun)
    before=request.model_dump()
    stress=run_stress_tests(request)
    high=next(s for s in stress.scenarios if s.id=='obs30')
    assert high.status=='WARN'
    assert any(c.id=='shadow' for c in high.warning_checks)
    assert high.affected_panel_ids==['0'] and high.recommendations
    assert stress.passed+stress.warned+stress.failed==8
    assert stress.warned>0
    assert request.model_dump()==before


def test_stress_without_instant_sun_recomputes_shadows_and_energy():
    cfg=config(setback_m=.1);spec=PanelSpec()
    obs=[RectObstacle(id='tank',x=5,y=2,width_m=1,depth_m=3,height_m=1)]
    design=fixed_design(cfg,spec,[(3.1,2.2)],obs)
    stress=run_stress_tests(StressRequest(config=cfg,panel=spec,obstacles=obs,design=design))
    base=next(s for s in stress.scenarios if s.id=='base')
    high=next(s for s in stress.scenarios if s.id=='obs30')
    assert high.annual_energy_kwh<base.annual_energy_kwh
    assert base.annual_energy_kwh==design.metrics.annual_energy_kwh


def test_unconfirmed_inputs_produce_stress_warnings():
    cfg=config();spec=PanelSpec();design=fixed_design(cfg,spec,[(2,2)])
    cfg.geometry_confirmed=False
    stress=run_stress_tests(StressRequest(config=cfg,panel=spec,design=design))
    assert stress.passed==0
    assert all(s.status=='WARN' for s in stress.scenarios)


@pytest.mark.parametrize('angle',[None,0,25])
def test_open_strip_splitting_roof_generates_valid_layout(angle):
    cfg=config(roof_openings=[[{'x':5,'y':0},{'x':7,'y':0},{'x':7,'y':9},{'x':5,'y':9}]])
    cfg.layout_angle_deg=angle
    spec=PanelSpec()
    design=generate_design(DesignRequest(config=cfg,panel=spec,objective='max_energy'))
    assert design.panels and check(cfg,spec,design).valid
    for p in design.panels:
        assert panel_shape(p.x,p.y,p.width_m,p.height_m,p.rotation_deg).intersection(box(5,0,7,9)).area<1e-8
    assert any(p.x<5 for p in design.panels) and any(p.x>7 for p in design.panels)


def test_completely_open_roof_returns_infeasible_not_server_error():
    cfg=config(roof_openings=[[{'x':0,'y':0},{'x':12,'y':0},{'x':12,'y':9},{'x':0,'y':9}]])
    design=generate_design(DesignRequest(config=cfg,panel=PanelSpec()))
    assert design.panels==[] and design.solver_status=='INFEASIBLE'


def test_pvgis_missing_irradiance_does_not_masquerade_as_real_data(monkeypatch):
    from app.services import solar
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'outputs':{'totals':{'fixed':{'E_y':1400}}}}
    monkeypatch.setattr(solar.requests,'get',lambda *a,**k:Response())
    assert solar.fetch_pvgis(10,106).source=='fallback'


@pytest.mark.parametrize('corruption',['energy_total','panel_energy','gap'])
def test_approval_endpoint_rejects_corrupted_or_too_close_layout(corruption,monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    saved=[]
    monkeypatch.setattr(main,'save_version',lambda *a,**k:saved.append(a) or 123)
    cfg=config();spec=PanelSpec()
    positions=[(2,2),(2+spec.width_m,2)] if corruption=='gap' else [(2,2)]
    design=fixed_design(cfg,spec,positions)
    if corruption=='energy_total':design.metrics.annual_energy_kwh=999999
    if corruption=='panel_energy':
        design.panels[0].annual_energy_kwh=999999
        design.metrics.annual_energy_kwh=999999
        design.metrics.annual_energy_mwh=999.999
    client=TestClient(main.app)
    payload={'config':cfg.model_dump(),'panel':spec.model_dump(),'design':design.model_dump(),'obstacles':[]}
    response=client.post('/api/design/verify',json=payload)
    assert response.status_code==200 and response.json()['valid'] is False
    assert client.post('/api/projects/approve',json=payload).status_code==409
    assert not saved


def test_split_roof_and_stress_statuses_roundtrip_through_api(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.setattr(main,'save_version',lambda *a,**k:123)
    cfg=config(roof_openings=[[{'x':5,'y':0},{'x':7,'y':0},{'x':7,'y':9},{'x':5,'y':9}]])
    client=TestClient(main.app);spec=PanelSpec()
    response=client.post('/api/design/generate',json={'config':cfg.model_dump(),'panel':spec.model_dump(),'objective':'max_energy'})
    assert response.status_code==200 and response.json()['panels']
    stress=client.post('/api/design/stress-test',json={'config':cfg.model_dump(),'panel':spec.model_dump(),'design':response.json()})
    assert stress.status_code==200
    data=stress.json()
    assert data['passed']+data['warned']+data['failed']==data['total']==8
    assert all(s['status'] in {'PASS','WARN','FAIL'} for s in data['scenarios'])
