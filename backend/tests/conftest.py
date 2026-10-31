import pytest
from fastapi.testclient import TestClient
from app import database
from app.main import app

@pytest.fixture
def authenticated_client(tmp_path, monkeypatch):
    monkeypatch.setenv('SOLAROPT_DB_PATH', str(tmp_path / 'authenticated.db'))
    database.init_db()
    client = TestClient(app, headers={'X-SolarOpt-Request': '1'})
    response = client.post('/api/auth/register', json={'email': 'tester@example.com', 'password': 'test-password-long'})
    assert response.status_code == 201, response.text
    return client
