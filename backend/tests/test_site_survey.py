"""Site survey screening (structure, wind, corrosion, fire, legal, data) and its effect on layout and electrical design."""
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box

from app.main import app
from app.schemas import CandidatePanel, DesignMetrics, DesignRequest, DesignResult, PanelSpec, ProjectConfig, RectObstacle, VerifyRequest
from app.services.electrical import ElectricalRequest, ac_cable, design_electrical, phase_split, CATALOG
from app.services.geometry import fire_breaks, fire_keepout, is_roof_exit, obstacle_polygon, panel_shape
from app.services.optimizer import generate_design
from app.services.site import SiteReviewRequest, SiteSurvey, corrosion, k_height, mounting_plan, review_site
from app.services.verifier import verify_design

PANEL = PanelSpec()
STAIR = RectObstacle(id="stair", label="Tum thang", x=1, y=6, width_m=2.5, depth_m=2, height_m=2.7)
TANK = RectObstacle(id="tank", label="Bồn nước", x=7, y=5.6, width_m=1.6, depth_m=1.4, height_m=1.2)


def _design(cfg, obstacles=(STAIR, TANK), objective="max_energy"):
    return generate_design(DesignRequest(config=cfg, panel=PANEL, obstacles=list(obstacles), objective=objective))


def _grid(n_x, n_y, gap=.1):
    panels = [CandidatePanel(id=f"P{i}-{j}", x=.5 + i * (1.134 + gap), y=.5 + j * (2.278 + gap), width_m=1.134, height_m=2.278,
                             annual_energy_kwh=800, shading_loss_pct=0) for i in range(n_x) for j in range(n_y)]
    n = len(panels)
    return DesignResult(panels=panels, metrics=DesignMetrics(panel_count=n, peak_power_kwp=n * .58, annual_energy_kwh=n * 800,
                                                             annual_energy_mwh=n * .8, estimated_cost_vnd=n * 2.2e6, average_shading_loss_pct=0,
                                                             roof_utilization_pct=50))


# ---- fire layout -------------------------------------------------------------------------------

def test_roof_exits_are_found_by_kind_label_or_flag():
    assert is_roof_exit(STAIR) and not is_roof_exit(TANK)
    assert is_roof_exit(TANK.model_copy(update={"roof_exit": True}))
    assert not is_roof_exit(STAIR.model_copy(update={"roof_exit": False}))
    assert is_roof_exit(RectObstacle(id="h", label="Hộp kỹ thuật", kind="stair", x=0, y=0))
    assert not is_roof_exit(STAIR.model_copy(update={"scope": "neighbor"}))


def test_fire_code_keeps_panels_three_metres_from_the_stair_and_still_verifies():
    off = _design(ProjectConfig(roof_width_m=20, roof_height_m=14, budget_vnd=1e9))
    cfg = ProjectConfig(roof_width_m=20, roof_height_m=14, budget_vnd=1e9, fire_code=True)
    on = _design(cfg)
    stair = obstacle_polygon(STAIR)
    assert any(panel_shape(p.x, p.y, p.width_m, p.height_m).distance(stair) < 3 for p in off.panels)
    assert on.panels and all(panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg).distance(stair) >= 3 - 1e-6 for p in on.panels)
    assert len(on.panels) < len(off.panels)
    check = verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[STAIR, TANK], design=on))
    assert check.valid
    # A panel dragged back next to the stair is outside the usable area under the fire rules.
    moved = on.model_copy(update={"panels": [on.panels[0].model_copy(update={"x": 3.6, "y": 6.2})] + on.panels[1:]})
    assert not verify_design(VerifyRequest(config=cfg, panel=PANEL, obstacles=[STAIR, TANK], design=moved)).valid


def test_fire_breaks_split_long_roofs_into_groups_of_forty_metres():
    strips = fire_breaks(box(0, 0, 90, 30))
    assert len(strips) == 2                     # 90 m → three groups of 29 m with two 1,5 m breaks
    xs = sorted(s.bounds[0] for s in strips)
    assert xs[0] == pytest.approx(29) and xs[1] == pytest.approx(59.5)
    assert all(s.bounds[2] - s.bounds[0] == pytest.approx(1.5) for s in strips)
    assert fire_breaks(box(0, 0, 40, 40)) == []
    keep = fire_keepout(ProjectConfig(roof_width_m=12, roof_height_m=9, parapet=True), [])
    assert keep.area == pytest.approx(12 * 9 - 7 * 4)   # 2,5 m ring inside the parapet


# ---- wind and corrosion ------------------------------------------------------------------------

def test_height_factor_follows_the_table():
    assert k_height(10, "B") == pytest.approx(1.0)
    assert k_height(6, "B") == pytest.approx(.904)
    assert k_height(1, "A") == pytest.approx(1.0)


def test_mounting_without_survey_is_the_legacy_assumption():
    plan = mounting_plan(ProjectConfig(), PANEL, None)
    assert not plan.surveyed and plan.foot_spacing_center_m == plan.foot_spacing_edge_m == 1.2 and plan.price_factor == 1


def test_wind_zone_sets_attachment_spacing_and_edge_setback():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, roof_elevation_m=6)
    hcmc = mounting_plan(cfg, PANEL, SiteSurvey(roof_material="metal", purlin="steel"))
    assert hcmc.wind_zone == "II" and hcmc.zone_assumed
    assert hcmc.foot_spacing_center_m == 1.2 and hcmc.foot_spacing_edge_m < 1.2
    assert hcmc.edge_zone_m == pytest.approx(.9) and hcmc.recommended_setback_m == cfg.setback_m
    storm = mounting_plan(cfg, PANEL, SiteSurvey(roof_material="metal", purlin="steel", wind_zone="V", terrain="A"))
    assert storm.q_edge_kpa > hcmc.q_edge_kpa * 2
    assert storm.foot_spacing_edge_m < hcmc.foot_spacing_edge_m and storm.recommended_setback_m == pytest.approx(.9)
    far = mounting_plan(cfg.model_copy(update={"latitude": 21.03, "longitude": 105.85}), PANEL, SiteSurvey())
    assert far.zone_assumed and far.wind_zone == "II"


@pytest.mark.parametrize("km,industrial,expected", [(.2, False, "C5"), (2, False, "C4"), (5, False, "C3"), (50, False, "C2"), (50, True, "C3"), (None, False, "C3")])
def test_corrosion_category_by_distance_to_sea(km, industrial, expected):
    assert corrosion(SiteSurvey(coast_km=km, industrial_air=industrial))[0] == expected


# ---- electrical ---------------------------------------------------------------------------------

def test_survey_changes_the_bill_of_materials_consistently():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=120_000_000)
    design = _design(cfg)
    base = design_electrical(ElectricalRequest(config=cfg, panel=PANEL, design=design))
    names = {b.name for b in base.bom}
    assert "Ngắt khẩn cấp phía DC" not in names and "Đồng hồ chống phát ngược" not in names
    coastal = design_electrical(ElectricalRequest(config=cfg, panel=PANEL, design=design, zero_export=True,
                                                  survey=SiteSurvey(roof_material="metal", purlin="steel", coast_km=.2)))
    bom = {b.name: b for b in coastal.bom}
    assert {"Ngắt khẩn cấp phía DC", "Ngắt khẩn cấp tại tủ đóng cắt", "Đồng hồ chống phát ngược"} <= set(bom)
    old = {b.name: b for b in base.bom}
    assert bom["Ray nhôm"].unit_price_vnd == round(old["Ray nhôm"].unit_price_vnd * 1.3)
    assert bom["Chân đỡ / móc mái"].quantity > old["Chân đỡ / móc mái"].quantity
    assert coastal.cost_by_group["mounting"] > base.cost_by_group["mounting"]
    assert sum(coastal.cost_by_group.values()) == pytest.approx(sum(b.amount_vnd for b in coastal.bom))


def test_dispatch_link_from_one_hundred_kilowatts():
    cfg = ProjectConfig(roof_width_m=60, roof_height_m=40)
    design = _design_grid = _grid(25, 8)
    r = design_electrical(ElectricalRequest(config=cfg, panel=PANEL, design=design))
    assert design.metrics.peak_power_kwp >= 100
    assert any(b.name.startswith("Giám sát, kết nối điều độ") for b in r.bom)


def test_long_dc_runs_upsize_the_cable_and_long_ac_runs_too():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=120_000_000)
    design = _design(cfg)
    near = design_electrical(ElectricalRequest(config=cfg, panel=PANEL, design=design))
    far = design_electrical(ElectricalRequest(config=cfg, panel=PANEL, design=design, home_run_m=150, ac_run_m=120))
    spec = lambda r, name: next(b.spec for b in r.bom if b.name == name)
    assert spec(near, "Cáp DC solar").startswith("4 mm²") and not spec(far, "Cáp DC solar").startswith("4 mm²")
    assert {c.id: c.status for c in near.checks}["dc_drop"] == "PASS"
    inv = next(i for i in CATALOG if i.id == "huawei-6ktl-l1")
    size, _, drop = ac_cable(inv, "single", 20)
    assert size == 10 and drop <= 1.5            # 26 A over 20 m: 2,5 % on 4 mm², 1,7 % on 6 mm²


def test_noon_grid_voltage_flags_inverter_trips():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=120_000_000)
    design = _design(cfg)
    status = lambda v: {c.id: c.status for c in design_electrical(ElectricalRequest(config=cfg, panel=PANEL, design=design, grid_voltage_v=v)).checks}["grid_voltage"]
    assert status(230) == "PASS" and status(242) == "WARN" and status(252.5) == "FAIL"


def test_single_phase_inverters_are_spread_over_the_phases():
    inv = next(i for i in CATALOG if i.id == "huawei-6ktl-l1")
    assert phase_split(inv, 2) == [6, 6, 0] and phase_split(inv, 3) == [6, 6, 6]


# ---- review --------------------------------------------------------------------------------------

def _items(review):
    return {f"{s.id}.{i.id}": i for s in review.sections for i in s.items}


def test_review_flags_structure_fire_and_data():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=120_000_000)
    design = _design(cfg)
    survey = SiteSurvey(roof_material="metal", purlin="wood", roof_age_years=18, roof_defects=True,
                        image_source="satellite", image_date="2023-05")
    r = review_site(SiteReviewRequest(config=cfg, panel=PANEL, obstacles=[STAIR, TANK], design=design, survey=survey, today="2026-11", panel_mass_kg=27.5))
    items = _items(r)
    assert r.dead_load_kg_m2 == pytest.approx(27.5 / (1.134 * 2.278) + 2.5, abs=.05)
    assert items["structure.defects"].status == "FAIL" and items["structure.age"].status == "FAIL" and items["structure.purlin"].status == "WARN"
    assert items["fire.exits"].status == "WARN"                  # recommendation only: building not on the approval list
    assert items["data.age"].status == "WARN" and "42 tháng" in items["data.age"].detail
    assert items["data.resolution"].status == "WARN" and items["data.visit"].status == "WARN"
    listed = review_site(SiteReviewRequest(config=cfg, panel=PANEL, obstacles=[STAIR, TANK], design=design,
                                           survey=survey.model_copy(update={"pccc_listed": True})))
    assert _items(listed)["fire.exits"].status == "FAIL" and "fire.approval" in _items(listed)
    assert r.counts["FAIL"] >= 2


@pytest.mark.parametrize("kind,kwp,sell,path,extra", [
    ("residential", 12, True, "Mẫu số 01", "legal.sale"),
    ("residential", 12, False, "Mẫu số 01", "legal.zero_export"),
    ("business", 200, True, "Mẫu số 03", "legal.dispatch"),
    ("business", 60, False, "Mẫu số 02", "legal.zero_export"),
    ("industrial", 1500, False, "1.000 kW", "legal.dispatch"),
])
def test_legal_path_follows_decree_58(kind, kwp, sell, path, extra):
    design = _grid(1, 1).model_copy(update={"metrics": _grid(1, 1).metrics.model_copy(update={"peak_power_kwp": kwp})})
    r = review_site(SiteReviewRequest(config=ProjectConfig(), panel=PANEL, design=design, customer_type=kind, sell_surplus=sell))
    assert path in r.legal_path and extra in _items(r)


def test_public_property_may_not_sell():
    r = review_site(SiteReviewRequest(config=ProjectConfig(), panel=PANEL, survey=SiteSurvey(public_property=True), sell_surplus=True))
    assert _items(r)["legal.public"].status == "FAIL"


def test_review_endpoint_and_bad_month():
    client = TestClient(app)
    res = client.post("/api/site/review", json={"config": ProjectConfig().model_dump(), "panel": PANEL.model_dump(), "survey": {"wind_zone": "III"}})
    assert res.status_code == 200 and res.json()["mounting"]["wind_zone"] == "III"
    assert client.post("/api/site/review", json={"config": ProjectConfig().model_dump(), "panel": PANEL.model_dump(), "survey": {"image_date": "2026-13"}}).status_code == 422
