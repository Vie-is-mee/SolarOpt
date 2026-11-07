import json
import time

import pytest
from fastapi.testclient import TestClient

from app import billing, database, main
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


def design(client, name, **where):
    body = {'config': ProjectConfig(project_name=name, **where).model_dump(), 'panel': PanelSpec().model_dump(), 'obstacles': []}
    return client.post('/api/design/generate', json=body)


def test_guest_gets_two_projects_per_day_and_reruns_are_free(api):
    assert design(api, 'Nhà A').status_code == 200
    assert design(api, 'nhà  a ').status_code == 200          # same project, normalised name
    assert design(api, 'Nhà B').status_code == 200
    blocked = design(api, 'Nhà C')
    assert blocked.status_code == 402 and 'Đăng ký' in blocked.json()['detail']
    assert design(api, 'Nhà A').status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'guest' and usage['used']['projects'] == 2 and usage['limits']['chat'] == 0


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


def test_chat_ai_needs_an_account_and_stops_at_the_plan_quota(api, monkeypatch):
    from app.services import assistant
    calls = []

    class Fake:
        model = 'fake-model'
        def chat(self, messages, tools=None, json_mode=False):
            calls.append(1)
            return {'content': 'Mái này xếp được số tấm như phương án đã tính.'}
    monkeypatch.setattr(assistant, 'assistant_client', lambda: Fake())
    cfg = ProjectConfig(roof_width_m=5, roof_height_m=4, budget_vnd=1e12)
    body = {'messages': [{'role': 'user', 'content': 'Vì sao chỉ lắp được bấy nhiêu tấm?'}], 'config': cfg.model_dump(),
            'panel': PanelSpec().model_dump(), 'obstacles': [], 'design': DESIGN.model_dump()}
    guest = api.post('/api/assistant/chat', json=body).json()
    assert guest['mode'] == 'rules' and 'Đăng nhập' in guest['notice'] and calls == []      # no paid call for guests
    register(api, 'chat@example.com')
    assert api.post('/api/assistant/chat', json=body).json()['mode'] == 'llm' and len(calls) == 1
    assert api.get('/api/account/usage').json()['used']['chat'] == 1
    with database.connect() as conn:
        conn.executemany("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,NULL,?)",
                         [('u:1', 'chat', int(time.time()))] * 29)
    over = api.post('/api/assistant/chat', json=body).json()
    assert over['mode'] == 'rules' and 'hết 30' in over['notice'] and len(calls) == 1      # free plan: 30 AI answers


def test_trial_account_has_one_project_then_must_buy_a_plan(api):
    register(api, 'free@example.com')
    assert design(api, 'Dự án 0').status_code == 200
    assert design(api, 'Dự án 1').status_code == 402
    assert design(api, 'Dự án 0').status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'free' and usage['used']['projects'] == 1 and usage['limits']['projects'] == 1


def test_upgrade_request_admin_activation_and_expiry(api):
    register(api, 'eng@example.com')
    assert api.post('/api/account/upgrade-request', json={'plan': 'single', 'note': 'Nhà xưởng 500 kWp'}).status_code == 201
    assert api.get('/api/account/usage').json()['pending_request'] == 'single'
    assert api.get('/api/admin/users').status_code == 403
    admin = make_admin(api)
    users = {u['email']: u for u in admin.get('/api/admin/users').json()}
    assert users['eng@example.com']['pending_request']['plan'] == 'single'
    uid = users['eng@example.com']['id']
    assert admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'single', 'periods': 1}).status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'single' and usage['limits']['projects'] == 1 and usage['pending_request'] is None
    plans = usage['plans']
    assert [plans[k]['price_vnd'] for k in ('single', 'start', 'team', 'pro')] == [5_990_000, 17_900_000, 34_900_000, 54_900_000]
    assert [plans[k]['projects'] for k in ('single', 'start', 'team', 'pro')] == [1, 8, 24, 60]
    assert [plans[k]['seats'] for k in ('single', 'start', 'team', 'pro')] == [1, 2, 5, 10]
    assert set(plans) == {'free', 'single', 'start', 'team', 'pro'} and plans['start']['period'] == 'year'
    assert [t['fee_vnd_month'] for t in usage['storage_terms']['tiers']] == [299_000, 599_000, 899_000, 1_490_000]
    with database.connect() as conn:
        conn.execute('UPDATE users SET plan_until=? WHERE id=?', (int(time.time()) - 1, uid))
    assert api.get('/api/account/usage').json()['plan'] == 'free'
    assert admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'gold'}).status_code == 422
    assert admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'start', 'periods': 2}).json()['plan_until'] > time.time() + 700 * 86400


def test_cycle_resets_allowance_and_a_name_at_another_place_is_a_new_project(api):
    register(api, 'cycle@example.com')
    admin = make_admin(api)
    uid = {u['email']: u['id'] for u in admin.get('/api/admin/users').json()}['cycle@example.com']
    admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'single', 'periods': 3})
    assert design(api, 'Nhà A').status_code == 200
    assert design(api, 'Nhà A', latitude=21.03, longitude=105.85).status_code == 402      # same name, roof in Hà Nội
    assert design(api, 'Nhà B').status_code == 402
    with database.connect() as conn:                                                        # 31 days later: second month
        conn.execute('UPDATE users SET plan_started=plan_started-? WHERE id=?', (31 * 86400, uid))
        conn.execute('UPDATE usage_events SET created_at=created_at-?', (31 * 86400,))
    assert api.get('/api/account/usage').json()['used']['projects'] == 0
    assert design(api, 'Nhà B').status_code == 200
    assert design(api, 'Nhà A').status_code == 200                                          # same job next month: not charged twice
    assert api.get('/api/account/usage').json()['used']['projects'] == 1
    with database.connect() as conn:                                                        # after a year it is a new use
        conn.execute("UPDATE usage_events SET created_at=created_at-? WHERE project_key LIKE 'nhà a%'", (366 * 86400,))
    assert design(api, 'Nhà A').status_code == 402


def test_project_data_is_kept_while_paid_then_hidden_and_purged(api):
    from scripts import purge_expired_projects
    register(api, 'store@example.com')
    admin = make_admin(api)
    uid = {u['email']: u['id'] for u in admin.get('/api/admin/users').json()}['store@example.com']
    admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'single', 'periods': 1})
    assert design(api, 'Kho Bình Dương').status_code == 200
    stored = api.get('/api/account/storage').json()
    assert stored['grace_days'] == 30 and len(stored['projects']) == 1
    project = stored['projects'][0]
    assert project['state'] == 'included' and project['covered_until'] > time.time() + 29 * 86400
    version = api.get('/api/history').json()[0]
    assert version['project_key'] == project['project_key']

    def age(days):   # the cycle that covered the project ended `days` ago, and storage was not paid
        with database.connect() as conn:
            conn.execute('UPDATE project_storage SET covered_until=?', (int(time.time()) - days * 86400,))
    age(1)
    assert api.get('/api/account/storage').json()['projects'][0]['state'] == 'grace'
    assert api.get('/api/account/usage').json()['storage_due'] == 1 and len(api.get('/api/history').json()) == 1
    age(31)
    assert api.get('/api/history').json() == []
    assert api.get(f"/api/projects/Kho Bình Dương/versions/{version['id']}").status_code == 410
    assert api.post('/api/account/storage-request', json={'months': 3}).json()['fee_vnd'] == 3 * 299_000
    assert api.get('/api/account/storage').json()['pending_months'] == 3
    assert admin.get('/api/admin/storage').json()['accounts'][0]['pending_months'] == 3
    extended = admin.post('/api/admin/storage', json={'owner': f'u:{uid}', 'months': 3}).json()
    assert extended['storage_until'] > time.time() + 89 * 86400
    assert api.get('/api/account/storage').json()['projects'][0]['state'] == 'paid' and len(api.get('/api/history').json()) == 1
    with database.connect() as conn:
        conn.execute('UPDATE project_storage SET storage_until=?', (int(time.time()) - 31 * 86400,))
    purge_expired_projects.main(apply=False)
    assert len(api.get('/api/projects/Kho Bình Dương/versions').json()) == 0          # hidden, still on disk
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM project_versions').fetchone()[0] == 1
    purge_expired_projects.main(apply=True)
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM project_versions').fetchone()[0] == 0
    assert api.get('/api/account/storage').json()['projects'][0]['state'] == 'purged'
    assert admin.post('/api/admin/storage', json={'owner': f'u:{uid}', 'months': 1}).status_code == 404
    assert api.post('/api/account/storage-request', json={'months': 1}).status_code == 409


@pytest.mark.parametrize('projects,fee', [(0, 0), (1, 299_000), (8, 299_000), (9, 599_000), (24, 599_000), (25, 899_000), (60, 899_000), (61, 1_490_000), (150, 1_490_000), (151, None)])
def test_storage_fee_follows_the_tier_of_the_project_count(projects, fee):
    assert billing.storage_fee(projects) == fee


def test_twelve_months_of_storage_bill_ten():
    assert [billing.storage_bill(9, m) for m in (1, 6, 12, 24)] == [599_000, 6 * 599_000, 10 * 599_000, 20 * 599_000]
    assert billing.storage_bill(151, 12) is None


def test_an_active_yearly_plan_keeps_as_many_stored_projects_free_as_it_sells(api):
    register(api, 'renew@example.com')
    admin = make_admin(api)
    uid = {u['email']: u['id'] for u in admin.get('/api/admin/users').json()}['renew@example.com']
    admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'start', 'periods': 1})
    with database.connect() as conn:
        for i in range(10):
            conn.execute('INSERT INTO project_storage(owner,project_key,project_name,first_used,covered_until) VALUES(?,?,?,?,?)',
                         (f'u:{uid}', f'cu {i}', f'Dự án cũ {i}', int(time.time()) - 500 * 86400 - i, int(time.time()) - 10 * 86400))
    stored = api.get('/api/account/storage').json()
    assert [p['state'] for p in stored['projects']] == ['included'] * 8 + ['grace'] * 2
    assert stored['projects'][0]['project_name'] == 'Dự án cũ 0' and stored['billable'] == 2 and stored['fee_vnd_month'] == 299_000
    with database.connect() as conn:
        conn.execute('UPDATE users SET plan_until=? WHERE id=?', (int(time.time()) - 1, uid))
    stored = api.get('/api/account/storage').json()
    assert stored['billable'] == 10 and stored['fee_vnd_month'] == 599_000


def test_retired_plans_are_not_sold_but_an_account_keeps_theirs_until_it_ends(api):
    register(api, 'old@example.com')
    assert api.post('/api/account/upgrade-request', json={'plan': 'year_7'}).status_code == 422
    admin = make_admin(api)
    uid = {u['email']: u['id'] for u in admin.get('/api/admin/users').json()}['old@example.com']
    assert admin.post(f'/api/admin/users/{uid}/plan', json={'plan': 'year_7', 'periods': 1}).status_code == 422
    with database.connect() as conn:
        conn.execute("UPDATE users SET plan='year_7', plan_started=?, plan_until=? WHERE id=?", (int(time.time()), int(time.time()) + 86400, uid))
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'year_7' and usage['limits']['projects'] == 7 and 'year_7' not in usage['plans']


def test_admin_is_unlimited_and_rights_come_only_from_the_database(api):
    register(api, 'owner@example.com')
    assert api.get('/api/admin/users').status_code == 403
    with database.connect() as conn:
        conn.execute("UPDATE users SET role='admin'")
    for i in range(8):
        assert design(api, f'Dự án quản trị {i}').status_code == 200
    usage = api.get('/api/account/usage').json()
    assert usage['plan'] == 'admin' and usage['is_admin'] and usage['limits']['projects'] is None
    assert api.get('/api/account/storage').json()['unlimited'] is True
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM project_storage').fetchone()[0] == 0     # admin data never expires


def test_team_pools_quota_shares_history_and_respects_seats(api):
    owner = TestClient(main.app, headers={'X-SolarOpt-Request': '1'}); register(owner, 'boss@example.com')
    eng = TestClient(main.app, headers={'X-SolarOpt-Request': '1'}); register(eng, 'eng@example.com')
    other = TestClient(main.app, headers={'X-SolarOpt-Request': '1'}); register(other, 'other@example.com')
    team = owner.post('/api/team', json={'name': 'Công ty Nắng'}).json()
    assert team['role'] == 'owner' and team['seats'] == 1
    assert owner.post('/api/team/members', json={'email': 'eng@example.com'}).status_code == 402      # unpaid team: 1 seat
    assert owner.post('/api/account/upgrade-request', json={'plan': 'team'}).status_code == 201
    admin = make_admin(api)
    listed = {t['name']: t for t in admin.get('/api/admin/teams').json()}
    assert listed['Công ty Nắng']['pending_request']['plan'] == 'team'
    assert admin.post(f"/api/admin/teams/{team['id']}/plan", json={'plan': 'team', 'periods': 1}).status_code == 200
    assert owner.post('/api/team/members', json={'email': 'nobody@example.com'}).status_code == 404
    assert owner.post('/api/team/members', json={'email': 'eng@example.com'}).json()['members'][1]['email'] == 'eng@example.com'
    assert eng.post('/api/team/members', json={'email': 'other@example.com'}).status_code == 403          # members cannot add
    assert design(eng, 'Nhà xưởng A').status_code == 200
    assert design(owner, 'Nhà xưởng A').status_code == 200                                               # same project, one use
    usage = owner.get('/api/account/usage').json()
    assert usage['plan'] == 'team' and usage['used']['projects'] == 1 and usage['limits']['projects'] == 24
    assert any(v['project_name'] == 'Nhà xưởng A' for v in owner.get('/api/history').json())             # engineer's version visible
    assert other.get('/api/history').json() == []                                                        # outsiders see nothing
    eng_member = [m for m in owner.get('/api/team').json()['members'] if m['email'] == 'eng@example.com'][0]
    assert owner.post(f"/api/team/members/{eng_member['id']}/remove").status_code == 200
    assert eng.get('/api/account/usage').json()['plan'] == 'free'
    assert owner.post('/api/team/leave').status_code == 200 and owner.get('/api/team').json() is None
