import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import ProjectConfig,PanelSpec,DesignRequest,StressPreviewRequest,StressRequest
from app.services.optimizer import generate_design
from app.services.stress import preview_stress,run_stress_tests,SCENARIOS
from app.evidence import ProjectEvidence


@pytest.fixture(scope='module')
def original():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,geometry_confirmed=True,target_energy_kwh_year=10000)
    spec=PanelSpec();design=generate_design(DesignRequest(config=cfg,panel=spec))
    return StressRequest(config=cfg,panel=spec,design=design)


@pytest.mark.parametrize('sid',SCENARIOS)
def test_preview_uses_test_scenario_without_changing_original(original,sid):
    before=original.model_dump_json()
    req=StressPreviewRequest(**original.model_dump(),scenario_id=sid,date='2026-10-16',hour_local=9)
    preview=preview_stress(req)
    expected=next(s for s in run_stress_tests(original).scenarios if s.id==sid)
    assert preview['result'].status==expected.status
    assert preview['design'].metrics.annual_energy_kwh==expected.annual_energy_kwh
    assert [(p.x,p.y,p.rotation_deg) for p in preview['design'].panels]==[(p.x,p.y,p.rotation_deg) for p in original.design.panels]
    assert preview['scene']['sun']==preview['base_scene']['sun']
    assert original.model_dump_json()==before
    if sid=='panel1':assert preview['panel'].width_m==original.panel.width_m*1.01
    if sid=='roof2':assert preview['config'].roof_width_m==original.config.roof_width_m*.98
    if sid=='setback':assert preview['config'].setback_m==original.config.setback_m+.15
    if sid=='budget':assert preview['config'].budget_vnd==original.config.budget_vnd*.85


def test_preview_api_rejects_unknown_scenario_and_serializes_geometry(original):
    payload={**original.model_dump(mode='json'),'scenario_id':'bad','date':'2026-10-16','hour_local':9}
    client=TestClient(app)
    assert client.post('/api/design/stress-preview',json=payload).status_code==422
    payload['scenario_id']='setback'
    response=client.post('/api/design/stress-preview',json=payload)
    assert response.status_code==200
    assert response.json()['result']['id']=='setback'
    assert response.json()['scene']['usable_polygons']


def test_finance_and_datum_evidence_are_bounded_and_round_trip():
    values={'costs':[{'name':'Inverter','amount':None}],'years':25}
    evidence=ProjectEvidence(economic_assumptions=values,layout_datum={'vertex_index':1,'description':'Measured corner'})
    assert ProjectEvidence.model_validate(evidence.model_dump()).economic_assumptions.costs[0].amount is None
    with pytest.raises(ValueError):ProjectEvidence(economic_assumptions={**values,'years':10000})
    with pytest.raises(ValueError):ProjectEvidence(layout_datum={'vertex_index':-1})
