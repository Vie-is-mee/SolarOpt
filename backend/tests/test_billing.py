import json
import time

import pytest
from fastapi.testclient import TestClient

from app import database, main
from app.schemas import DesignRequest, PanelSpec, ProjectConfig
from app.services import vision
from app.services.optimizer import generate_design

PASSWORD = 'correct-horse-battery'
DESIGN = generate_design(DesignRequest(config=ProjectConfig(roof_width_m=5, roof_height_m=4, budget_vnd=1e12), panel=PanelSpec(), obstacles=[]))


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('SOLAROPT_DB_PATH', str(tmp_path / 'billing.db'))
    monkeypatch.setenv('SOLAROPT_ADMIN_EMAILS', 'admin@example.com')
    monkeypatch.setattr(main, 'generate_design', lambda req: DESIGN.model_copy(deep=True))
    database.init_db()
    return TestClient(main.app, headers={'X-SolarOpt-Request': '1'})


def register(client, email):
    assert client.post('/api/auth/register', json={'email': email, 'password': PASSWORD}).status_code == 201


def design(client, name):
    body = {'config': ProjectConfig(project_name=name).model_dump(), 'panel': PanelSpec().model_dump(), 'obstacles': []}
    return client.post('/api/design/generate', json=body)


def test_guest_gets_two_projects_per_day_and_reruns_are_free(api):
    assert design(api, 'Nhà A').status_code == 200
    assert design(api, 'nhà  a ').status_code == 200          # same project, normalised name
    assert design(api, 'Nhà B').status_code == 200
    blocked = design(api, 'Nhà C')
    assert blocked.status_code == 402 and 'Đăng ký' in blocked.json()['detail']
    assert design(api, 'Nhà A').status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'guest' and usage['used']['projects'] == 2


def test_free_account_has_five_projects_then_must_upgrade(api):
    register(api, 'free@example.com')
    for i in range(5):
        assert design(api, f'Dự án {i}').status_code == 200
    assert design(api, 'Dự án 5').status_code == 402
    assert design(api, 'Dự án 0').status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'free' and usage['used']['projects'] == 5 and usage['limits']['projects'] == 5


def test_ai_reads_need_login_and_are_counted_only_when_billed(api, monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'groq'); monkeypatch.setenv('GROQ_API_KEY', 'test-billing'); vision._cache.clear()

    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices': [{'message': {'content': json.dumps({'roof_confidence': .5, 'obstacles': []})}}]}
    monkeypatch.setattr(vision.requests, 'post', lambda *a, **kw: Response())
    from tests.test_studio import image_bytes
    upload = lambda: api.post('/api/vision/analyze', files={'file': ('roof.png', image_bytes(), 'image/png')})
    assert upload().status_code == 401
    register(api, 'ai@example.com')
    assert upload().status_code == 200
    assert upload().json()['cached'] is True                   # same image again: cached, not billed
    assert api.get('/api/account/usage').json()['used']['ai_reads'] == 1
    with database.connect() as conn:
        conn.executemany("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,NULL,?)",
                         [('u:1', 'ai', int(time.time()))] * 9)
    assert upload().status_code == 402


def test_upgrade_request_admin_activation_and_expiry(api):
    register(api, 'eng@example.com')
    assert api.post('/api/account/upgrade-request', json={'plan': 'pro', 'note': 'Đội 2 kỹ sư'}).status_code == 201
    assert api.get('/api/account/usage').json()['pending_request'] == 'pro'
    assert api.get('/api/admin/users').status_code == 403
    admin = TestClient(main.app, headers={'X-SolarOpt-Request': '1'})
    register(admin, 'admin@example.com')
    users = {u['email']: u for u in admin.get('/api/admin/users').json()}
    assert users['eng@example.com']['pending_request']['plan'] == 'pro'
    uid = users['eng@example.com']['id']
    assert admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'pro', 'months': 1}).status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'pro' and usage['limits']['projects'] == 30 and usage['pending_request'] is None
    with database.connect() as conn:
        conn.execute('UPDATE users SET plan_until=? WHERE id=?', (int(time.time()) - 1, uid))
    assert api.get('/api/account/usage').json()['plan'] == 'free'
    assert admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'gold'}).status_code == 422
