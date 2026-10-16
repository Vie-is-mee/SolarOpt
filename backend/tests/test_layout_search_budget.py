import pytest
from shapely.geometry import box
from app.schemas import DesignRequest, ProjectConfig, PanelSpec
from app.services.geometry import build_context, overlap_ratio
from app.services import layout_search


def request():
    return DesignRequest(config=ProjectConfig(roof_width_m=12,roof_height_m=9,
        geometry_confirmed=True),panel=PanelSpec())


def test_budget_before_first_grid_returns_actionable_error(monkeypatch):
    req=request()
    monkeypatch.setattr(layout_search,'perf_counter',lambda:10.)
    with pytest.raises(ValueError,match='góc xếp thủ công'):
        layout_search.search_layouts(req,build_context(req.config,[],None),[],budget_seconds=0)


def test_budget_discards_unfinished_grid_and_preserves_completed_winner(monkeypatch):
    req=request();ctx=build_context(req.config,[],None)
    full_candidates,full_trials=layout_search.search_layouts(req,ctx,[])
    calls=0
    def clock():
        nonlocal calls
        calls+=1
        return 0. if calls<=2 else 30.
    monkeypatch.setattr(layout_search,'perf_counter',clock)
    info={}
    candidates,trials=layout_search.search_layouts(req,ctx,[],diagnostics=info)
    assert info['limited']
    assert len(trials)==1
    assert trials[0]['selected']
    assert trials[0]['candidate_count']==full_trials[0]['candidate_count']
    assert len(candidates)==trials[0]['candidate_count']
    assert all(p.id.startswith('g0') for p in candidates)


def test_fast_overlap_retains_exact_area_and_boundary_behavior():
    shape=box(0,0,2,2)
    assert overlap_ratio(shape,box(3,0,4,1))==0
    assert overlap_ratio(shape,box(2,0,4,2))==0
    assert overlap_ratio(shape,box(1,0,3,2))==.5
    assert overlap_ratio(shape,box(-1,-1,3,3))==1
