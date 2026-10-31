from datetime import date

from app.schemas import DesignRequest, PanelSpec, ProjectConfig, RectObstacle, SunPosition, VerifyRequest
from app.services.optimizer import generate_design
from app.services.verifier import verify_design
from app.services.dependency import trace_impact


def test_design_and_verify():
    cfg = ProjectConfig(budget_vnd=100_000_000)
    panel = PanelSpec(price_vnd=4_000_000)
    obs = [RectObstacle(id="tank", label="Bồn nước", x=5.6, y=3.4, width_m=1.2, depth_m=1.1, height_m=1.2)]
    sun = SunPosition(altitude_deg=60, azimuth_deg=180, zenith_deg=30)
    result = generate_design(DesignRequest(config=cfg, panel=panel, obstacles=obs, sun=sun))
    assert result.metrics.panel_count > 0
    ver = verify_design(VerifyRequest(config=cfg, panel=panel, obstacles=obs, design=result, sun=sun))
    assert ver.valid


def test_dependency_impact():
    impact = trace_impact("obstacle_height")
    assert "shadow_map" in impact.affected_nodes
    assert "layout" in impact.affected_nodes
    assert "roof_geometry" in impact.reused_nodes


def test_area_upper_bound_never_below_selected_panels():
    cfg = ProjectConfig(budget_vnd=1_000_000_000)
    panel = PanelSpec(price_vnd=4_000_000)
    obs = [RectObstacle(id="tank", label="Bồn nước", x=5.6, y=3.4, width_m=1.2, depth_m=1.1, height_m=1.2)]
    result = generate_design(DesignRequest(config=cfg, panel=panel, obstacles=obs))
    m = result.metrics
    assert m.usable_area_m2 is not None and 0 < m.usable_area_m2 < cfg.roof_width_m * cfg.roof_height_m
    assert m.area_upper_bound_panels >= m.panel_count > 0


def test_installable_obstacle_top_adds_panels_without_breaking_checks():
    from app.services.geometry import build_context
    cfg = ProjectConfig(budget_vnd=1_000_000_000, roof_elevation_m=6)
    panel = PanelSpec(price_vnd=4_000_000)
    stair = dict(id="stair", label="Tum thang", x=1, y=1, width_m=4.6, depth_m=3, height_m=2.7)
    plain = generate_design(DesignRequest(config=cfg, panel=panel, obstacles=[RectObstacle(**stair)]))
    obs = [RectObstacle(**stair, top_installable=True)]
    ctx = build_context(cfg, obs, None)
    top = next(s for s in ctx.surfaces if s.id == "top-stair")
    assert top.elevation == 6 + 2.7 and top.installable
    result = generate_design(DesignRequest(config=cfg, panel=panel, obstacles=obs))
    on_top = [p for p in result.panels if p.face_id == "top-stair"]
    assert len(on_top) >= 3 and result.metrics.panel_count >= plain.metrics.panel_count + 3
    assert any("nóc vật cản" in w for w in result.warnings)
    assert verify_design(VerifyRequest(config=cfg, panel=panel, obstacles=obs, design=result)).valid


def test_obstacle_top_flag_ignored_for_neighbours():
    from app.services.geometry import build_context
    cfg = ProjectConfig()
    house = RectObstacle(id="nb", label="Nhà bên", x=13, y=0, width_m=5, depth_m=5, height_m=8, scope="neighbor", top_installable=True)
    assert not any(s.id.startswith("top-") for s in build_context(cfg, [house], None).surfaces)
