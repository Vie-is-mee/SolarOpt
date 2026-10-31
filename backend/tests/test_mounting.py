import math

import pytest

from app.schemas import DesignRequest, PanelSpec, ProjectConfig, SunRequest, VerifyRequest
from app.services.geometry import build_context, footprint_dims, panel_shape, rack_row_pitch
from app.services.mounting import compare_mountings
from app.services.optimizer import generate_design
from app.services.roof_templates import generate_faces
from app.services.solar import sun_position
from app.services.verifier import verify_design
from datetime import date

PANEL = PanelSpec(price_vnd=4_000_000)


def run(**cfg):
    config = ProjectConfig(roof_width_m=16, roof_height_m=10, budget_vnd=1e12, **cfg)
    design = generate_design(DesignRequest(config=config, panel=PANEL, obstacles=[], objective="max_energy"))
    return config, design


def test_rack_pitch_leaves_no_row_shadow_in_the_winter_design_window():
    cfg = ProjectConfig(latitude=21.03, longitude=105.85, mounting="tilted_rack", rack_tilt_deg=20)
    L = PANEL.height_m
    pitch = rack_row_pitch(L, cfg)
    beta = math.radians(20)
    assert pitch > L * math.cos(beta)
    for hour in (9, 10.5, 12, 13.5, 15):
        sun = sun_position(SunRequest(latitude=cfg.latitude, longitude=cfg.longitude, date=date(2026, 12, 21), hour_local=hour))
        shadow = L * math.sin(beta) * max(0, math.cos(math.radians(sun.azimuth_deg - 180))) / math.tan(math.radians(sun.altitude_deg))
        assert L * math.cos(beta) + shadow <= pitch + 1e-9
    assert rack_row_pitch(L, cfg.model_copy(update={"latitude": 10.78})) < pitch        # lower sun further north


def test_rack_layout_uses_tilted_footprint_spacing_and_passes_checks():
    cfg, design = run(mounting="tilted_rack", rack_tilt_deg=15)
    assert design.metrics.panel_count > 0
    rack = next(s for s in build_context(cfg, [], None).surfaces if s.mount == "tilted_rack")
    for p in design.panels:
        assert footprint_dims(PANEL.width_m, PANEL.height_m, p.rotation_deg % 180, rack, cfg) == pytest.approx((p.width_m, p.height_m), abs=1e-5)
    assert verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[], design=design)).valid
    flat = run()[1]
    assert design.metrics.annual_energy_kwh / design.metrics.panel_count > flat.metrics.annual_energy_kwh / flat.metrics.panel_count


def test_tracker_gains_per_panel_but_spacing_costs_panels_on_a_small_roof():
    cfg, design = run(mounting="tracker", tracker_gcr=0.4)
    flat = run()[1]
    per = lambda d: d.metrics.annual_energy_kwh / d.metrics.panel_count
    assert per(design) > per(flat) * 1.12
    assert design.metrics.panel_count < flat.metrics.panel_count
    assert {(round(p.width_m, 3), round(p.height_m, 3)) for p in design.panels} <= {(PANEL.width_m, PANEL.height_m)}
    assert verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[], design=design)).valid


def test_sloped_faces_keep_flush_mounting():
    base = ProjectConfig(roof_width_m=16, roof_height_m=10, budget_vnd=1e12, mounting="tracker")
    faces, _ = generate_faces(base, "gable", "x", 2.5, panel_pitch_m=1.214)
    cfg = ProjectConfig(**{**base.model_dump(), "roof_faces": [f.model_dump() for f in faces]})
    assert all(s.mount is None for s in build_context(cfg, [], None).surfaces if s.tilt > 1)


def test_compare_reports_every_option_against_flush():
    result = compare_mountings(DesignRequest(config=ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=1e12), panel=PANEL, obstacles=[]))
    labels = [o["label"] for o in result["options"]]
    assert labels[0] == "Lắp sát mái" and len(labels) == 7 and result["best"] in labels
    assert result["options"][0]["vs_flush_pct"] == 0
    assert any("chi phí" in n for n in result["notes"])
