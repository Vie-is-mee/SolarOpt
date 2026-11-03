"""Request and proposal shapes for the design advisor.

Every number in a proposal is produced by SolarOpt's own tools (tariff, optimizer, cash flow). The LLM
chooses which scenarios to try and writes the reasoning; each reason cites fact keys that the server
checks against the computed facts, so a claim without a computed source is dropped, not shown.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import PanelSpec, ProjectConfig, RectObstacle

Need = Literal["max_energy", "min_cost", "robust"]
NEED_LABEL = {"max_energy": "Sản lượng cao nhất", "min_cost": "Đáp ứng nhu cầu, giảm chi phí", "robust": "Dự phòng sai số"}


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    monthly_kwh: float | None = Field(default=None, gt=0, le=10_000_000, description="From the bill; preferred over monthly_bill_vnd")
    monthly_bill_vnd: float | None = Field(default=None, gt=0, le=1e11)
    tariff: Literal["residential", "business"] = "residential"
    business_price_vnd_kwh: float | None = Field(default=None, gt=0, le=20_000, description="Average price before VAT, business tariff only")
    vat_pct: float = Field(default=8, ge=0, le=20)
    daytime_share_pct: float | None = Field(default=None, ge=0, le=100, description="Share of consumption between 7h and 17h")
    budget_vnd: float | None = Field(default=None, gt=0, le=1e12, description="Total the customer can invest, all-in")
    capex_million_per_kwp: float | None = Field(default=None, gt=0, le=200, description="All-in installed price; SolarOpt planning reference when empty")
    notes: str = Field(default="", max_length=2000)


class Finance(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    years: int = Field(default=25, ge=5, le=40)
    degradation_pct: float = Field(default=0.5, ge=0, le=5)
    price_growth_pct: float = Field(default=0, ge=0, le=15)
    discount_pct: float = Field(default=6, ge=0, le=30)
    maintenance_vnd_per_kwp_year: float = Field(default=100_000, ge=0, le=5_000_000)
    sell_price_vnd_kwh: float = Field(default=0, ge=0, le=20_000, description="Paid surplus; 0 unless there is a basis for payment")


class AdvisorRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = Field(default_factory=list, max_length=100)
    need: Need
    customer: Customer = Field(default_factory=Customer)
    finance: Finance = Field(default_factory=Finance)
    feedback: list[str] = Field(default_factory=list, max_length=12, description="Engineer's change requests, oldest first")
    previous: "Proposal | None" = None
    use_llm: bool = True


class Consumption(BaseModel):
    annual_kwh: float | None
    monthly_kwh: float | None
    daytime_share_pct: float
    daytime_kwh_year: float | None
    source: str


class ScenarioParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: Literal["max_energy", "min_cost", "robust"]
    target_energy_kwh_year: float | None = Field(default=None, gt=0, le=10_000_000)
    max_investment_vnd: float | None = Field(default=None, gt=0, le=1e12)
    edge_reserve_m: float = Field(default=0, ge=0, le=1)
    extra_daytime_kwh_year: float = Field(default=0, ge=0, le=1_000_000, description="Daytime demand added by the engineer's notes (EV charging, heat pump...)")


class Scenario(BaseModel):
    id: str
    label: str
    intent: str = ""
    params: ScenarioParams
    panel_count: int
    peak_power_kwp: float
    annual_energy_kwh: float
    coverage_pct: float | None
    self_use_pct: float
    average_shading_loss_pct: float
    investment_vnd: float
    annual_saving_vnd: float
    payback_years: float | None
    npv_vnd: float
    target_met: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class Reason(BaseModel):
    text: str
    refs: list[str] = Field(default_factory=list)


class ApplyPlan(BaseModel):
    """What 'Áp dụng' changes in the project before running the design."""
    objective: Literal["max_energy", "min_cost", "robust"]
    budget_vnd: float
    target_energy_kwh_year: float | None
    layout_edge_reserve_m: float


class Proposal(BaseModel):
    mode: Literal["llm", "rules"]
    model: str = ""
    need: Need
    consumption: Consumption
    capex_million_per_kwp: float
    capex_source: str
    scenarios: list[Scenario]
    recommended_id: str
    recommended_budget_vnd: float
    summary: str
    reasons: list[Reason]
    risks: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    facts: dict[str, float | str | None] = Field(default_factory=dict)
    apply: ApplyPlan
    plans: dict[str, ApplyPlan] = Field(default_factory=dict, description="Settings that reproduce each scenario, so any one can be applied")
    trace: list[dict] = Field(default_factory=list)
    notice: str = ""
    elapsed_ms: float = 0


AdvisorRequest.model_rebuild()
