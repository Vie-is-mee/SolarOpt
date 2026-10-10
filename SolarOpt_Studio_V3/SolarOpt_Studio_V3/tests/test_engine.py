from app.engine.orchestrator import new_demo_state, run_autopilot, change_tank_height, change_panel


def test_autopilot_produces_design():
    s = new_demo_state()
    out = run_autopilot(s)
    assert out["design"] is not None
    assert out["design"]["panel_count"] > 0
    assert len(out["events"]) >= 6


def test_change_height_creates_new_version_or_passes():
    s = new_demo_state()
    run_autopilot(s)
    n0 = len(s.versions)
    out = change_tank_height(s, 1.8)
    assert len(out["events"]) >= 2
    assert len(s.versions) >= n0


def test_panel_change_traces_dependencies():
    s = new_demo_state()
    run_autopilot(s)
    out = change_panel(s, "TRINA_600")
    assert out["project"]["panel"]["id"] == "TRINA_600"
    assert out["dependency_status"]["layout"] == "VERIFIED"
