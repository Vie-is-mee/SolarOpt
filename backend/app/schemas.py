from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.evidence import ProjectEvidence

Objective = Literal["max_energy", "min_cost", "robust", "balanced", "durability"]


class StrictModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class Point(StrictModel):
    x: float
    y: float


class RectObstacle(StrictModel):
    id: str
    label: str = "Vật cản"
    x: float = Field(description="Tọa độ x theo mét, gốc trái dưới của mái")
    y: float = Field(description="Tọa độ y theo mét, gốc trái dưới của mái")
    width_m: float = Field(default=1.0, gt=0, le=200)
    depth_m: float = Field(default=1.0, gt=0, le=200)
    height_m: float = Field(default=1.0, ge=0, le=500)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: Literal["manual", "gemini", "groq", "ollama", "demo"] = "manual"
    scope: Literal["roof", "neighbor"] = "roof"
    confirmed: bool = True
    floors: int | None = Field(default=None, ge=1, le=100)
    shape: Literal["rect", "ellipse", "polygon"] = "rect"
    rotation_deg: float = Field(default=0, ge=-360, le=360)
    points: list[Point] = Field(default_factory=list, max_length=80, description="Local footprint coordinates before rotation")
    base_elevation_m: float | None = Field(default=None, ge=0, le=500)

    @model_validator(mode="after")
    def validate_footprint(self):
        if self.shape == "polygon":
            from shapely.geometry import Polygon
            if len(self.points)<3 or not Polygon([(p.x,p.y) for p in self.points]).is_valid:
                raise ValueError("Vật cản đa giác cần ít nhất 3 điểm, không tự cắt.")
            if Polygon([(p.x,p.y) for p in self.points]).area<0.001:
                raise ValueError("Vật cản không có diện tích.")
        return self


class RoofFace(StrictModel):
    id: str
    label: str = "Phần mái"
    polygon: list[Point] = Field(min_length=3, max_length=80)
    elevation_m: float = Field(default=6, ge=0, le=300)
    tilt_deg: float = Field(default=0, ge=0, le=60)
    azimuth_deg: float = Field(default=180, ge=0, le=360)
    installable: bool = True


class PanelSpec(StrictModel):
    manufacturer: str = "LONGi"
    model: str = "Hi-MO 6 580W"
    width_m: float = Field(default=1.134, gt=0, le=10)
    height_m: float = Field(default=2.278, gt=0, le=10)
    power_w: float = Field(default=580.0, gt=0, le=2000)
    price_vnd: float = Field(default=4_200_000, ge=1)
    voc_v: float = 52.1
    vmp_v: float = 43.6
    imp_a: float = 13.3


class ProjectConfig(StrictModel):
    project_name: str = "SolarOpt Demo"
    latitude: float = Field(default=10.7769, ge=-89, le=89)
    longitude: float = Field(default=106.7009, ge=-180, le=180)
    roof_width_m: float = Field(default=10.0, gt=0, le=100)
    roof_height_m: float = Field(default=8.0, gt=0, le=100)
    roof_azimuth_deg: float = Field(default=180.0, ge=0, le=360)
    roof_tilt_deg: float = Field(default=0.0, ge=0, le=60)
    layout_edge_reserve_m: float = Field(default=0, ge=0, le=5, description="Additional packing reserve; independent of mandatory setback")
    layout_angle_deg: float | None = Field(default=None, ge=-180, le=180, description="In-plane panel angle; None searches roof-edge directions")
    north_rotation_deg: float = Field(default=0.0, ge=0, lt=360, description="Azimuth of the drawing's +Y axis, clockwise from true north")
    roof_elevation_m: float = Field(default=6.0, ge=0, le=300)
    roof_polygon: list[Point] = Field(default_factory=list, max_length=50)
    roof_faces: list[RoofFace] = Field(default_factory=list, max_length=24)
    roof_openings: list[list[Point]] = Field(default_factory=list, max_length=24)
    geometry_confirmed: bool = False
    dimensions_source: Literal["assumed", "reference", "measured"] = "assumed"
    measurement_image_width_px: float | None = Field(default=None, gt=0, le=40000)
    measurement_image_height_px: float | None = Field(default=None, gt=0, le=40000)
    dimensions_verified: bool = False
    calibration_reference_m: float | None = Field(default=None, gt=0, le=100)
    setback_m: float = Field(default=0.35, ge=0, le=10)
    panel_gap_m: float = Field(default=0.08, ge=0.02, le=5)
    obstacle_clearance_m: float = Field(default=0.25, ge=0, le=10)
    annual_irradiance_kwh_m2: float = Field(default=1581.0, gt=0, le=4000)
    irradiance_reference_tilt_deg: float = Field(default=0, ge=0, le=60)
    irradiance_reference_azimuth_deg: float = Field(default=180, ge=0, le=360)
    performance_ratio: float = Field(default=0.82, gt=0, le=1)
    budget_vnd: float = Field(default=100_000_000, ge=0)
    target_energy_kwh_year: float | None = Field(default=None, gt=0, le=10_000_000)

    @model_validator(mode="after")
    def validate_polygon(self):
        from shapely.geometry import Polygon, box
        boundary = box(0,0,self.roof_width_m,self.roof_height_m)
        if self.roof_polygon:
            poly = Polygon([(p.x, p.y) for p in self.roof_polygon]) if len(self.roof_polygon) >= 3 else None
            if poly is None or not poly.is_valid or poly.area < 0.1:
                raise ValueError("Đường viền mái cần ít nhất 3 điểm, không tự cắt và có diện tích dương.")
            if any(p.x < 0 or p.y < 0 or p.x > self.roof_width_m or p.y > self.roof_height_m for p in self.roof_polygon):
                raise ValueError("Điểm biên mái phải nằm trong kích thước khung mái.")
            boundary = poly
        faces=[]
        ids=set()
        for face in self.roof_faces:
            poly=Polygon([(p.x,p.y) for p in face.polygon])
            if not poly.is_valid or poly.area<0.01 or not boundary.buffer(1e-7).covers(poly):
                raise ValueError("Phần mái phải có diện tích, không tự cắt và nằm trong biên mái.")
            if face.id in ids or any(poly.intersection(old).area>1e-5 for old in faces):
                raise ValueError("Các phần mái không được trùng tên định danh hoặc chồng diện tích.")
            faces.append(poly);ids.add(face.id)
        for points in self.roof_openings:
            if len(points)<3 or len(points)>80:
                raise ValueError("Khoảng trống mái cần 3–80 điểm.")
            poly=Polygon([(p.x,p.y) for p in points])
            if not poly.is_valid or poly.area<.01 or not boundary.buffer(1e-7).covers(poly):
                raise ValueError("Khoảng trống phải nằm trong biên mái và không tự cắt.")
        return self


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
    source: str = "pvlib"


class CandidatePanel(StrictModel):
    id: str
    x: float
    y: float
    width_m: float = Field(gt=0, le=10)
    height_m: float = Field(gt=0, le=10)
    rotation_deg: float = Field(default=0, ge=-180, le=180)
    annual_energy_kwh: float = Field(ge=0)
    shading_loss_pct: float = Field(ge=0, le=100)
    preserved: bool = False
    face_id: str = "base"


class DesignRequest(BaseModel):
    evidence: ProjectEvidence | None = None
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = Field(default_factory=list, max_length=100)
    sun: SunPosition | None = None
    objective: Objective = "balanced"
    previous_panels: list[CandidatePanel] = []
    minimal_repair_weight: float = 0.0

    @model_validator(mode="after")
    def require_energy_target(self):
        if self.objective == "min_cost" and self.config.target_energy_kwh_year is None:
            raise ValueError("Nhập điện năng mục tiêu (kWh/năm) để tính phương án giảm chi phí.")
        return self


class DesignMetrics(StrictModel):
    panel_count: int
    peak_power_kwp: float
    annual_energy_kwh: float
    annual_energy_mwh: float
    estimated_cost_vnd: float
    average_shading_loss_pct: float
    maximum_shading_loss_pct: float = 0
    roof_utilization_pct: float
    preserved_panel_count: int = 0
    layout_preservation_rate_pct: float = 0.0


class LayoutTrial(BaseModel):
    search_stage: Literal["coarse", "refined"] = "coarse"
    angle_deg: float
    offset_x_m: float
    offset_y_m: float
    candidate_count: int
    geometry_candidate_count: int = 0
    shading_rejected_count: int = 0
    robustness_rejected_count: int = 0
    target_met: bool | None = None
    panel_count: int
    annual_energy_kwh: float
    objective_score: float
    selected: bool = False


class RobustnessCheck(BaseModel):
    id: str
    name: str
    status: Literal["PASS", "WARN", "FAIL"]
    detail: str


class DesignResult(BaseModel):
    panels: list[CandidatePanel]
    metrics: DesignMetrics
    warnings: list[str] = []
    solver_status: str = "UNKNOWN"
    layout_trials: list[LayoutTrial] = Field(default_factory=list)
    objective: Objective | None = None
    target_energy_kwh_year: float | None = None
    target_met: bool | None = None
    robustness_checks: list[RobustnessCheck] = Field(default_factory=list)


class VerifyRequest(BaseModel):
    evidence: ProjectEvidence | None = None
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
    affected_panel_ids: list[str] = Field(default_factory=list)


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
    status: Literal["PASS", "WARN", "FAIL"]
    panel_count: int
    annual_energy_kwh: float
    detail: str
    failed_checks: list[CheckResult] = Field(default_factory=list)
    warning_checks: list[CheckResult] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    affected_panel_ids: list[str] = Field(default_factory=list)


class StressResult(BaseModel):
    passed: int
    total: int
    warned: int = 0
    failed: int = 0
    scenarios: list[StressScenarioResult]


class RepairRequest(BaseModel):
    evidence: ProjectEvidence | None = None
    config: ProjectConfig
    panel: PanelSpec
    previous_config: ProjectConfig | None = None
    previous_panel: PanelSpec | None = None
    obstacles_before: list[RectObstacle]
    obstacles_after: list[RectObstacle]
    previous_design: DesignResult
    sun: SunPosition | None = None
    objective: Objective = "balanced"
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


class NormalizedPoint(StrictModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class VisionObstacle(StrictModel):
    id: str
    label: str
    x_pct: float = Field(ge=0, le=100)
    y_pct: float = Field(ge=0, le=100)
    width_pct: float = Field(ge=0, le=100)
    depth_pct: float = Field(ge=0, le=100)
    height_m: float | None = Field(default=None, ge=0, le=500)
    confidence: float = Field(ge=0, le=1)
    observation: str = ""
    requires_placement: bool = False


class VisionResult(StrictModel):
    mode: Literal["gemini", "groq", "ollama", "manual", "demo"]
    model: str = ""
    roof_width_m: float | None = Field(default=None, gt=0, le=100)
    roof_height_m: float | None = Field(default=None, gt=0, le=100)
    roof_confidence: float = Field(default=0, ge=0, le=1)
    obstacles: list[VisionObstacle]
    extracted_text: list[str] = []
    notes: list[str] = []
    roof_polygon_pct: list[NormalizedPoint] = Field(default_factory=list, max_length=50)
    events: list[dict] = []
    cached: bool = False
    elapsed_ms: float = 0
    input_kind: str = "drone"
    preview_data_url: str | None = None
    roof_polygon_image_pct: list[NormalizedPoint] = Field(default_factory=list, max_length=80)
    roof_crop_data_url: str | None = None
    roof_aspect_ratio: float | None = None
    coordinate_version: int = 1

    @model_validator(mode="after")
    def validate_extraction(self):
        if self.roof_polygon_pct:
            from shapely.geometry import Polygon
            if len(self.roof_polygon_pct) < 3:
                raise ValueError("Đường biên AI thiếu điểm.")
            polygon = Polygon([(p.x, p.y) for p in self.roof_polygon_pct])
            if not polygon.is_valid or polygon.area <= 0:
                raise ValueError("Đường biên AI tự cắt hoặc không có diện tích.")
        return self


class SceneRequest(BaseModel):
    config: ProjectConfig
    obstacles: list[RectObstacle] = Field(default_factory=list, max_length=100)
    date: date
    hour_local: float = Field(ge=0, le=23.99)
    heatmap: bool = True


class IrradianceResult(BaseModel):
    source: Literal["PVGIS", "fallback"]
    annual_irradiance_kwh_m2: float
    specific_yield_kwh_kwp: float
    detail: str
    reference_tilt_deg: float = 0
    reference_azimuth_deg: float = 180

class UncertaintyRequest(BaseModel):
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle]
    obstacle_id: str
    low_height_m: float
    high_height_m: float
    objective: Objective = "balanced"


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
