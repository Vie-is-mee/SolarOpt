import base64
import io
import pytest
from PIL import Image
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.evidence import ProjectEvidence
from app.schemas import ProjectConfig,PanelSpec,DesignRequest
from app.services.optimizer import generate_design


def evidence():
    stream=io.BytesIO();Image.new('RGB',(40,20),'green').save(stream,'PNG')
    image='data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()
    return dict(source_name='roof.png',input_kind='drone',source_image=image,reference_image=image,
        calibration=dict(captured_at='2026-10-16T03:00:00Z',method='manual_image_trace',image_width_px=40,image_height_px=20,
            reference_points=[dict(x=10,y=10),dict(x=90,y=10)],reference_m=8,
            result_width_m=10,result_height_m=5,measured_width_m=10,measured_length_m=5,frame_error_pct=0))


@pytest.mark.parametrize('image',['https://example.com/a.png','data:image/svg+xml;base64,PHN2Zz4=','data:image/png;base64,YWJj','data:image/jpeg;base64,???'])
def test_rejects_remote_or_non_image_evidence(image):
    with pytest.raises(ValidationError):ProjectEvidence(**{**evidence(),'source_image':image})


def test_rejects_unpaired_measurement_and_wrong_image_dimensions():
    data=evidence();data['calibration']['reference_points'].pop()
    with pytest.raises(ValidationError):ProjectEvidence(**data)
    data=evidence();data['calibration']['image_width_px']=41
    with pytest.raises(ValidationError):ProjectEvidence(**data)


def test_evidence_is_json_serializable_and_accepts_legacy_absence():
    item=ProjectEvidence(**evidence())
    assert ProjectEvidence.model_validate_json(item.model_dump_json())==item
    assert DesignRequest(config=ProjectConfig(),panel=PanelSpec()).evidence is None


def test_version_list_excludes_image_bytes_and_detail_preserves_evidence(tmp_path,monkeypatch):
    from app import database,main
    monkeypatch.setenv('SOLAROPT_DB_PATH',str(tmp_path/'versions.db'));database.init_db()
    client=TestClient(main.app,headers={'X-SolarOpt-Request':'1'})
    user=client.post('/api/auth/register',json={'email':'evidence@example.com','password':'long-test-password'}).json()
    full=evidence()
    version_id=database.save_version('Roof A','design','test',{'evidence':full,'config':{'project_name':'Roof A'}},user['id'])
    listed=database.list_versions('Roof A',user['id'])[0]
    assert listed['has_evidence']
    assert listed['payload']['evidence']['source_image'] is None
    assert database.get_version('Roof A',version_id,user['id'])['payload']['evidence']==full
    assert database.get_version('Roof B',version_id) is None
    assert client.get(f'/api/projects/Roof%20A/versions/{version_id}').json()['payload']['evidence']==full
    assert client.get(f'/api/projects/Roof%20B/versions/{version_id}').status_code==404


def test_design_and_approval_save_same_calibration_evidence(tmp_path,monkeypatch):
    from app import database,main
    monkeypatch.setenv('SOLAROPT_DB_PATH',str(tmp_path/'versions.db'));database.init_db()
    cfg=ProjectConfig(project_name='Evidence flow',geometry_confirmed=True,dimensions_source='measured',dimensions_verified=True)
    spec=PanelSpec();request=DesignRequest(config=cfg,panel=spec,objective='max_energy')
    design=generate_design(request)
    monkeypatch.setattr(main,'generate_design',lambda req:design)
    client=TestClient(main.app,headers={'X-SolarOpt-Request':'1'})
    user=client.post('/api/auth/register',json={'email':'evidence@example.com','password':'long-test-password'}).json()
    body={**request.model_dump(mode='json'),'evidence':evidence()}
    result=client.post('/api/design/generate',json=body)
    assert result.status_code==200,result.text
    saved=database.get_version(cfg.project_name,database.list_versions(cfg.project_name,user['id'])[0]['id'],user['id'])
    assert saved['payload']['evidence']['source_image']==evidence()['source_image']
    approved=client.post('/api/projects/approve',json={**body,'design':design.model_dump(mode='json')})
    assert approved.status_code==200,approved.text
    payload=database.get_version(cfg.project_name,approved.json()['version_id'],user['id'])['payload']
    assert payload['evidence']['calibration']['reference_m']==8
