import hashlib
import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
from app import database
from app.main import app

PASSWORD='correct-horse-battery'
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SOLAROPT_DB_PATH',str(tmp_path/'accounts.db'))
    database.init_db()
    return TestClient(app,headers={'X-SolarOpt-Request':'1'})

def register(client,email='owner@example.com'):
    response=client.post('/api/auth/register',json={'email':email,'password':PASSWORD})
    assert response.status_code==201,response.text
    return response.json()

def test_account_lifecycle(client):
    user=register(client,'Owner@Example.com')
    assert user['email']=='owner@example.com'
    assert client.get('/api/auth/me').json()==user
    token=client.cookies.get('solaropt_session')
    with database.connect() as conn:
        hashed=conn.execute('SELECT password_hash FROM users').fetchone()[0]
        session=conn.execute('SELECT token_hash FROM sessions').fetchone()[0]
    assert PASSWORD not in hashed and hashed.startswith('scrypt$')
    assert session==hashlib.sha256(token.encode()).hexdigest()
    assert client.post('/api/auth/logout').status_code==200
    client.cookies.set('solaropt_session',token)
    assert client.get('/api/auth/me').status_code==401
    client.cookies.clear()
    for password,status in [('wrong-password',401),(PASSWORD,200)]:
        assert client.post('/api/auth/login',json={'email':user['email'],'password':password}).status_code==status

def test_history_isolation(client):
    legacy=database.save_version('Roof','design','legacy',{})
    owner=register(client)
    version=database.save_version('Roof','design','private',{'config':{'project_name':'Roof'}},owner['id'])
    database.init_db()
    assert [v['id'] for v in client.get('/api/history').json()]==[version]
    assert client.get(f'/api/projects/Roof/versions/{version}').status_code==200
    assert client.get(f'/api/projects/Roof/versions/{legacy}').status_code==404
    client.post('/api/auth/logout')
    assert client.get('/api/history').status_code==401
    register(client,'other@example.com')
    assert client.get('/api/projects/Roof/versions').json()==[]
    assert client.get(f'/api/projects/Roof/versions/{version}').status_code==404

def test_expiry_csrf_and_validation(client):
    register(client)
    assert client.post('/api/auth/register',json={'email':'owner@example.com','password':PASSWORD}).status_code==409
    with database.connect() as conn:
        conn.execute('UPDATE sessions SET expires_at=?',(int(time.time())-1,))
    assert client.get('/api/auth/me').status_code==401
    assert TestClient(app).post('/api/auth/login',json={'email':'x@example.com','password':PASSWORD}).status_code==403
    assert client.post('/api/auth/register',json={'email':'bad','password':'short'}).status_code==422

def test_rate_limit(client):
    with database.connect() as conn:
        conn.execute('INSERT INTO auth_attempts VALUES(?,?,?)',('testclient',int(time.time()),30))
    response=client.post('/api/auth/login',json={'email':'x@example.com','password':PASSWORD})
    assert response.status_code==429 and response.headers['retry-after']=='900'


def test_stale_tab_cannot_read_or_save_under_another_accounts_cookie(client,monkeypatch):
    from app import main
    owner=register(client)
    old_identity=str(owner['id'])
    client.post('/api/auth/logout')
    other=register(client,'other@example.com')
    monkeypatch.setattr(main,'generate_design',lambda req:pytest.fail('stale identity reached optimizer'))
    headers={'X-SolarOpt-User':old_identity}
    assert client.get('/api/history',headers=headers).status_code==401
    assert client.post('/api/design/generate',headers=headers,json={'config':{},'panel':{}}).status_code==401
    assert client.get('/api/history',headers={'X-SolarOpt-User':'guest'}).status_code==401
    assert database.list_versions(None,other['id'])==[]


def test_expired_or_missing_session_does_not_silently_downgrade_signed_in_designs(client,monkeypatch):
    from app import main
    owner=register(client)
    monkeypatch.setattr(main,'generate_design',lambda req:pytest.fail('expired session reached optimizer'))
    with database.connect() as conn:
        conn.execute('UPDATE sessions SET expires_at=?',(int(time.time())-1,))
    headers={'X-SolarOpt-User':str(owner['id'])}
    assert client.post('/api/design/generate',headers=headers,json={'config':{},'panel':{}}).status_code==401
    assert client.cookies.get('solaropt_session') is None
    client.cookies.clear()
    assert client.post('/api/design/generate',headers=headers,json={'config':{},'panel':{}}).status_code==401
    assert database.list_versions(None,owner['id'])==[]

def test_legacy_migration(tmp_path,monkeypatch):
    path=tmp_path/'legacy.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE project_versions (id INTEGER PRIMARY KEY, project_name TEXT, version_label TEXT, reason TEXT, payload_json TEXT, created_at TEXT)')
        conn.execute("INSERT INTO project_versions VALUES(1,'Roof','design','old','{}','2026-01-01')")
    monkeypatch.setenv('SOLAROPT_DB_PATH',str(path))
    database.init_db();database.init_db()
    assert database.get_version('Roof',1)['reason']=='old'
    with database.connect() as conn:
        assert conn.execute('SELECT user_id FROM project_versions').fetchone()[0] is None


def test_legacy_hash_still_logs_in_and_is_upgraded(client):
    from app.auth import SCRYPT
    user=register(client,'legacy@example.com')
    salt='00'*16
    legacy='scrypt$'+salt+'$'+hashlib.scrypt(PASSWORD.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    with database.connect() as conn:
        conn.execute('UPDATE users SET password_hash=? WHERE id=?',(legacy,user['id']))
    client.cookies.clear()
    assert client.post('/api/auth/login',json={'email':user['email'],'password':'wrong-password'}).status_code==401
    assert client.post('/api/auth/login',json={'email':user['email'],'password':PASSWORD}).status_code==200
    with database.connect() as conn:
        upgraded=conn.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()[0]
    assert upgraded.startswith('scrypt$%d$%d$%d$'%SCRYPT)
    client.cookies.clear()
    assert client.post('/api/auth/login',json={'email':user['email'],'password':PASSWORD}).status_code==200


def test_deployed_backend_reads_client_ip_from_caddy():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    dockerfile=(root/'deploy/Dockerfile.backend').read_text(encoding='utf-8')
    compose=(root/'compose.yaml').read_text(encoding='utf-8')
    assert '"--proxy-headers"' in dockerfile and '"--forwarded-allow-ips"' in dockerfile
    # Trusting forwarded headers is only safe while the backend publishes no port of its own.
    backend=compose.split('\n  web:')[0]
    assert 'ports:' not in backend
