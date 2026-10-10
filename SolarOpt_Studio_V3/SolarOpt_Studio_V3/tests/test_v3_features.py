from app.engine.orchestrator import (
    new_demo_state,
    run_autopilot,
    configure_project,
)


def test_three_design_options_and_robust_option_is_verified():
    s = new_demo_state()
    out = run_autopilot(s)
    assert len(out["design_options"]) == 3
    robust = next(x for x in out["design_options"] if x["id"] == "OPT-3")
    assert robust["stress_passed"] == robust["stress_total"]


def test_configuration_moves_hardware_to_project_input():
    s = new_demo_state()
    out = configure_project(
        s,
        panel_id="TRINA_600",
        latitude=10.8,
        longitude=106.7,
        roof_tilt_deg=18,
        roof_azimuth_deg=185,
        edge_setback_m=0.5,
        objective="robust",
        budget_vnd=150_000_000,
        inverter_name="Sungrow SG12RT",
    )
    assert out["project"]["panel"]["id"] == "TRINA_600"
    assert out["project"]["objective"] == "robust"
    assert out["project"]["budget_vnd"] == 150_000_000
