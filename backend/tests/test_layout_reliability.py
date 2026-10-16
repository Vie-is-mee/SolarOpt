from app.schemas import ProjectConfig,PanelSpec,DesignRequest,VerifyRequest
from app.services.optimizer import generate_design
from app.services.verifier import verify_design


def rectangle(left,right):
    return [{'x':left,'y':0},{'x':right,'y':0},{'x':right,'y':9},{'x':left,'y':9}]


def test_narrow_installable_face_between_forbidden_faces_is_not_missed():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,setback_m=.01,layout_angle_deg=0,
        geometry_confirmed=True,roof_faces=[
            {'id':'left','label':'Excluded','polygon':rectangle(0,3.21),'installable':False},
            {'id':'strip','label':'Narrow roof','polygon':rectangle(3.21,4.41)},
            {'id':'right','label':'Excluded','polygon':rectangle(4.41,12),'installable':False}])
    spec=PanelSpec();result=generate_design(DesignRequest(config=cfg,panel=spec))
    assert len(result.panels)==3
    assert all(p.face_id=='strip' for p in result.panels)
    assert verify_design(VerifyRequest(config=cfg,panel=spec,design=result)).valid


def test_solver_timeout_preserves_feasible_grid(monkeypatch):
    from app.services import optimizer
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,geometry_confirmed=True,target_energy_kwh_year=10000)
    class TimedOutSolver:
        def __init__(self):
            from types import SimpleNamespace
            self.parameters=SimpleNamespace()
        def Solve(self,model):return optimizer.cp_model.UNKNOWN
        def StatusName(self,status):return 'UNKNOWN'
    monkeypatch.setattr(optimizer.cp_model,'CpSolver',TimedOutSolver)
    for goal in ('max_energy','min_cost','robust'):
        req=DesignRequest(config=cfg,panel=PanelSpec(),objective=goal)
        result=generate_design(req)
        assert result.panels
        assert result.solver_status=='GREEDY_FALLBACK'
        assert any('UNKNOWN' in warning for warning in result.warnings)
        assert verify_design(VerifyRequest(config=cfg,panel=req.panel,design=result)).valid
