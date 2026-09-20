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
