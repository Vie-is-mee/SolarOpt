"""EVN retail tariff: monthly bill <-> kWh, so consumption comes from a formula, never from the LLM.

Prices: Quyết định 2892/QĐ-BCT (effective 01/11/2026), VND/kWh before VAT. Residential has five stepped tiers;
business and production pay by time band (Quyết định 963/QĐ-BCT, 22/04/2026): peak 17:30–22:30 Monday to
Saturday, off-peak 0:00–6:00 every day, normal otherwise; Sunday has no peak. The frontend (src/tariff.ts)
mirrors these numbers. VAT is a parameter: bills show 8 % while the VAT reduction is in force (through 2026).
"""
from __future__ import annotations

import math

TARIFF_SOURCE = "Biểu giá điện EVN theo Quyết định 2892/QĐ-BCT (hiệu lực 01/11/2026), chưa gồm VAT"
# (kWh in this tier, price); the last tier is open-ended.
RESIDENTIAL_TIERS: tuple[tuple[float, float], ...] = ((100, 1901), (100, 2289), (200, 2894), (300, 3456), (math.inf, 3844))
# Low voltage (≤ 1 kV) and medium voltage (1–35 kV): (normal, off-peak, peak).
TOU = {
    "business": {"low": (3089, 1880, 5313), "medium": (2829, 1577, 4924)},
    "industrial": {"low": (1966, 1274, 3586), "medium": (1814, 1166, 3348)},
}


def residential_bill(kwh: float, vat_pct: float = 8.0) -> float:
    """Monthly bill (VND, VAT included) for kwh on the stepped residential tariff."""
    left, total = max(0.0, kwh), 0.0
    for size, price in RESIDENTIAL_TIERS:
        used = min(left, size)
        total += used * price
        left -= used
        if left <= 0:
            break
    return total * (1 + vat_pct / 100)


def residential_kwh(bill_vnd: float, vat_pct: float = 8.0) -> float:
    """Inverse of residential_bill: kWh that produce this monthly bill (VAT included)."""
    left, kwh = max(0.0, bill_vnd) / (1 + vat_pct / 100), 0.0
    for size, price in RESIDENTIAL_TIERS:
        cost = size * price
        if left <= cost:
            return kwh + left / price
        left -= cost
        kwh += size
    return kwh


def marginal_price(kwh: float) -> float:
    """Price of the next kWh before VAT: the tier that solar output removes first."""
    used = 0.0
    for size, price in RESIDENTIAL_TIERS:
        used += size
        if kwh < used:
            return price
    return RESIDENTIAL_TIERS[-1][1]


def monthly_saving(monthly_kwh: float, self_used_kwh: float, tariff: str, business_price: float | None, vat_pct: float) -> float:
    """Bill reduction when self_used_kwh of the month comes from the roof instead of the grid.
    On the stepped tariff the top (most expensive) tiers disappear first."""
    self_used = min(max(0.0, self_used_kwh), max(0.0, monthly_kwh))
    if tariff == "business":
        # Solar hours fall in the normal band now that the peak moved to the evening.
        return self_used * (business_price or TOU["business"]["low"][0]) * (1 + vat_pct / 100)
    return residential_bill(monthly_kwh, vat_pct) - residential_bill(monthly_kwh - self_used, vat_pct)
