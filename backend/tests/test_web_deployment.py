from fastapi.testclient import TestClient
from app import database
from app.main import app, compute_slots


def test_database_path_environment_persists(monkeypatch, tmp_path):
    target = tmp_path / "persistent" / "studio.db"
    monkeypatch.setenv("SOLAROPT_DB_PATH", str(target))
    database.init_db()
    version = database.save_version("deployment-test", "v1", "test", {"input": 1})
    database.init_db()
    assert database.list_versions("deployment-test")[0]["id"] == version
    assert target.exists()


def test_busy_compute_returns_retryable_response():
    assert compute_slots.acquire(blocking=False)
    try:
        response = TestClient(app).post("/api/design/generate", json={})
        assert response.status_code == 429
        assert response.headers["retry-after"] == "5"
        assert TestClient(app).get("/api/health").status_code == 200
    finally:
        compute_slots.release()
