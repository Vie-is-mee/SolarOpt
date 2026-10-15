import pytest
from app.schemas import DesignRequest, PanelSpec, ProjectConfig, RectObstacle, SunPosition, VerifyRequest
from app.services.optimizer import generate_design
from app.services.verifier import verify_design
from app.services.layout_search import SHADING_LIMITS

OBJECTIVES = ('max_energy','balanced','durability')


def signature(result):
    return sorted((p.x,p.y,p.rotation_deg) for p in result.panels)


def test_clear_roof_can_legitimately_have_identical_options():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,budget_vnd=500_000_000)
    results=[generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective=o)) for o in OBJECTIVES]
    assert results[0].panels
    assert all(signature(r)==signature(results[0]) for r in results)
    assert all(r.metrics.maximum_shading_loss_pct==0 for r in results)
    assert all(next(t for t in r.layout_trials if t.selected).shading_rejected_count==0 for r in results)


def test_shaded_roof_objectives_really_filter_and_change_layout(monkeypatch):
    # Controlled sun isolates policy differences from seasonal sampling.
    import app.services.energy as energy
    monkeypatch.setattr(energy,'sun_position',lambda _:SunPosition(altitude_deg=60,azimuth_deg=90,zenith_deg=30))
    cfg=ProjectConfig(roof_width_m=10,roof_height_m=8,setback_m=.1,obstacle_clearance_m=0,
                      layout_angle_deg=0,panel_gap_m=.1,budget_vnd=500_000_000)
    panel=PanelSpec(width_m=1,height_m=2)
    obstacles=[RectObstacle(id='wall',x=8,y=0,width_m=1,depth_m=8,height_m=3)]
    results={o:generate_design(DesignRequest(config=cfg,panel=panel,obstacles=obstacles,objective=o)) for o in OBJECTIVES}
    for objective,result in results.items():
        assert result.panels
        assert all(p.shading_loss_pct<=SHADING_LIMITS[objective] for p in result.panels)
        assert result.metrics.maximum_shading_loss_pct==max(p.shading_loss_pct for p in result.panels)
        assert verify_design(VerifyRequest(config=cfg,panel=panel,obstacles=obstacles,design=result)).valid
        assert all(t.geometry_candidate_count==t.candidate_count+t.shading_rejected_count for t in result.layout_trials)
    assert signature(results['max_energy'])!=signature(results['durability'])
    assert results['max_energy'].metrics.annual_energy_kwh>=results['durability'].metrics.annual_energy_kwh
    assert results['durability'].metrics.average_shading_loss_pct<results['max_energy'].metrics.average_shading_loss_pct


@pytest.mark.parametrize('objective',OBJECTIVES)
def test_each_objective_fallback_matches_solver_and_budget(objective,monkeypatch):
    import app.services.optimizer as optimizer
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,budget_vnd=12_600_000)
    req=DesignRequest(config=cfg,panel=PanelSpec(),objective=objective,
        obstacles=[RectObstacle(id='tank',x=5,y=4,width_m=2,depth_m=2,height_m=3)])
    result=generate_design(req)
    monkeypatch.setattr(optimizer,'cp_model',None)
    fallback=generate_design(req)
    assert fallback.metrics.annual_energy_kwh==result.metrics.annual_energy_kwh
    assert fallback.metrics.estimated_cost_vnd<=cfg.budget_vnd
    assert fallback.metrics.panel_count==3
