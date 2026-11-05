"""Panels the engineer drags by hand are re-measured like a fresh verification."""
from app.schemas import DesignRequest, PanelSpec, ProjectConfig, RectObstacle, VerifyRequest
from app.services.manual_layout import evaluate_layout
from app.services.optimizer import generate_design
from app.services.verifier import verify_design

CFG = ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=1e12, geometry_confirmed=True)
PANEL = PanelSpec()
TANK = RectObstacle(id="tank", x=7, y=5.6, width_m=1.6, depth_m=1.4, height_m=1.2)


def base():
    design = generate_design(DesignRequest(config=CFG, panel=PANEL, obstacles=[TANK], objective="max_energy"))
    return design


def test_untouched_layout_matches_the_verifier_exactly():
    design = base()
    out = evaluate_layout(VerifyRequest(config=CFG, panel=PANEL, obstacles=[TANK], design=design))
    assert out["design"].metrics.annual_energy_kwh == design.metrics.annual_energy_kwh
    assert out["verification"].valid
    assert {c.id: c.status for c in out["verification"].checks} == {c.id: c.status for c in verify_design(VerifyRequest(config=CFG, panel=PANEL, obstacles=[TANK], design=design)).checks}


def test_panel_dragged_onto_the_tank_is_named_and_numbers_follow():
    design = base()
    moved = design.panels[0].model_copy(update={"x": 7.2, "y": 5.7})
    edited = design.model_copy(update={"panels": [moved, *design.panels[1:]]})
    out = evaluate_layout(VerifyRequest(config=CFG, panel=PANEL, obstacles=[TANK], design=edited))
    checks = {c.id: c for c in out["verification"].checks}
    assert not out["verification"].valid
    assert moved.id in checks["obstacle_clearance"].affected_panel_ids
    assert checks["result_consistency"].status == "PASS"
    assert any("chỉnh tay" in w for w in out["design"].warnings)


def test_removing_a_panel_updates_count_power_and_cost():
    design = base()
    edited = design.model_copy(update={"panels": design.panels[1:]})
    out = evaluate_layout(VerifyRequest(config=CFG, panel=PANEL, obstacles=[TANK], design=edited))
    m = out["design"].metrics
    assert m.panel_count == design.metrics.panel_count - 1
    assert m.estimated_cost_vnd == design.metrics.estimated_cost_vnd - PANEL.price_vnd
    assert out["verification"].valid
