import io
import json

import pytest
from fastapi.testclient import TestClient

from app import demo
from app.main import app
from app.services import vision


@pytest.fixture(autouse=True)
def recordings(tmp_path, monkeypatch):
    """Each test gets its own recordings folder and never calls a live model."""
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setenv("AI_PROVIDER", "none")
    monkeypatch.delenv("SOLAROPT_DEMO_RECORD", raising=False)
    return tmp_path


def png():
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(out, format="PNG")
    return out.getvalue()


def advisor_body(**extra):
    return {"config": {"project_name": "Demo", "roof_width_m": 12, "roof_height_m": 9, "geometry_confirmed": True},
            "panel": {}, "obstacles": [], "need": "min_cost", "customer": {"monthly_bill_vnd": 2_500_000}, **extra}


def test_matching_vision_recording_replays_without_login_or_model(recordings, monkeypatch):
    files = [(png(), "image/png")]
    key = demo.vision_key(files, "drone", 12.0, 9.0)
    recorded = {"mode": "openai", "model": "gemma", "roof_confidence": 0.9, "obstacles": [], "notes": ["n"], "input_kind": "drone"}
    demo.save("vision", key, recorded, "gemma", 201_000)
    monkeypatch.setattr(vision.requests, "post", lambda *a, **k: pytest.fail("model must not be called"))
    client = TestClient(app, headers={"X-SolarOpt-Request": "1"})
    args = {"files": {"file": ("roof.png", files[0][0], "image/png")}, "data": {"input_kind": "drone", "roof_width_m": "12", "roof_height_m": "9"}}
    replay = client.post("/api/vision/analyze", data={**args["data"], "demo_mode": "true"}, files=args["files"])
    assert replay.status_code == 200, replay.text
    body = replay.json()
    assert body["mode"] == "openai" and "Phát lại" in body["replay"] and "gemma" in body["replay"] and "201 giây" in body["replay"]
    # Outside demo mode, or with another size, nothing is replayed: the live path still needs an account.
    assert client.post("/api/vision/analyze", **args).status_code == 401
    other = {**args["data"], "roof_width_m": "10", "demo_mode": "true"}
    assert client.post("/api/vision/analyze", data=other, files=args["files"]).status_code == 401


def test_advisor_replays_only_the_exact_inputs_it_recorded(recordings):
    from app.services.advisor.models import AdvisorRequest
    client = TestClient(app, headers={"X-SolarOpt-Request": "1"})
    live = client.post("/api/advisor/propose", json=advisor_body())
    assert live.status_code == 200 and live.json()["replay"] == ""
    recorded = {**live.json(), "mode": "llm", "model": "nemotron", "summary": "Bản ghi"}
    demo.save("advisor", demo.advisor_key(AdvisorRequest.model_validate(advisor_body())), recorded, "nemotron", 40_000)
    replay = client.post("/api/advisor/propose", json=advisor_body(demo=True)).json()
    assert replay["summary"] == "Bản ghi" and "nemotron" in replay["replay"]
    # Budget and target do not change the key (the advisor proposes them); the customer's bill does.
    moved = advisor_body(demo=True)
    moved["config"]["budget_vnd"] = 1
    assert client.post("/api/advisor/propose", json=moved).json()["summary"] == "Bản ghi"
    other = advisor_body(demo=True, customer={"monthly_bill_vnd": 3_000_000})
    assert client.post("/api/advisor/propose", json=other).json()["replay"] == ""
    # Without demo mode the same inputs run live.
    assert client.post("/api/advisor/propose", json=advisor_body()).json()["replay"] == ""


def test_obstacle_ids_minted_per_session_do_not_change_the_key():
    from app.services.advisor.models import AdvisorRequest
    body = advisor_body(obstacles=[{"id": "ai-0-1793686928950", "label": "Bồn", "x": 6.5, "y": 5, "width_m": 1.5, "depth_m": 2, "height_m": 1}])
    again = advisor_body(obstacles=[{**body["obstacles"][0], "id": "ai-0-1793699999999"}])
    moved = advisor_body(obstacles=[{**body["obstacles"][0], "x": 7.5}])
    key = lambda b: demo.advisor_key(AdvisorRequest.model_validate(b))
    assert key(body) == key(again) and key(body) != key(moved)


def test_recording_saves_only_model_answers(recordings, monkeypatch):
    monkeypatch.setenv("SOLAROPT_DEMO_RECORD", "1")
    client = TestClient(app, headers={"X-SolarOpt-Request": "1"})
    assert client.post("/api/advisor/propose", json=advisor_body()).json()["mode"] == "rules"
    # A rule-based answer is not an AI result, so there is nothing to replay later.
    assert not list(recordings.glob("advisor-*.json"))


def test_label_names_date_model_and_live_duration():
    text = demo.label({"recorded_at": "2026-11-03T05:00:00+00:00", "model": "m", "live_elapsed_ms": 64_400})
    assert "m" in text and "64 giây" in text and "/11/2026" in text
    json.dumps(text)
