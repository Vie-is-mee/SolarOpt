from datetime import date
import io
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.schemas import ProjectConfig, PanelSpec, RectObstacle, SunPosition, SceneRequest, DesignRequest, VerifyRequest, StressRequest
from app.services.geometry import build_context, shadow_polygon
from app.services.scene import simulate_scene
from app.services.optimizer import generate_design
from app.services.stress import run_stress_tests
from app.services.verifier import verify_design
from app.services import vision

@pytest.fixture
def client(tmp_path,monkeypatch):
    from app import database
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'test.db')
    database.init_db()
    return TestClient(app)

def test_neighbor_shadow_reaches_roof_and_uses_relative_height():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,roof_elevation_m=6)
    sun=SunPosition(altitude_deg=45,azimuth_deg=90,zenith_deg=45)
    high=RectObstacle(id='east',scope='neighbor',x=14,y=2,width_m=3,depth_m=5,height_m=20)
    low=high.model_copy(update={'height_m':5})
    assert build_context(cfg,[high],sun).shadow_union.intersection(build_context(cfg,[],None).roof).area>10
    assert shadow_polygon(low,sun,cfg) is None

def test_shadow_respects_drawing_north_rotation():
    sun=SunPosition(altitude_deg=45,azimuth_deg=90,zenith_deg=45)
    o=RectObstacle(id='tank',x=5,y=5,width_m=1,depth_m=1,height_m=2)
    plain=shadow_polygon(o,sun,ProjectConfig(north_rotation_deg=0))
    rotated=shadow_polygon(o,sun,ProjectConfig(north_rotation_deg=90))
    assert plain.bounds[0]==pytest.approx(3)
    assert rotated.bounds[1]==pytest.approx(3)
    assert rotated.bounds[0]==pytest.approx(5)

def test_shadow_on_inclined_plane_changes_projection():
    sun=SunPosition(altitude_deg=45,azimuth_deg=180,zenith_deg=45)
    o=RectObstacle(id='tank',x=5,y=5,height_m=2)
    flat=shadow_polygon(o,sun,ProjectConfig(roof_tilt_deg=0))
    tilted=shadow_polygon(o,sun,ProjectConfig(roof_tilt_deg=20,roof_azimuth_deg=180))
    # Roof rises toward north, so a northbound shadow intersects it sooner.
    assert tilted.bounds[3]<flat.bounds[3]

def test_empty_setback_remains_empty():
    cfg=ProjectConfig(roof_width_m=2,roof_height_m=2,setback_m=1.2)
    assert build_context(cfg,[],None).usable_roof.is_empty
    assert generate_design(DesignRequest(config=cfg,panel=PanelSpec())).metrics.panel_count==0

def test_zero_budget_never_selects_panels():
    result=generate_design(DesignRequest(config=ProjectConfig(budget_vnd=0),panel=PanelSpec()))
    assert result.metrics.panel_count==0

def test_non_rectangular_roof_is_respected():
    cfg=ProjectConfig(roof_polygon=[{'x':0,'y':0},{'x':10,'y':0},{'x':10,'y':4},{'x':5,'y':4},{'x':5,'y':8},{'x':0,'y':8}])
    result=generate_design(DesignRequest(config=cfg,panel=PanelSpec()))
    checked=verify_design(VerifyRequest(config=cfg,panel=PanelSpec(),design=result))
    assert result.metrics.panel_count>0
    assert checked.valid
    assert not any(p.x>5 and p.y>4 for p in result.panels)

@pytest.mark.parametrize('change',[{'roof_width_m':0},{'panel_gap_m':-.1},{'north_rotation_deg':360},{'latitude':float('nan')},{'roof_polygon':[{'x':0,'y':0},{'x':10,'y':8},{'x':0,'y':8},{'x':10,'y':0}]}])
def test_invalid_geometry_rejected(change):
    with pytest.raises((ValidationError,ValueError)):
        ProjectConfig(**change)

def test_midnight_has_zero_irradiance_and_full_darkness():
    result=simulate_scene(SceneRequest(config=ProjectConfig(),date=date(2026,10,10),hour_local=0))
    assert result['sun']['altitude_deg']<0
    assert result['plane_irradiance_w_m2']==0
    assert result['shaded_pct']==100
    assert all(cell['irradiance_w_m2']==0 for cell in result['cells'])

def test_sun_position_moves_east_to_west_and_fractional_hour_works():
    from app.schemas import SunRequest
    from app.services.solar import sun_position
    morning=sun_position(SunRequest(date=date(2026,10,10),hour_local=8))
    afternoon=sun_position(SunRequest(date=date(2026,10,10),hour_local=16))
    late=sun_position(SunRequest(date=date(2026,10,10),hour_local=23.99))
    assert 0<morning.azimuth_deg<180
    assert 180<afternoon.azimuth_deg<360
    assert late.altitude_deg<0

def test_stress_tests_original_design_not_reoptimized():
    cfg=ProjectConfig(budget_vnd=100_000_000)
    panel=PanelSpec()
    design=generate_design(DesignRequest(config=cfg,panel=panel))
    result=run_stress_tests(StressRequest(config=cfg,panel=panel,design=design))
    budget=next(s for s in result.scenarios if s.id=='budget')
    assert budget.status=='FAIL'
    assert all(s.panel_count==design.metrics.panel_count for s in result.scenarios)

def test_verification_rejects_tampered_metrics():
    cfg=ProjectConfig();panel=PanelSpec()
    design=generate_design(DesignRequest(config=cfg,panel=panel))
    design.metrics.estimated_cost_vnd=1
    checked=verify_design(VerifyRequest(config=cfg,panel=panel,design=design))
    assert not checked.valid

def test_approval_requires_confirmation_and_stores_full_inputs(client):
    cfg=ProjectConfig(); panel=PanelSpec()
    design=generate_design(DesignRequest(config=cfg,panel=panel))
    body={'config':cfg.model_dump(),'panel':panel.model_dump(),'obstacles':[],'design':design.model_dump()}
    assert client.post('/api/projects/approve',json=body).status_code==409
    body['config']['geometry_confirmed']=True
    assert client.post('/api/projects/approve',json=body).status_code==200
    versions=client.get('/api/projects/SolarOpt Demo/versions').json()
    assert versions[0]['payload']['config']['geometry_confirmed']
    assert 'design' in versions[0]['payload']

def test_scene_api_exposes_source_and_actual_polygons(client):
    result=client.post('/api/solar/scene',json={'config':ProjectConfig().model_dump(),'obstacles':[],'date':'2026-10-10','hour_local':9})
    assert result.status_code==200
    data=result.json()
    assert data['irradiance_source']=='pvlib_ineichen_clear_sky'
    assert data['plane_irradiance_w_m2']>0

def test_no_key_returns_manual_without_fabricated_obstacles(client,monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','groq');monkeypatch.delenv('GROQ_API_KEY',raising=False)
    result=client.post('/api/vision/analyze',files={'file':('roof.jpg',b'not-sent-to-ai','image/jpeg')})
    assert result.status_code==200
    assert result.json()['mode']=='manual'
    assert result.json()['obstacles']==[]

def image_bytes():
    from PIL import Image
    out=io.BytesIO();Image.new('RGB',(20,20),'white').save(out,format='PNG');return out.getvalue()

def test_vision_cache_and_partial_photo_requires_placement(client,monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','groq');monkeypatch.setenv('GROQ_API_KEY','test-not-real')
    vision._cache.clear();calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({'roof_width_m':None,'roof_height_m':None,'roof_confidence':.4,'obstacles':[{'id':'tank','label':'Bồn','x_pct':10,'y_pct':20,'width_pct':10,'depth_pct':10,'height_m':None,'confidence':.5}],'notes':[]})}}]}
    def post(*args,**kwargs):calls.append(kwargs);return Response()
    monkeypatch.setattr(vision.requests,'post',post)
    args={'files':{'file':('roof.png',image_bytes(),'image/png')},'data':{'input_kind':'partial'}}
    one=client.post('/api/vision/analyze',**args);two=client.post('/api/vision/analyze',**args)
    assert one.status_code==200,one.text
    assert len(calls)==1
    assert two.json()['cached']
    assert one.json()['obstacles'][0]['requires_placement']
    assert one.json()['obstacles'][0]['height_m'] is None

def test_provider_rate_limit_is_not_fake_success(client,monkeypatch):
    import requests
    monkeypatch.setenv('AI_PROVIDER','groq');monkeypatch.setenv('GROQ_API_KEY','test-429');vision._cache.clear()
    def post(*a,**kw):
        response=requests.Response();response.status_code=429
        raise requests.HTTPError(response=response)
    monkeypatch.setattr(vision.requests,'post',post)
    result=client.post('/api/vision/analyze',files={'file':('roof.png',image_bytes(),'image/png')})
    assert result.status_code==429
    assert 'mode' not in result.json()

def test_vision_rejects_invalid_coordinates(client,monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','groq');monkeypatch.setenv('GROQ_API_KEY','test-coords');vision._cache.clear()
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({'roof_confidence':.5,'obstacles':[{'id':'bad','label':'bad','x_pct':95,'y_pct':20,'width_pct':50,'depth_pct':10,'confidence':.5}]})}}]}
    monkeypatch.setattr(vision.requests,'post',lambda *a,**kw:Response())
    result=client.post('/api/vision/analyze',files={'file':('roof.png',image_bytes(),'image/png')})
    assert result.status_code==502


def test_repair_traces_roof_and_panel_changes(client):
    cfg=ProjectConfig(geometry_confirmed=True);panel=PanelSpec()
    design=generate_design(DesignRequest(config=cfg,panel=panel))
    result=client.post('/api/design/repair',json={
        'config':{**cfg.model_dump(),'north_rotation_deg':90,'budget_vnd':90_000_000},
        'panel':{**panel.model_dump(),'power_w':600},
        'previous_config':cfg.model_dump(),'previous_panel':panel.model_dump(),
        'obstacles_before':[],'obstacles_after':[],'previous_design':design.model_dump(),
    })
    assert result.status_code==200,result.text
    impact=result.json()['impact']
    assert all(node in impact['changed_input'] for node in ['roof_orientation','budget','panel_spec'])
    assert 'shadow_map' in impact['affected_nodes']
    assert 'electrical' not in impact['affected_nodes']


def test_import_validation_rejects_invalid_panel(client):
    body={'config':ProjectConfig().model_dump(),'panel':{**PanelSpec().model_dump(),'width_m':-1},'obstacles':[]}
    assert client.post('/api/projects/validate',json=body).status_code==422


@pytest.mark.parametrize('points',[
    [{'x':-1,'y':0},{'x':100,'y':0},{'x':100,'y':100}],
    [{'x':0,'y':0},{'x':100,'y':100},{'x':0,'y':100},{'x':100,'y':0}],
])
def test_ai_polygon_requires_valid_normalized_geometry(points):
    from app.schemas import VisionResult
    with pytest.raises(ValidationError):
        VisionResult(mode='groq',obstacles=[],roof_polygon_pct=points)
