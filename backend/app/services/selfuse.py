"""Hour-by-hour self-consumption, the server twin of frontend/src/loadProfiles.ts.

The layout's typical-day output (12 months × 24 hours, energy.month_hour_energy) is matched hour by hour
against a load profile built from the customer's monthly consumption, on three kinds of day (cloudy,
average, sunny) so the overlap is not overstated. The avoided bill follows the stepped residential tariff
or the time bands of business and production supply (tariff.py). Both sides must stay identical: the
golden figures in tests/test_selfuse.py and frontend/scripts/selfuse.test.mjs are the same numbers.
"""
from __future__ import annotations

from app.services.advisor.tariff import TOU, residential_bill

DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_HOME = (3.5, 3.2, 3, 3, 3, 3.2, 4, 4.5, 4.2, 4, 4.2, 4.6, 4.8, 4.6, 4.4, 4.2, 4.2, 4.6, 5.5, 6.2, 6.4, 6, 5, 4.2)
_AWAY = (4.5, 4.2, 4, 4, 4, 4.2, 5.2, 4.6, 2.2, 1.8, 1.8, 1.9, 2, 1.9, 1.8, 1.8, 2, 3.5, 6, 7.2, 7.4, 7, 6, 5)
_SHOP = (1, 1, 1, 1, 1, 1, 1.5, 3, 7, 8.5, 9, 9.2, 8.6, 8.8, 9, 9, 8.5, 7, 3, 1.5, 1.2, 1, 1, 1)
_SHIFT1 = (1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 3, 8, 8.5, 8.5, 8.5, 6, 7.5, 8.5, 8.5, 8.5, 6, 2.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5)
_SHIFT2 = (2, 2, 2, 2, 2, 2, 7, 8, 8, 8, 8, 7, 8, 8, 8, 8, 8, 7.5, 7.5, 7.5, 7.5, 7, 4, 2)
_FLAT = tuple(1.1 if 6 <= h < 18 else 1 for h in range(24))
_STANDBY = (1,) * 24
# id: (workday, saturday, sunday) as (shape, daily weight), and whether household seasons apply.
PROFILES = {
    "away_day": (((_AWAY, .95), (_HOME, 1.12), (_HOME, 1.12)), True),
    "home_day": (((_HOME, 1), (_HOME, 1), (_HOME, 1)), True),
    "shop": (((_SHOP, 1), (_SHOP, .9), (_STANDBY, .25)), False),
    "factory_1": (((_SHIFT1, 1), (_SHIFT1, 1), (_STANDBY, .2)), False),
    "factory_2": (((_SHIFT2, 1), (_SHIFT2, 1), (_STANDBY, .25)), False),
    "continuous": (((_FLAT, 1), (_FLAT, 1), (_FLAT, 1)), False),
}
SOUTH = (.92, .95, 1.08, 1.15, 1.12, 1.02, .98, .97, .95, .96, .94, .96)
NORTH = (.85, .8, .82, .9, 1.1, 1.25, 1.3, 1.25, 1.1, .95, .85, .83)
DAY_KINDS = ((.5, .2), (1, .4), (1.25, .4))
DAY_TYPES = ((0, 5 / 7, False), (1, 1 / 7, False), (2, 1 / 7, True))   # Mon–Fri, Saturday, Sunday


def band_shares(h: int, sunday: bool):
    """(normal, off-peak, peak) share of the hour starting at h; peak 17:30–22:30 Monday–Saturday."""
    if h < 6:
        return 0.0, 1.0, 0.0
    if sunday:
        return 1.0, 0.0, 0.0
    if h in (17, 22):
        return .5, 0.0, .5
    if 18 <= h <= 21:
        return 0.0, 0.0, 1.0
    return 1.0, 0.0, 0.0


def hour_price(prices, h, sunday):
    n, o, p = band_shares(h, sunday)
    return n * prices[0] + o * prices[1] + p * prices[2]


def daytime_share(profile: str, start: int = 7, end: int = 17) -> float:
    """Share of a week's consumption between start and end o'clock, used to match a customer's stated share."""
    days, _ = PROFILES[profile]
    total = day = 0.0
    for t, share, _sunday in DAY_TYPES:
        shape, weight = days[t]
        s = sum(shape)
        total += share * weight
        day += share * weight * sum(shape[start:end]) / s
    return day / total * 100


def nearest_profile(kind: str, daytime_pct: float | None) -> str:
    if kind != "residential":
        return "shop"
    if daytime_pct is None:
        return "away_day"
    return min(("away_day", "home_day"), key=lambda p: abs(daytime_share(p) - daytime_pct))


def scale_profile(profile, annual):
    total = sum(v * DAYS[i // 24] for i, v in enumerate(profile))
    return [v * annual / total for v in profile] if total > 0 else list(profile)


def self_consumption(production, kind: str, profile: str, monthly_kwh: float, latitude: float, voltage: str = "low",
                     vat_pct: float = 8.0, extra_daytime_kwh_year: float = 0.0):
    """Year-one self-use and avoided bill (VAT included). production: kWh per typical day, 288 values.
    extra_daytime_kwh_year adds a load spread evenly from 9:00 to 17:00 every day (EV charging, a heat pump)."""
    days, seasonal = PROFILES[profile]
    season = (NORTH if abs(latitude) >= 18 else SOUTH) if seasonal else (1,) * 12
    mean = sum(DAYS) / 12
    norm = sum(share * days[t][1] for t, share, _ in DAY_TYPES)
    extra = [extra_daytime_kwh_year / 365 / 8 if 9 <= h < 17 else 0.0 for h in range(24)]
    prices = None if kind == "residential" else TOU[kind][voltage]
    self_kwh = prod_kwh = load_kwh = avoided = 0.0
    for m in range(12):
        prod = production[m * 24:m * 24 + 24]
        m_self = m_load = m_tou = 0.0
        for t, share, sunday in DAY_TYPES:
            shape, weight = days[t]
            daily = monthly_kwh * season[m] / mean * weight / norm
            s = sum(shape)
            for h in range(24):
                load = daily * shape[h] / s + extra[h]
                used = sum(pk * min(k * prod[h], load) for k, pk in DAY_KINDS)
                m_self += DAYS[m] * share * used
                m_load += DAYS[m] * share * load
                if prices:
                    m_tou += DAYS[m] * share * used * hour_price(prices, h, sunday)
        avoided += m_tou * (1 + vat_pct / 100) if prices else residential_bill(m_load, vat_pct) - residential_bill(m_load - m_self, vat_pct)
        self_kwh += m_self
        prod_kwh += sum(prod) * DAYS[m]
        load_kwh += m_load
    return {"production_kwh": prod_kwh, "load_kwh": load_kwh, "self_kwh": self_kwh, "export_kwh": max(0.0, prod_kwh - self_kwh),
            "self_pct": self_kwh / prod_kwh * 100 if prod_kwh > 0 else 0.0, "coverage_pct": self_kwh / load_kwh * 100 if load_kwh > 0 else 0.0,
            "avoided_vnd": avoided, "buy_price": avoided / self_kwh if self_kwh > 0 else 0.0}
