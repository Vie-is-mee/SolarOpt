from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CandidatePanel, DesignMetrics, DesignResult, PanelSpec, ProjectConfig, RoofFace
from app.services.electrical import CATALOG, ElectricalRequest, InverterSpec, design_electrical

PANEL = PanelSpec()


def layout(rows, cols, face="base", x0=0.0, y0=0.0, shading=0.0):
    return [CandidatePanel(id=f"{face}-{r}-{c}", x=x0 + c * 1.2, y=y0 + r * 2.4, width_m=1.134, height_m=2.278,
                           annual_energy_kwh=800, shading_loss_pct=shading if (r, c) == (0, 0) else 0, face_id=face)
            for r in range(rows) for c in range(cols)]


def design(panels):
    n = len(panels)
    return DesignResult(panels=panels, metrics=DesignMetrics(panel_count=n, peak_power_kwp=n * 0.58, annual_energy_kwh=n * 800,
                                                             annual_energy_mwh=n * 0.8, estimated_cost_vnd=0, average_shading_loss_pct=0,
                                                             roof_utilization_pct=50))


def run(panels, config=None, **kw):
    return design_electrical(ElectricalRequest(config=config or ProjectConfig(roof_width_m=20, roof_height_m=15), panel=PANEL,
                                               design=design(panels), **kw))


def test_every_panel_is_wired_once_within_the_voltage_window():
    panels = layout(3, 7)
    r = run(panels)
    assert r.valid, [c.detail for c in r.checks if c.status == "FAIL"]
    wired = [pid for s in r.strings for pid in s.panel_ids]
    assert sorted(wired) == sorted(p.id for p in panels)
    assert all(r.string_min <= s.length <= r.string_max for s in r.strings)
    assert all(s.voc_cold_v <= r.inverter.max_dc_voltage_v for s in r.strings)
    assert all(s.vmp_hot_v >= r.inverter.mppt_min_v for s in r.strings)
    # Equal or neighbouring lengths only: the split is as even as the string count allows.
    assert max(s.length for s in r.strings) - min(s.length for s in r.strings) <= 1


def test_cold_mornings_in_the_north_shorten_the_longest_string():
    huawei = "huawei-5ktl-l1"
    south = run(layout(2, 5), ProjectConfig(latitude=10.8), inverter_id=huawei)
    north = run(layout(2, 5), ProjectConfig(latitude=21.0), inverter_id=huawei)
    # 600 V / (52.1 V × (1 + 0.27 % × 23 °C)) = 10.8 at 2 °C; 600 / (52.1 × 1.027) = 11.2 at 15 °C.
    assert north.string_max == 10 and south.string_max == 11
    assert all(s.voc_cold_v <= 600 for s in north.strings)


def test_strings_and_trackers_never_mix_roof_orientations():
    config = ProjectConfig(roof_width_m=20, roof_height_m=15, roof_faces=[
        RoofFace(id="east", polygon=[{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 15}, {"x": 0, "y": 15}], tilt_deg=20, azimuth_deg=90),
        RoofFace(id="west", polygon=[{"x": 10, "y": 0}, {"x": 20, "y": 0}, {"x": 20, "y": 15}, {"x": 10, "y": 15}], tilt_deg=20, azimuth_deg=270),
    ])
    r = run(layout(2, 4, "east") + layout(2, 4, "west", x0=10), config)
    assert r.valid
    for s in r.strings:
        assert len({pid.split("-")[0] for pid in s.panel_ids}) == 1
    by_id = {s.id: s for s in r.strings}
    for m in r.mppts:
        assert len({by_id[i].orientation for i in m.strings}) == 1
    assert next(c for c in r.checks if c.id == "orientation").status == "PASS"


def test_a_face_too_small_for_its_own_string_is_joined_and_flagged():
    config = ProjectConfig(roof_faces=[
        RoofFace(id="main", polygon=[{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 6}, {"x": 0, "y": 6}], tilt_deg=15, azimuth_deg=180),
        RoofFace(id="dormer", polygon=[{"x": 0, "y": 6}, {"x": 10, "y": 6}, {"x": 10, "y": 8}, {"x": 0, "y": 8}], tilt_deg=15, azimuth_deg=90),
    ])
    r = run(layout(2, 6, "main") + layout(1, 1, "dormer", y0=6), config, inverter_id="huawei-5ktl-l1")
    assert not r.unassigned_panel_ids
    assert next(c for c in r.checks if c.id == "orientation").status == "WARN"


def test_too_few_trackers_is_a_failure_not_a_silent_drop():
    tiny = InverterSpec(id="tiny", manufacturer="Test", model="1 MPPT", ac_rated_w=3000, max_dc_power_w=4000, max_dc_voltage_v=600,
                        mppt_min_v=90, mppt_max_v=560, start_voltage_v=100, mppt_count=1, strings_per_mppt=1,
                        max_current_per_mppt_a=14, max_short_circuit_per_mppt_a=18, price_vnd=10_000_000)
    # 24 panels need at least 3 strings of 8-11; with one tracker per inverter the count must grow or panels stay unwired.
    r = run(layout(4, 6), custom_inverter=tiny)
    assert r.inverter_count >= 3 or not r.valid
    if not r.valid:
        assert r.unassigned_panel_ids and any(c.id == "unassigned" and c.status == "FAIL" for c in r.checks)


def test_shading_spread_inside_a_string_is_flagged():
    r = run(layout(2, 5, shading=40), inverter_id="huawei-5ktl-l1")
    assert next(c for c in r.checks if c.id == "shading").status == "WARN"


def test_bill_of_materials_prices_the_chosen_equipment():
    r = run(layout(3, 7))
    items = {b.name: b for b in r.bom}
    assert items["Tấm pin"].quantity == 21
    assert items["Inverter hòa lưới"].quantity == r.inverter_count
    assert items["Inverter hòa lưới"].amount_vnd == r.inverter.price_vnd * r.inverter_count
    assert items["CB DC 2 cực"].quantity == len(r.strings)
    assert sum(r.cost_by_group.values()) == sum(b.amount_vnd for b in r.bom)
    assert {"inverter", "dc", "ac", "mounting", "earthing"} <= set(r.cost_by_group)


def test_auto_pick_prefers_single_phase_for_a_small_house_and_reports_alternatives():
    r = run(layout(2, 4))
    assert r.phase == "single" and 0.85 <= r.dc_ac_ratio <= 1.35
    assert len(r.options) >= 3 and r.options[0].inverter_id == r.inverter.id


def test_api_lists_catalogue_and_designs():
    client = TestClient(app, headers={"X-SolarOpt-Request": "1"})
    assert len(client.get("/api/electrical/inverters").json()) == len(CATALOG)
    body = {"config": ProjectConfig().model_dump(), "panel": PANEL.model_dump(), "design": design(layout(2, 5)).model_dump()}
    res = client.post("/api/design/electrical", json=body)
    assert res.status_code == 200, res.text
    assert res.json()["strings"]
    empty = client.post("/api/design/electrical", json={**body, "design": design([]).model_dump()})
    assert empty.status_code == 422 and "Chưa có tấm pin" in empty.text
