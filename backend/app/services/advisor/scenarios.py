"""Deterministic tools the advisor calls: consumption, site facts, and scenario evaluation.

A scenario runs SolarOpt's own optimizer on a copy of the project with a given objective, energy target,
investment cap and edge reserve, then prices it with an all-in cost per kWp and a cash flow that
values self-used energy at the customer's own tariff.
"""
from __future__ import annotations

import math

from app.schemas import DesignRequest
from app.services.advisor.models import AdvisorRequest, ApplyPlan, Consumption, Scenario, ScenarioParams
from app.services.advisor.tariff import TARIFF_SOURCE, marginal_price, monthly_saving, residential_kwh
from app.services.geometry import build_context
from app.services.optimizer import area_upper_bound, generate_design
from app.services.selfuse import nearest_profile, scale_profile, self_consumption

EXPORT_CAP = 0.5   # surplus paid on at most half the output (NĐ 58/2025 as amended by NĐ 243/2026)

# All-in installed price (equipment, labour, installer margin and VAT) by size, the same table as the
# handover economics (frontend economics.ts marketCapex): press quotes of 2026 put households at about
# 12–15 and businesses at about 7.5–13 million VND per kWp. Not a quote; the engineer replaces it.
MARKET_CAPEX_SOURCE = ("Suất đầu tư trọn gói tham khảo theo quy mô (thị trường Việt Nam 11/2026, gồm thiết bị, thi công, lãi nhà thầu và VAT): "
                       "hộ gia đình đến 5 kWp 13,5; đến 15 kWp 12; lớn hơn 11 triệu đ/kWp; kinh doanh đến 50 kWp 10; đến 200 kWp 8,5; lớn hơn 7,5. "
                       "Thay bằng báo giá thật trước khi chốt.")


def market_capex(tariff: str, kwp: float) -> float:
    if tariff == "business":
        return 10.0 if kwp <= 50 else 8.5 if kwp <= 200 else 7.5
    return 13.5 if kwp <= 5 else 12.0 if kwp <= 15 else 11.0
DEFAULT_DAYTIME = {"residential": 35.0, "business": 60.0}


def vn(v: float, digits: int = 1) -> str:
    """Vietnamese number: 15.502 / 2,32 (dot thousands, comma decimals, no trailing zeros)."""
    text = f"{v:,.{digits}f}".translate(str.maketrans({",": ".", ".": ","}))
    return text.rstrip("0").rstrip(",") if "," in text else text


def consumption(req: AdvisorRequest) -> Consumption:
    c = req.customer
    share = c.daytime_share_pct if c.daytime_share_pct is not None else DEFAULT_DAYTIME[c.tariff]
    monthly, source = None, "Chưa có hóa đơn hay số kWh: chưa biết nhu cầu, phương án chỉ dựa vào mái và ngân sách."
    if c.monthly_kwh:
        monthly, source = c.monthly_kwh, "Số kWh mỗi tháng do kỹ sư nhập từ hóa đơn."
    elif c.monthly_bill_vnd and c.tariff == "residential":
        monthly = residential_kwh(c.monthly_bill_vnd, c.vat_pct)
        source = f"Quy đổi từ tiền điện {vn(c.monthly_bill_vnd, 0)} đ/tháng theo {TARIFF_SOURCE}; cộng VAT {vn(c.vat_pct)}%."
    elif c.monthly_bill_vnd and c.business_price_vnd_kwh:
        monthly = c.monthly_bill_vnd / (c.business_price_vnd_kwh * (1 + c.vat_pct / 100))
        source = f"Quy đổi từ tiền điện {vn(c.monthly_bill_vnd, 0)} đ/tháng với giá kinh doanh bình quân {vn(c.business_price_vnd_kwh, 0)} đ/kWh, VAT {vn(c.vat_pct)}%."
    monthly = round(monthly, 1) if monthly else None
    annual = round(monthly * 12) if monthly else None
    return Consumption(annual_kwh=annual, monthly_kwh=monthly, daytime_share_pct=share, daytime_kwh_year=annual * share / 100 if annual else None, source=source)


def capex(req: AdvisorRequest) -> tuple[float | None, str]:
    """All-in price per kWp the engineer typed (None: the market table by size), and where it came from."""
    if req.customer.capex_million_per_kwp:
        return req.customer.capex_million_per_kwp, "Suất đầu tư trọn gói do kỹ sư nhập theo báo giá."
    return None, MARKET_CAPEX_SOURCE


def site_facts(req: AdvisorRequest) -> dict[str, float | str | None]:
    ctx = build_context(req.config, req.obstacles, None)
    usable, bound = area_upper_bound(req.config, req.panel, ctx)
    roof_obstacles = [o for o in req.obstacles if o.scope == "roof"]
    return {
        "site.roof_area_m2": round(ctx.roof.area, 1),
        "site.usable_area_m2": usable,
        "site.max_panels_by_area": bound,
        "site.max_kwp_by_area": round(bound * req.panel.power_w / 1000, 2),
        "site.obstacles": len(roof_obstacles),
        "site.neighbour_structures": len(req.obstacles) - len(roof_obstacles),
        "site.tallest_obstacle_m": max((o.height_m for o in req.obstacles), default=0),
        "site.latitude": req.config.latitude,
        "panel.power_w": req.panel.power_w,
        "panel.price_vnd": req.panel.price_vnd,
        "panel.model": f"{req.panel.manufacturer} {req.panel.model}",
    }


def cash_flow(req: AdvisorRequest, cons: Consumption, kwp: float, energy: float, investment: float,
              profile: list[float] | None = None, extra_daytime: float = 0.0):
    """Self-used energy saves the customer's own tariff; surplus earns sell_price (0 by default) on at most half
    the output. With the layout's hourly output and a known bill, self-use is matched hour by hour against the
    customer's load profile (services/selfuse.py, the same model as the handover economics); otherwise it is
    capped by daytime demand, and without a known demand all output counts as self-used."""
    f, c = req.finance, req.customer
    monthly = cons.monthly_kwh
    base = consumption(req)                       # the bill alone; extra daytime load is added hour by hour
    hourly = None
    if profile and len(profile) == 288 and base.monthly_kwh and energy > 0:
        kind = "business" if c.tariff == "business" else "residential"
        hourly = self_consumption(scale_profile(profile, energy), kind, nearest_profile(kind, base.daytime_share_pct), base.monthly_kwh,
                                  req.config.latitude, vat_pct=c.vat_pct, extra_daytime_kwh_year=extra_daytime)
        if kind == "business" and c.business_price_vnd_kwh:
            hourly["avoided_vnd"] = hourly["self_kwh"] * c.business_price_vnd_kwh * (1 + c.vat_pct / 100)
    cumulative, npv, payback = -investment, -investment, None
    first_saving, self_use_pct = 0.0, 100.0
    for year in range(1, f.years + 1):
        fade = (1 - f.degradation_pct / 100) ** (year - 1)
        e = energy * fade
        growth = (1 + f.price_growth_pct / 100) ** (year - 1)
        if hourly:
            self_used = min(e, hourly["self_kwh"] * fade)
            saving = hourly["avoided_vnd"] * fade * growth
        else:
            self_used = min(e, cons.daytime_kwh_year) if cons.daytime_kwh_year is not None else e
            if monthly:
                saving = 12 * monthly_saving(monthly, self_used / 12, c.tariff, c.business_price_vnd_kwh, c.vat_pct) * growth
            else:   # No bill: value self use at the 3rd residential tier, a conservative middle price.
                saving = self_used * marginal_price(250) * (1 + c.vat_pct / 100) * growth
        export = min(e - self_used, e * EXPORT_CAP) * f.sell_price_vnd_kwh * growth
        net = saving + export - f.maintenance_vnd_per_kwp_year * kwp
        if year == 1:
            first_saving, self_use_pct = saving + export, (self_used / e * 100 if e else 0)
        previous = cumulative
        cumulative += net
        if payback is None and cumulative >= 0 and net > 0:
            payback = year - 1 + max(0.0, -previous) / net
        npv += net / (1 + f.discount_pct / 100) ** year
    return first_saving, self_use_pct, payback, npv


class ScenarioBook:
    """Runs and remembers scenarios for one advisor request; ids are S1, S2, ..."""
    MAX = 4

    def __init__(self, req: AdvisorRequest):
        self.req = req
        self.cons = consumption(req)
        self.fixed_capex, self.capex_source = capex(req)
        self.items: list[Scenario] = []
        self.applied: dict[str, ApplyPlan] = {}   # project settings that reproduce each scenario
        # Without an investment cap the roof is the limit; this bound can never bind the optimizer.
        self.area_bound = max(1, area_upper_bound(req.config, req.panel, build_context(req.config, req.obstacles, None))[1])

    def per_kwp(self, kwp: float) -> float:
        return self.fixed_capex or market_capex(self.req.customer.tariff, kwp)

    @property
    def capex(self) -> float:
        """Price per kWp quoted to the model and the page: the typed price, or the market price at the roof's full size."""
        return self.per_kwp(self.area_bound * self.req.panel.power_w / 1000)

    def investment(self, kwp: float) -> float:
        return self.per_kwp(kwp) * 1e6 * kwp if kwp > 0 else 0.0

    def demand(self, extra_daytime: float) -> Consumption:
        """Consumption with extra daytime load (e.g. an EV charged at home); it shifts the bill into higher tiers too."""
        if not extra_daytime:
            return self.cons
        base = self.cons
        annual = (base.annual_kwh or 0) + extra_daytime
        daytime = (base.daytime_kwh_year or 0) + extra_daytime
        return Consumption(annual_kwh=round(annual), monthly_kwh=round(annual / 12, 1), daytime_share_pct=round(daytime / annual * 100, 1),
                           daytime_kwh_year=round(daytime), source=base.source + f" Cộng {vn(extra_daytime, 0)} kWh/năm dùng ban ngày theo góp ý.")

    def run(self, params: ScenarioParams, label: str, intent: str = "") -> Scenario:
        if len(self.items) >= self.MAX:
            raise ValueError(f"Đã thử tối đa {self.MAX} kịch bản cho một lần đề xuất.")
        req, panel = self.req, self.req.panel
        cap = params.max_investment_vnd or req.customer.budget_vnd
        cons = self.demand(params.extra_daytime_kwh_year)
        panel_kwp = panel.power_w / 1000
        # The optimizer caps panels by panel price; translate an all-in cap into that panel count
        # (the price per kWp steps down with size, so count down from the roof's limit).
        max_panels = next((n for n in range(self.area_bound, -1, -1) if self.investment(n * panel_kwp) <= cap + 1e-6), 0) if cap else self.area_bound
        target = params.target_energy_kwh_year if params.objective == "min_cost" else None
        if params.objective == "min_cost" and target is None:
            target = cons.annual_kwh or None
            if target is None:
                raise ValueError("Phương án giảm chi phí cần điện năng mục tiêu; chưa có hóa đơn hay số kWh.")
        config = req.config.model_copy(update={
            "budget_vnd": max(1, max_panels) * panel.price_vnd if max_panels else 0,
            "target_energy_kwh_year": target,
            "layout_edge_reserve_m": max(req.config.layout_edge_reserve_m, params.edge_reserve_m),
            "geometry_confirmed": True,
        })
        result = generate_design(DesignRequest(config=config, panel=panel, obstacles=req.obstacles, objective=params.objective))
        m = result.metrics
        kwp, energy = m.peak_power_kwp, m.annual_energy_kwh
        investment = self.investment(kwp) if m.panel_count else 0.0
        saving, self_use, payback, npv = cash_flow(req, cons, kwp, energy, investment, result.month_hour_kwh, params.extra_daytime_kwh_year)
        notes = [w for w in result.warnings if w.startswith(("Chưa đáp ứng", "Dự phòng", "Đã đạt giới hạn")) or "trên nóc vật cản" in w]
        item = Scenario(
            id=f"S{len(self.items) + 1}", label=label[:80] or params.objective, intent=intent[:400], params=params,
            panel_count=m.panel_count, peak_power_kwp=round(kwp, 2), annual_energy_kwh=round(energy),
            coverage_pct=round(energy / cons.annual_kwh * 100, 1) if cons.annual_kwh else None,
            self_use_pct=round(self_use, 1), average_shading_loss_pct=round(m.average_shading_loss_pct, 2),
            investment_vnd=round(investment, -3), annual_saving_vnd=round(saving, -3),
            payback_years=round(payback, 1) if payback is not None else None, npv_vnd=round(npv, -3),
            target_met=result.target_met, warnings=notes[:4],
        )
        self.items.append(item)
        self.applied[item.id] = ApplyPlan(objective=params.objective, budget_vnd=config.budget_vnd, target_energy_kwh_year=target, layout_edge_reserve_m=config.layout_edge_reserve_m)
        return item

    def drop_if_duplicate(self) -> bool:
        """Forget the last scenario when it landed on the same layout as an earlier one (e.g. two plans capped by one budget)."""
        last = self.items[-1]
        if any(s.panel_count == last.panel_count and abs(s.annual_energy_kwh - last.annual_energy_kwh) <= .005 * max(1.0, s.annual_energy_kwh) for s in self.items[:-1]):
            self.items.pop()
            self.applied.pop(last.id, None)
            return True
        return False

    def get(self, sid: str) -> Scenario | None:
        return next((s for s in self.items if s.id == sid), None)

    def facts(self) -> dict[str, float | str | None]:
        out: dict[str, float | str | None] = {
            "consumption.annual_kwh": round(self.cons.annual_kwh) if self.cons.annual_kwh else None,
            "consumption.monthly_kwh": round(self.cons.monthly_kwh) if self.cons.monthly_kwh else None,
            "consumption.daytime_share_pct": self.cons.daytime_share_pct,
            "consumption.daytime_kwh_year": round(self.cons.daytime_kwh_year) if self.cons.daytime_kwh_year else None,
            "customer.budget_vnd": self.req.customer.budget_vnd,
            "capex.million_per_kwp": self.capex,
        }
        for s in self.items:
            for key in ("panel_count", "peak_power_kwp", "annual_energy_kwh", "coverage_pct", "self_use_pct", "average_shading_loss_pct",
                        "investment_vnd", "annual_saving_vnd", "payback_years", "npv_vnd"):
                out[f"{s.id}.{key}"] = getattr(s, key)
        return out
