"""Server twin of the frontend self-consumption model: the golden figures below are asserted on both sides
(frontend/scripts/selfuse.test.mjs), so the advisor and the handover economics cannot drift apart."""
import math

import pytest

from app.services.selfuse import daytime_share, nearest_profile, self_consumption

SEASON = [1, 1.15, 1.25, 1.25, 1.05, 1.05, .95, .9, .9, .95, .8, .9]
PROFILE = [SEASON[i // 24] * 7.6 * math.sin(math.pi * ((i % 24 + .5) - 6) / 12) if 6 < (i % 24 + .5) < 18 else 0 for i in range(288)]
GOLDEN = {
    ("residential", "home_day", 500): (21496.9881, 6001.4795, 2978.0801, 10037298.9646),
    ("business", "shop", 3000): (21496.9881, 36000.0, 18811.6141, 63134813.5348),
}


@pytest.mark.parametrize("key", GOLDEN)
def test_golden_figures_match_the_frontend(key):
    kind, profile, monthly = key
    r = self_consumption(PROFILE, kind, profile, monthly, 10.78)
    production, load, used, avoided = GOLDEN[key]
    assert r["production_kwh"] == pytest.approx(production, abs=1e-3)
    assert r["load_kwh"] == pytest.approx(load, abs=1e-3)
    assert r["self_kwh"] == pytest.approx(used, abs=1e-3)
    assert r["avoided_vnd"] == pytest.approx(avoided, abs=1)


def test_profiles_match_a_stated_daytime_share():
    assert daytime_share("away_day") < 35 < daytime_share("home_day") < 45
    assert nearest_profile("residential", 40) == "home_day"
    assert nearest_profile("residential", 25) == "away_day"
    assert nearest_profile("business", None) == "shop"


def test_daytime_extra_load_raises_self_use():
    base = self_consumption(PROFILE, "residential", "away_day", 400, 10.78)
    ev = self_consumption(PROFILE, "residential", "away_day", 400, 10.78, extra_daytime_kwh_year=1800)
    assert ev["self_kwh"] > base["self_kwh"] and ev["load_kwh"] == pytest.approx(base["load_kwh"] + 1800, rel=1e-6)


def test_daytime_extra_golden_matches_the_frontend():
    r = self_consumption(PROFILE, "residential", "away_day", 400, 10.78, extra_daytime_kwh_year=1800)
    assert r["load_kwh"] == pytest.approx(6601.1836, abs=1e-3)
    assert r["self_kwh"] == pytest.approx(3614.0059, abs=1e-3)
    assert r["avoided_vnd"] == pytest.approx(12388894.18, abs=1)
