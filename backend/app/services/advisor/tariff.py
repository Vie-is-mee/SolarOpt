"""EVN retail tariff: monthly bill <-> kWh, so consumption comes from a formula, never from the LLM.

Residential stepped tariff (Quyết định 1279/QĐ-BCT, effective 10/05/2025), VND/kWh before VAT.
VAT is a parameter: bills show 8 % or 10 % depending on the reduction in force; check the customer's bill.
Businesses pay one price per time band; the engineer enters the average price from the bill.
"""
from __future__ import annotations

import math

TARIFF_SOURCE = "Biểu giá điện sinh hoạt bậc thang EVN theo Quyết định 1279/QĐ-BCT (hiệu lực 10/05/2025), chưa gồm VAT"
# (kWh in this tier, price); the last tier is open-ended.
RESIDENTIAL_TIERS: tuple[tuple[float, float], ...] = ((50, 1984), (50, 2050), (100, 2380), (100, 2998), (100, 3350), (math.inf, 3460))


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
        return self_used * (business_price or 0) * (1 + vat_pct / 100)
    return residential_bill(monthly_kwh, vat_pct) - residential_bill(monthly_kwh - self_used, vat_pct)
