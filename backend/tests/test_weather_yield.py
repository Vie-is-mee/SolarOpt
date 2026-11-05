"""Typical-year weather, itemised losses and the hourly output profile (no network: real HCMC TMY fixture)."""
import json
from pathlib import Path

import pytest

from app.schemas import DesignRequest, PanelSpec, ProjectConfig, RectObstacle, VerifyRequest, WeatherYear, YieldLosses
from app.services.energy import model_note, WEATHER_NOTE
from app.services.optimizer import generate_design
from app.services.verifier import verify_design
from app.services.weather import month_hour_grid, temperature_loss_pct
from tests.test_studio import client  # noqa: F401  (fixture reuse)

DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
WEATHER = WeatherYear(**json.loads((Path(__file__).parent / "fixtures" / "weather_hcmc.json").read_text(encoding="utf-8")))
OBSTACLES = [RectObstacle(id="tank", x=7, y=5.6, width_m=1.6, depth_m=1.4, height_m=1.2)]


def config(**extra):
    return ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=1e12, geometry_confirmed=True, **extra)


def with_weather(**extra):
    return config(weather=WEATHER, annual_irradiance_kwh_m2=WEATHER.annual_ghi_kwh_m2, irradiance_reference_tilt_deg=0,
                  yield_losses=YieldLosses(temperature_pct=8.0), **extra)


def test_tmy_hours_land_on_local_month_hours_and_keep_their_energy():
    # 17:00 UTC on 31 Dec is 00:00 local on 1 Jan; 05:00 UTC on 1 Jan is local noon.
    rows = [{"time(UTC)": f"2017{m:02d}{d:02d}:{h:02d}00", "G(h)": 600.0 if (h + 7) % 24 == 12 else 0.0, "Gd(h)": 100.0 if (h + 7) % 24 == 12 else 0.0,
             "T2m": 30.0, "WS10m": 2.0} for m in range(1, 13) for d in (1, 2) for h in range(24)]
    grid = month_hour_grid(rows)
    assert grid["beam_h"][0 * 24 + 12] == pytest.approx(500) and grid["dhi"][0 * 24 + 12] == pytest.approx(100)
    assert sum(grid["beam_h"]) == pytest.approx(12 * 500)


def test_weather_fixture_is_physical():
    assert 1700 < WEATHER.annual_ghi_kwh_m2 < 2000
    month_ghi = [sum(WEATHER.ghi[m * 24:(m + 1) * 24]) for m in range(12)]
    assert month_ghi.index(max(month_ghi)) in (1, 2, 3)          # dry season, Feb–Apr
    assert month_ghi.index(min(month_ghi)) in (8, 9, 10)         # wet season ends in Nov


def test_losses_set_the_performance_ratio_and_roofs_run_hotter_than_racks():
    losses = YieldLosses()
    expected = 1.0
    for v in (8, 4, 2.5, 2, 1.5, 1.5, 2.5, 1, 2):
        expected *= 1 - v / 100
    assert losses.performance_ratio() == round(expected, 4)
    assert config(yield_losses=losses, performance_ratio=.9).performance_ratio == round(expected, 4)
    flush = temperature_loss_pct(WEATHER, 10, 180, "flush", -0.32)
    rack = temperature_loss_pct(WEATHER, 10, 180, "tilted_rack", -0.32)
    assert 5 < rack < flush < 12


def test_weather_from_another_place_is_refused():
    with pytest.raises(ValueError):
        config(weather=WEATHER, latitude=21.03, longitude=105.85)


def test_typical_year_yield_is_realistic_seasonal_and_verifiable():
    cfg = with_weather()
    design = generate_design(DesignRequest(config=cfg, panel=PanelSpec(), obstacles=OBSTACLES, objective="max_energy"))
    m = design.metrics
    # PVGIS PVcalc 1 385 and Global Solar Atlas 1 446 kWh/kWp for this site; flush panels with conservative losses.
    assert 1300 < m.annual_energy_kwh / m.peak_power_kwp < 1500
    months = design.monthly_energy_kwh
    assert months.index(max(months)) in (2, 3) and months.index(min(months)) == 10
    assert sum(design.month_hour_kwh[i] * DAYS[i // 24] for i in range(288)) == pytest.approx(m.annual_energy_kwh, rel=1e-4)
    assert all(v == 0 for i, v in enumerate(design.month_hour_kwh) if i % 24 in (0, 1, 2, 3, 22, 23))
    assert WEATHER_NOTE in design.warnings and model_note(cfg) == WEATHER_NOTE
    check = verify_design(VerifyRequest(config=cfg, panel=PanelSpec(), obstacles=OBSTACLES, design=design))
    assert {c.id: c.status for c in check.checks}["result_consistency"] == "PASS"


def test_clear_sky_projects_still_get_an_hourly_profile():
    design = generate_design(DesignRequest(config=config(), panel=PanelSpec(), obstacles=OBSTACLES, objective="max_energy"))
    assert len(design.month_hour_kwh) == 288
    assert sum(design.month_hour_kwh[i] * DAYS[i // 24] for i in range(288)) == pytest.approx(design.metrics.annual_energy_kwh, rel=1e-4)


def test_weather_endpoint_returns_weather_and_losses(monkeypatch, client):  # noqa: F811
    from app.services import weather
    monkeypatch.setattr(weather, "build_weather", lambda lat, lon, data: WEATHER)
    monkeypatch.setattr(weather, "_download", lambda lat, lon: {})
    r = client.post("/api/solar/weather", json={"latitude": 10.7769, "longitude": 106.7009, "tilt_deg": 10, "azimuth_deg": 180})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["weather"]["annual_ghi_kwh_m2"] == WEATHER.annual_ghi_kwh_m2
    assert body["performance_ratio"] == YieldLosses(**body["losses"]).performance_ratio()
