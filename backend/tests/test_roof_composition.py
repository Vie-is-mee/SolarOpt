"""Roofs built in parts (a smaller roof stacked on the main one, again on top of that) and vaults with a chosen strip count."""
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.main import app
from app.schemas import DesignRequest, PanelSpec, ProjectConfig, VerifyRequest
from app.services.geometry import surface_z, surfaces
from app.services.optimizer import generate_design
from app.services.roof_templates import generate_faces, height_below, stack_faces
from app.services.verifier import verify_design

client = TestClient(app)
BASE = ProjectConfig(roof_width_m=14, roof_height_m=10, roof_elevation_m=6, budget_vnd=1e9)


def _template(config, **body):
    res = client.post("/api/roof/template", json={"config": config.model_dump(), **body})
    assert res.status_code == 200, res.text
    return res.json()


def _with(config, faces):
    return ProjectConfig(**{**config.model_dump(), "roof_faces": faces})


def test_vault_strip_count_is_the_engineers_choice():
    for n in (3, 6, 12):
        faces, notes = generate_faces(BASE, "barrel", "x", 2.5, strips=n)
        assert len(faces) == n and all(f.group == "vault" for f in faces)
        assert "kỹ sư chọn" in notes[0]
    auto, notes = generate_faces(BASE, "barrel", "x", 2.5, panel_pitch_m=1.21)
    assert "tự động" in notes[0]
    assert client.post("/api/roof/template", json={"config": BASE.model_dump(), "shape": "barrel", "strips": 1}).status_code == 422
    # Fewer strips follow the curve less closely: the reported deviation grows.
    dev = lambda n: float(generate_faces(BASE, "parabolic", "x", 2.5, strips=n)[1][0].split("cong ")[1].split(" cm")[0].replace(",", "."))
    assert dev(3) > dev(10)


def test_stacked_gables_three_levels():
    main = _with(BASE, _template(BASE, shape="gable", ridge_axis="x", rise_m=2)["roof_faces"])
    # A cross gable over the middle of the main ridge: it starts at the ridge height (6 + 2 m).
    region = (5, 3, 4, 4)
    assert height_below(main, (5, 3, 9, 7)) == pytest.approx(8)
    second = _template(main, shape="gable", ridge_axis="y", rise_m=1.5, region=list(region))
    cfg2 = _with(main, second["roof_faces"])
    ids = [f["id"] for f in second["roof_faces"]]
    assert any(i.startswith("sub1-") for i in ids) and "Mái phụ 1" in second["notes"][0]
    # A third, smaller gable on top of the second one.
    third = _template(cfg2, shape="gable", ridge_axis="x", rise_m=.8, region=[6, 4, 2, 2])
    cfg3 = _with(cfg2, third["roof_faces"])
    assert any(f["id"].startswith("sub2-") for f in third["roof_faces"]) and any(f["id"].startswith("sub1-") for f in third["roof_faces"])
    # Faces tile the roof without overlap and keep their planes outside the stacked parts.
    polys = [Polygon([(p.x, p.y) for p in f.polygon]) for f in cfg3.roof_faces]
    assert unary_union(polys).area == pytest.approx(14 * 10, rel=1e-3)
    assert sum(p.area for p in polys) == pytest.approx(14 * 10, rel=1e-3)
    planes = {s.id: s for s in surfaces(main)}
    for s in surfaces(cfg3):
        if not s.id.startswith("sub"):
            original = planes[s.id.split("-p")[0]]
            c = s.polygon.representative_point()
            assert surface_z(s, c.x, c.y, cfg3) == pytest.approx(surface_z(original, c.x, c.y, main), abs=1e-3)
    top = max(surface_z(s, s.origin_x, s.origin_y, cfg3) for s in surfaces(cfg3))
    assert top > 8 + 1.0
    # The engine designs and verifies on the composite roof.
    design = generate_design(DesignRequest(config=cfg3, panel=PanelSpec(), objective="max_energy"))
    assert design.panels and verify_design(VerifyRequest(config=cfg3, panel=PanelSpec(), design=design)).valid


def test_stacking_on_a_plain_roof_and_limits():
    faces = stack_faces(BASE, generate_faces(BASE, "hip", "x", 1.2, region=(2, 2, 6, 6), eave_m=6, prefix="sub1-")[0], (2, 2, 6, 6))
    cfg = _with(BASE, [f.model_dump() for f in faces])
    assert any(f.id == "main" and f.label == "Mái chính" for f in cfg.roof_faces)
    assert client.post("/api/roof/template", json={"config": BASE.model_dump(), "shape": "gable", "region": [40, 40, 3, 3]}).status_code == 422
    vault = _with(BASE, _template(BASE, shape="barrel", rise_m=2.5, strips=20)["roof_faces"])
    res = client.post("/api/roof/template", json={"config": vault.model_dump(), "shape": "barrel", "strips": 10, "region": [1, 1, 5, 5]})
    assert res.status_code == 422 and "24 mặt" in res.json()["detail"]
