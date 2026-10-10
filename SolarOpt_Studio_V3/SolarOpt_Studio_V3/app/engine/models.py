from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Tuple, Any


@dataclass
class PanelModel:
    id: str
    name: str
    width_m: float
    height_m: float
    power_w: int
    price_vnd: int
    efficiency: float


@dataclass
class Obstacle:
    id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    object_height_m: float
    confidence: float = 1.0
    kind: str = "obstacle"
    impact_hint: str = "medium"


@dataclass
class Candidate:
    id: str
    x: float
    y: float
    width: float
    height: float
    orientation: str
    energy_kwh: float = 0.0
    shade_loss: float = 0.0
    conflicts: List[str] = field(default_factory=list)


@dataclass
class Design:
    id: str
    version: int
    label: str
    candidate_ids: List[str]
    energy_kwh: float
    cost_vnd: int
    roof_utilization: float
    stress_passed: int = 0
    stress_total: int = 0
    verified: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class ProjectState:
    project_id: str
    roof_polygon: List[Tuple[float, float]]
    roof_tilt_deg: float
    roof_azimuth_deg: float
    latitude: float
    longitude: float
    edge_setback_m: float
    maintenance_gap_m: float
    panel: PanelModel
    obstacles: List[Obstacle]
    candidates: List[Candidate] = field(default_factory=list)
    design: Design | None = None
    versions: List[Design] = field(default_factory=list)
    design_options: List[Design] = field(default_factory=list)
    stress_results: List[Dict[str, Any]] = field(default_factory=list)
    last_repair: Dict[str, Any] = field(default_factory=dict)
    last_change: Dict[str, Any] = field(default_factory=dict)
    last_verification: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_attention: List[Dict[str, Any]] = field(default_factory=list)
    dependency_status: Dict[str, str] = field(default_factory=dict)
    objective: str = "balanced"
    budget_vnd: int = 120_000_000
    inverter_name: str = "Huawei SUN2000-12K-MAP0"
    uploaded_file: Dict[str, Any] = field(default_factory=dict)
    source_label: str = "Bản vẽ mẫu SolarOpt"

    def to_dict(self):
        return asdict(self)
