from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float
    y: float


class RectObstacle(BaseModel):
    id: str
    label: str = "Vật cản"
    x: float = Field(description="Tọa độ x theo mét, gốc trái dưới của mái")
    y: float = Field(description="Tọa độ y theo mét, gốc trái dưới của mái")
    width_m: float = 1.0
    depth_m: float = 1.0
    height_m: float = 1.0
    confidence: float = 1.0
    source: Literal["manual", "gemini", "demo"] = "manual"


class PanelSpec(BaseModel):
    manufacturer: str = "LONGi"
    model: str = "Hi-MO 6 580W"
    width_m: float = 1.134
    height_m: float = 2.278
    power_w: float = 580.0
    price_vnd: float = 4_200_000
    voc_v: float = 52.1
    vmp_v: float = 43.6
    imp_a: float = 13.3


class ProjectConfig(BaseModel):
    project_name: str = "SolarOpt Demo"
    latitude: float = 10.7769
    longitude: float = 106.7009
    roof_width_m: float = 10.0
    roof_height_m: float = 8.0
    roof_azimuth_deg: float = 180.0
    roof_tilt_deg: float = 10.0
    setback_m: float = 0.35
    panel_gap_m: float = 0.08
    obstacle_clearance_m: float = 0.25
    annual_irradiance_kwh_m2: float = 1581.0
    performance_ratio: float = 0.82
    budget_vnd: float = 100_000_000


class SunRequest(BaseModel):
    latitude: float = 10.7769
    longitude: float = 106.7009
    date: date
    hour_local: float = Field(ge=0, le=23.99)
    timezone: str = "Asia/Ho_Chi_Minh"


class SunPosition(BaseModel):
    altitude_deg: float
    azimuth_deg: float
    zenith_deg: float


class CandidatePanel(BaseModel):
    id: str
    x: float
    y: float
    width_m: float
    height_m: float
    annual_energy_kwh: float
    shading_loss_pct: float
    preserved: bool = False


class DesignRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = []
    sun: SunPosition | None = None
    objective: Literal["max_energy", "balanced", "durability"] = "balanced"
    previous_panels: list[CandidatePanel] = []
    minimal_repair_weight: float = 0.0


class DesignMetrics(BaseModel):
    panel_count: int
    peak_power_kwp: float
    annual_energy_kwh: float
    annual_energy_mwh: float
    estimated_cost_vnd: float
    average_shading_loss_pct: float
    roof_utilization_pct: float
    preserved_panel_count: int = 0
    layout_preservation_rate_pct: float = 0.0


class DesignResult(BaseModel):
    panels: list[CandidatePanel]
    metrics: DesignMetrics
    warnings: list[str] = []
    solver_status: str = "UNKNOWN"


class VerifyRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = []
    design: DesignResult
    sun: SunPosition | None = None


class CheckResult(BaseModel):
    id: str
    label: str
    status: Literal["PASS", "FAIL", "WARN"]
    detail: str


class VerifyResult(BaseModel):
    valid: bool
    checks: list[CheckResult]


class StressRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = []
    design: DesignResult
    sun: SunPosition | None = None


class StressScenarioResult(BaseModel):
    id: str
    name: str
    status: Literal["PASS", "FAIL"]
    panel_count: int
    annual_energy_kwh: float
    detail: str


class StressResult(BaseModel):
    passed: int
    total: int
    scenarios: list[StressScenarioResult]


class RepairRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles_before: list[RectObstacle]
    obstacles_after: list[RectObstacle]
    previous_design: DesignResult
    sun: SunPosition | None = None
    objective: Literal["max_energy", "balanced", "durability"] = "balanced"
    minimal_repair_weight: float = 250.0


class DependencyImpact(BaseModel):
    changed_input: str
    affected_nodes: list[str]
    reused_nodes: list[str]
    recomputation_ratio_pct: float


class RepairResult(BaseModel):
    impact: DependencyImpact
    design: DesignResult
    verification: VerifyResult


class VisionObstacle(BaseModel):
    id: str
    label: str
    x_pct: float = Field(ge=0, le=100)
    y_pct: float = Field(ge=0, le=100)
    width_pct: float = Field(ge=0, le=100)
    depth_pct: float = Field(ge=0, le=100)
    height_m: float = 1.0
    confidence: float = Field(ge=0, le=1)


class VisionResult(BaseModel):
    mode: Literal["gemini", "demo"]
    roof_width_m: float
    roof_height_m: float
    roof_confidence: float
    obstacles: list[VisionObstacle]
    extracted_text: list[str] = []
    notes: list[str] = []


class IrradianceResult(BaseModel):
    source: Literal["PVGIS", "fallback"]
    annual_irradiance_kwh_m2: float
    specific_yield_kwh_kwp: float
    detail: str

class UncertaintyRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle]
    obstacle_id: str
    low_height_m: float
    high_height_m: float
    objective: Literal["max_energy", "balanced", "durability"] = "balanced"


class UncertaintyResult(BaseModel):
    obstacle_id: str
    low_design: DesignResult
    high_design: DesignResult
    layout_difference_pct: float
    energy_difference_pct: float
    validity_changed: bool
    impact_score: float
    action: Literal["AUTO_CONTINUE", "ASK_ENGINEER"]
    explanation: str
