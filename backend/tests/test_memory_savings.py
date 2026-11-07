"""Reusing and compacting results must never change them."""
import random
import numpy as np
import pytest
from app.schemas import DesignRequest,PanelSpec,ProjectConfig,RectObstacle,RoofFace,StressRequest
from app.services import energy,layout_search
from app.services.design_policy import robust_contexts,robust_position,robust_positions,select_for_target
from app.services.geometry import build_context
from app.services.optimizer import EXACT_TARGET_ABOVE,generate_design
from app.services.stress import SCENARIOS,NEW_SHADOWS,run_stress_tests,scenario_inputs

CFG=ProjectConfig(roof_width_m=12,roof_height_m=9,budget_vnd=120_000_000,target_energy_kwh_year=12000)
OBJ=[RectObstacle(id='t',label='Bồn',x=7,y=5.6,width_m=1.6,depth_m=1.4,height_m=1.8),RectObstacle(id='n',label='Nhà',scope='neighbor',x=14,y=0,width_m=5,depth_m=9,height_m=12)]


def fresh_mask(cfg,obstacles):
    energy._SERIES.clear()
    return energy.shade_series(cfg,obstacles,build_context(cfg,obstacles,None)).mask


@pytest.mark.parametrize('change',[dict(budget_vnd=1),dict(target_energy_kwh_year=1),dict(annual_irradiance_kwh_m2=1000),dict(performance_ratio=.5),
    dict(setback_m=1),dict(panel_gap_m=.5),dict(obstacle_clearance_m=1),dict(layout_edge_reserve_m=1),dict(fire_code=True),dict(project_name='khác'),dict(geometry_confirmed=True)])
def test_inputs_left_out_of_the_raster_key_really_do_not_move_a_shadow(change):
    assert np.array_equal(fresh_mask(CFG,OBJ),fresh_mask(CFG.model_copy(update=change),OBJ))


def test_object_notes_left_out_of_the_key_do_not_move_a_shadow():
    renamed=[o.model_copy(update=dict(label='Khác',confirmed=False,confidence=.1)) for o in OBJ]
    assert energy.shadow_key(CFG,OBJ)==energy.shadow_key(CFG,renamed)
    assert np.array_equal(fresh_mask(CFG,OBJ),fresh_mask(CFG,renamed))


@pytest.mark.parametrize('change',[dict(roof_width_m=11),dict(roof_elevation_m=9),dict(north_rotation_deg=30),dict(latitude=21),dict(roof_tilt_deg=10)])
def test_inputs_that_move_shadows_stay_in_the_key(change):
    assert energy.shadow_key(CFG,OBJ)!=energy.shadow_key(CFG.model_copy(update=change),OBJ)


def test_a_taller_object_changes_the_key():
    taller=[OBJ[0].model_copy(update=dict(height_m=3)),OBJ[1]]
    assert energy.shadow_key(CFG,OBJ)!=energy.shadow_key(CFG,taller)


def test_scenarios_said_to_keep_the_shadows_really_share_the_raster():
    design=generate_design(DesignRequest(config=CFG,panel=PanelSpec(),obstacles=OBJ,objective='max_energy'))
    req=StressRequest(config=CFG,panel=PanelSpec(),obstacles=OBJ,design=design)
    keys={sid:energy.shadow_key(*scenario_inputs(req,sid)[:2]) for sid in SCENARIOS}
    same={sid for sid,key in keys.items() if key==keys['base']}
    assert same==set(SCENARIOS)-NEW_SHADOWS


def test_stress_report_keeps_its_order():
    design=generate_design(DesignRequest(config=CFG,panel=PanelSpec(),obstacles=OBJ,objective='max_energy'))
    result=run_stress_tests(StressRequest(config=CFG,panel=PanelSpec(),obstacles=OBJ,design=design))
    assert [s.id for s in result.scenarios]==list(SCENARIOS)


@pytest.mark.parametrize('cfg',[CFG,ProjectConfig(roof_width_m=12,roof_height_m=9,roof_tilt_deg=20,roof_azimuth_deg=180),
    ProjectConfig(roof_polygon=[{'x':0,'y':0},{'x':10,'y':0},{'x':10,'y':4},{'x':5,'y':4},{'x':5,'y':8},{'x':0,'y':8}],roof_width_m=10,roof_height_m=8)])
def test_robust_check_of_a_whole_grid_matches_checking_each_position(cfg):
    req=DesignRequest(config=cfg,panel=PanelSpec(),obstacles=OBJ[:1],objective='robust')
    contexts=robust_contexts(req);random.seed(3)
    xs=np.array([random.uniform(-.5,cfg.roof_width_m) for _ in range(200)]);ys=np.array([random.uniform(-.5,cfg.roof_height_m) for _ in range(200)])
    for angle in (0,90,17):
        fast=robust_positions(xs,ys,angle,req,contexts)
        assert fast.tolist()==[robust_position(x,y,angle,req,contexts) for x,y in zip(xs.tolist(),ys.tolist())]


def test_grid_arrays_give_back_the_exact_position_and_energy():
    layout_search._GRID_CACHE.clear()
    design=generate_design(DesignRequest(config=CFG,panel=PanelSpec(),obstacles=OBJ,objective='max_energy'))
    rows={(p.x,p.y):p for p in design.panels}
    grid=next(g for bucket in layout_search._GRID_CACHE.values() for g in bucket.values() if len(g.px))
    assert grid.total>=len(grid.px) and isinstance(grid.px.tolist()[0],float)
    assert all(isinstance(v,float) for v in grid.annual.tolist()) and rows


def test_changing_the_budget_reuses_the_grids_and_gives_the_same_positions():
    layout_search._GRID_CACHE.clear()
    first=generate_design(DesignRequest(config=CFG,panel=PanelSpec(),obstacles=OBJ,objective='max_energy'))
    assert len(layout_search._GRID_CACHE)==1
    richer=CFG.model_copy(update=dict(budget_vnd=130_000_000))
    second=generate_design(DesignRequest(config=richer,panel=PanelSpec(),obstacles=OBJ,objective='max_energy'))
    assert len(layout_search._GRID_CACHE)==1
    layout_search._GRID_CACHE.clear();energy._SERIES.clear()
    alone=generate_design(DesignRequest(config=richer,panel=PanelSpec(),obstacles=OBJ,objective='max_energy'))
    assert [(p.x,p.y,p.annual_energy_kwh) for p in second.panels]==[(p.x,p.y,p.annual_energy_kwh) for p in alone.panels] and first.panels


def test_highest_energy_prefix_is_the_fewest_panels_reaching_the_target():
    class P:
        def __init__(s,e):s.annual_energy_kwh=e;s.preserved=False
    random.seed(5)
    for _ in range(50):
        energies=[random.uniform(300,800) for _ in range(9)]
        target=random.uniform(500,3000)
        req=DesignRequest(config=ProjectConfig(budget_vnd=10**12,target_energy_kwh_year=target),panel=PanelSpec(),objective='min_cost')
        chosen,met=select_for_target(req,[P(e) for e in energies])
        if not met:continue
        from itertools import combinations
        fewest=next(k for k in range(1,10) if any(sum(c)>=target-.01 for c in combinations(energies,k)))
        best=max(sum(c) for c in combinations(energies,len(chosen)))
        assert len(chosen)==fewest and sum(p.annual_energy_kwh for p in chosen)==pytest.approx(best)


def test_large_target_roof_skips_the_solver_and_is_marked_exact(monkeypatch):
    cfg=ProjectConfig(roof_width_m=60,roof_height_m=40,budget_vnd=60_000_000_000,target_energy_kwh_year=120000)
    monkeypatch.setattr('app.services.optimizer.cp_model',None)
    design=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective='min_cost'))
    assert design.solver_status=='OPTIMAL' and design.target_met and design.metrics.panel_count>0 and EXACT_TARGET_ABOVE<1000


def test_a_queued_light_request_still_reaches_its_endpoint_with_its_body(authenticated_client):
    # The compute gate must not read the request itself: a body consumed there leaves the endpoint waiting for ever.
    body=authenticated_client.post('/api/solar/scene',json={'config':{'roof_width_m':12,'roof_height_m':9},'obstacles':[],'date':'2026-06-21','hour_local':9},headers={'X-SolarOpt-Request':'1'})
    assert body.status_code==200 and body.json()['sun']['altitude_deg']>0
