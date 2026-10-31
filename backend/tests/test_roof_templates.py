import json
import math

import pytest

from app.schemas import DesignRequest, PanelSpec, ProjectConfig, VerifyRequest
from app.services import vision
from app.services.geometry import build_context, surface_z, surfaces
from app.services.optimizer import generate_design
from app.services.roof_templates import SHAPES, generate_faces
from app.services.verifier import verify_design
from tests.test_studio import client, image_bytes  # noqa: F401  (fixture reuse)

PANEL = PanelSpec(price_vnd=4_000_000)
PITCH = PANEL.width_m + .08


def with_faces(shape, axis="x", rise=2.5, **base):
    cfg = ProjectConfig(roof_width_m=16, roof_height_m=10, budget_vnd=1e12, **base)
    faces, notes = generate_faces(cfg, shape, axis, rise, panel_pitch_m=PITCH)
    return ProjectConfig(**{**cfg.model_dump(), "roof_faces": [f.model_dump() for f in faces]}), faces, notes


@pytest.mark.parametrize("shape", SHAPES)
def test_every_shape_yields_a_verified_layout(shape):
    cfg, faces, _ = with_faces(shape, rise=1.5)
    design = generate_design(DesignRequest(config=cfg, panel=PANEL, obstacles=[], objective="max_energy"))
    assert design.metrics.panel_count > 0
    assert verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[], design=design)).valid


def test_gable_faces_meet_at_the_ridge_and_face_opposite_ways():
    cfg, faces, _ = with_faces("gable", "x", rise=2.5, roof_elevation_m=6)
    planes = {s.id: s for s in surfaces(cfg)}
    a, b = planes["gable-0"], planes["gable-1"]
    assert (a.azimuth - b.azimuth) % 360 == pytest.approx(180)
    assert a.tilt == pytest.approx(math.degrees(math.atan2(2.5, 5)), abs=1e-3)
    for s in (a, b):   # eave at 6 m, ridge (y = 5) at 8.5 m
        assert surface_z(s, 8, 5, cfg) == pytest.approx(8.5, abs=1e-3)
        assert surface_z(s, 8, 0 if s is a else 10, cfg) == pytest.approx(6, abs=1e-3)


def test_vault_strips_follow_the_curve_and_share_one_setback():
    cfg, faces, notes = with_faces("barrel", "x", rise=1.2)
    assert all(f.group == "vault" for f in faces) and len(faces) > 3
    assert "lệch lớn nhất" in notes[0]
    # Seams between strips are not set back: usable area is close to the whole roof minus the outer edge.
    usable = build_context(cfg, [], None).usable_roof.area
    assert usable == pytest.approx((16 - .7) * (10 - .7), rel=.02)


def test_steep_curve_reports_deviation_and_blocks_too_steep_strips():
    _, faces, notes = with_faces("barrel", "x", rise=4.9)
    assert "vượt dung sai" in notes[0]
    assert any(not f.installable for f in faces)


def test_template_endpoint_rejects_unknown_shape(client):  # noqa: F811
    body = {"config": ProjectConfig().model_dump(), "shape": "dome"}
    assert client.post("/api/roof/template", json=body).status_code == 422
    ok = client.post("/api/roof/template", json={**body, "shape": "hip", "rise_m": 2}).json()
    assert len(ok["roof_faces"]) == 4


def test_vision_reports_roof_shape_and_drops_invalid_values(authenticated_client, monkeypatch):
    client=authenticated_client
    monkeypatch.setenv('AI_PROVIDER', 'groq'); monkeypatch.setenv('GROQ_API_KEY', 'test-shape'); vision._cache.clear()
    payload = {'is_roof_or_plan': True, 'roof_confidence': .7, 'obstacles': [], 'roof_shape': 'gable', 'ridge_axis': 'diagonal', 'rise_m': -3}

    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices': [{'message': {'content': json.dumps(payload)}}]}
    monkeypatch.setattr(vision.requests, 'post', lambda *a, **kw: Response())
    body = client.post('/api/vision/analyze', files={'file': ('roof.png', image_bytes(), 'image/png')}).json()
    assert body['roof_shape'] == 'gable' and body['ridge_axis'] == 'unknown' and body['rise_m'] is None


def test_sloped_faces_use_plan_footprint_and_fit_more_panels():
    cfg, _, _ = with_faces("gable", "x", rise=2.5)
    design = generate_design(DesignRequest(config=cfg, panel=PANEL, obstacles=[], objective="max_energy"))
    c = math.cos(math.atan2(2.5, 5))
    sides = {round(v, 4) for p in design.panels for v in (p.width_m, p.height_m)}
    assert sides <= {round(PANEL.width_m, 4), round(PANEL.height_m, 4), round(PANEL.width_m * c, 4), round(PANEL.height_m * c, 4)}
    assert any(abs(v - PANEL.width_m * c) < 1e-4 or abs(v - PANEL.height_m * c) < 1e-4 for v in sides)
    assert design.metrics.panel_count >= 48
    assert verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[], design=design)).valid
    # The same layout drawn with physical sizes on the slope must not pass the consistency check.
    physical = design.model_copy(deep=True)
    for p in physical.panels:
        p.width_m, p.height_m = (PANEL.width_m, PANEL.height_m) if p.width_m <= p.height_m else (PANEL.height_m, PANEL.width_m)
    checks = {c.id: c.status for c in verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[], design=physical)).checks}
    assert checks["result_consistency"] == "FAIL"
