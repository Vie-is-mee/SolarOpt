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
    monkeypatch.setattr(main, 'generate_design', lambda req: DESIGN.model_copy(deep=True))
    database.init_db()
    return TestClient(main.app, headers={'X-SolarOpt-Request': '1'})


def register(client, email):
    assert client.post('/api/auth/register', json={'email': email, 'password': PASSWORD}).status_code == 201


def make_admin(api, email='admin@example.com'):
    admin = TestClient(main.app, headers={'X-SolarOpt-Request': '1'})
    register(admin, email)
    with database.connect() as conn:
        conn.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
    return admin


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
    admin = make_admin(api)
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


def test_admin_is_unlimited_and_rights_come_only_from_the_database(api):
    register(api, 'owner@example.com')
    assert api.get('/api/admin/users').status_code == 403
    with database.connect() as conn:
        conn.execute("UPDATE users SET role='admin'")
    for i in range(8):
        assert design(api, f'Dự án quản trị {i}').status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'admin' and usage['is_admin'] and usage['limits']['projects'] is None


def test_team_pools_quota_shares_history_and_respects_seats(api):
    owner = TestClient(main.app, headers={'X-SolarOpt-Request': '1'}); register(owner, 'boss@example.com')
    eng = TestClient(main.app, headers={'X-SolarOpt-Request': '1'}); register(eng, 'eng@example.com')
    other = TestClient(main.app, headers={'X-SolarOpt-Request': '1'}); register(other, 'other@example.com')
    assert owner.post('/api/account/upgrade-request', json={'plan': 'business'}).status_code == 409   # needs a team first
    team = owner.post('/api/team', json={'name': 'Công ty Nắng'}).json()
    assert team['role'] == 'owner' and team['seats'] == 1
    assert owner.post('/api/team/members', json={'email': 'eng@example.com'}).status_code == 402      # free team: 1 seat
    assert owner.post('/api/account/upgrade-request', json={'plan': 'business'}).status_code == 201
    admin = make_admin(api)
    listed = {t['name']: t for t in admin.get('/api/admin/teams').json()}
    assert listed['Công ty Nắng']['pending_request']['plan'] == 'business'
    assert admin.post(f"/api/admin/teams/{team['id']}/plan", json={'plan': 'business', 'months': 1}).status_code == 200
    assert owner.post('/api/team/members', json={'email': 'nobody@example.com'}).status_code == 404
    assert owner.post('/api/team/members', json={'email': 'eng@example.com'}).json()['members'][1]['email'] == 'eng@example.com'
    assert eng.post('/api/team/members', json={'email': 'other@example.com'}).status_code == 403          # members cannot add
    assert design(eng, 'Nhà xưởng A').status_code == 200
    assert design(owner, 'Nhà xưởng A').status_code == 200                                               # same project, one use
    usage = owner.get('/api/account/usage').json()
    assert usage['plan'] == 'business' and usage['used']['projects'] == 1 and usage['limits']['projects'] == 300
    assert any(v['project_name'] == 'Nhà xưởng A' for v in owner.get('/api/history').json())             # engineer's version visible
    assert other.get('/api/history').json() == []                                                        # outsiders see nothing
    eng_member = [m for m in owner.get('/api/team').json()['members'] if m['email'] == 'eng@example.com'][0]
    assert owner.post(f"/api/team/members/{eng_member['id']}/remove").status_code == 200
    assert eng.get('/api/account/usage').json()['plan'] == 'free'
    assert owner.post('/api/team/leave').status_code == 200 and owner.get('/api/team').json() is None
