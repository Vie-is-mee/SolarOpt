"""Compare predictions against separately supplied references in drawing metres.

No automatic alignment/rescaling, no AI calls and no writes to project history.
Synthetic cases and field observations are always reported separately.
"""
from __future__ import annotations

from datetime import date as CalendarDate
import math
from typing import Literal
from pydantic import Field, model_validator
from shapely import hausdorff_distance
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.schemas import StrictModel, Point, DesignRequest, CandidatePanel, SunPosition, SunRequest
from app.services.geometry import roof_polygon, build_context
from app.services.solar import sun_position
from app.services.energy import recalculate_panels


class Region(StrictModel):
    boundary: list[Point] = Field(min_length=3, max_length=80)
    openings: list[list[Point]] = Field(default_factory=list, max_length=24)

    def shape(self):
        return Polygon([(p.x,p.y) for p in self.boundary],
                       [[(p.x,p.y) for p in ring] for ring in self.openings])

    @model_validator(mode='after')
    def valid_region(self):
        if any(len(r)<3 or len(r)>80 for r in self.openings):
            raise ValueError('Khoảng trống tham chiếu cần 3–80 điểm.')
        if not self.shape().is_valid or self.shape().area<=0:
            raise ValueError('Vùng tham chiếu phải có diện tích và không tự cắt.')
        if any(abs(p.x)>10000 or abs(p.y)>10000 for ring in [self.boundary,*self.openings] for p in ring):
            raise ValueError('Tọa độ đối chiếu phải theo mét trong hệ bản vẽ, không phải kinh/vĩ độ hoặc pixel.')
        return self


class ShadowReference(StrictModel):
    label: str = 'Bóng đối chiếu'
    source: str = Field(min_length=5, max_length=1000)
    date: CalendarDate | None = None
    hour_local: float | None = Field(default=None, ge=0, le=23.99)
    analytical_sun: SunPosition | None = None
    regions: list[Region] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def complete_time(self):
        if (self.date is None)!=(self.hour_local is None):
            raise ValueError('Cần đủ cả ngày và giờ của bóng tham chiếu.')
        timed=self.date is not None and self.hour_local is not None
        if (self.analytical_sun is not None)==timed:
            raise ValueError('Chọn ngày/giờ hoặc mặt trời giả lập; không dùng cả hai.')
        if self.analytical_sun is not None:
            s=self.analytical_sun
            if not all(math.isfinite(v) for v in (s.altitude_deg,s.azimuth_deg,s.zenith_deg)) or not(-90<=s.altitude_deg<=90 and 0<=s.azimuth_deg<=360 and 0<=s.zenith_deg<=180) or abs(s.altitude_deg+s.zenith_deg-90)>.01:
                raise ValueError('Góc mặt trời giả lập không hợp lệ.')
        return self


class EnergyReference(StrictModel):
    annual_energy_kwh: float = Field(gt=0)
    source: str = Field(min_length=5, max_length=1000)
    same_layout_confirmed: bool = False
    same_weather_inputs_confirmed: bool = False


class Tolerances(StrictModel):
    roof_iou_min: float | None = Field(default=None,ge=0,le=1)
    boundary_error_m_max: float | None = Field(default=None,ge=0,le=100)
    shadow_iou_min: float | None = Field(default=None,ge=0,le=1)
    energy_error_pct_max: float | None = Field(default=None,ge=0,le=100)
    agreed_by: str | None = None


class ValidationCase(StrictModel):
    id: str = Field(min_length=1,max_length=100)
    label: str = Field(min_length=1,max_length=200)
    kind: Literal['synthetic','field']
    stage: Literal['ai_initial','engineer_corrected','simulation']
    reference_source: str = Field(min_length=5,max_length=1000)
    reviewed_by: str | None = None
    evidence_files: list[str] = Field(default_factory=list,max_length=30)
    project: DesignRequest
    reference_roof: Region | None = None
    shadow_references: list[ShadowReference] = Field(default_factory=list,max_length=30)
    panels: list[CandidatePanel] = Field(default_factory=list,max_length=2000)
    energy_reference: EnergyReference | None = None
    tolerances: Tolerances = Field(default_factory=Tolerances)

    @model_validator(mode='after')
    def field_requires_real_time(self):
        if self.kind=='field' and any(s.analytical_sun is not None for s in self.shadow_references):
            raise ValueError('Ca mái thật phải dùng ngày/giờ, không dùng mặt trời giả lập.')
        return self


def compare_regions(predicted, reference):
    union=predicted.union(reference).area
    if predicted.is_empty and reference.is_empty:
        boundary=0.
    elif predicted.is_empty or reference.is_empty:
        boundary=None
    else:
        # Densified discrete Hausdorff, an approximation, not a certified bound.
        boundary=float(hausdorff_distance(predicted.boundary,reference.boundary,densify=.05))
    return {
        'iou':predicted.intersection(reference).area/union if union>0 else 1.,
        'boundary_error_m':boundary,
        'predicted_area_m2':predicted.area,'reference_area_m2':reference.area,
        'area_difference_m2':predicted.area-reference.area,
    }


def shape_regions(shape):
    if shape is None or shape.is_empty:return []
    if shape.geom_type=='Polygon':
        return [{'boundary':list(shape.exterior.coords),
                 'openings':[list(r.coords) for r in shape.interiors]}]
    return [region for part in getattr(shape,'geoms',[]) for region in shape_regions(part)]


def evaluate_case(case: ValidationCase):
    cfg=case.project.config
    predicted=roof_polygon(cfg)
    checks=[];missing=[]
    roof=None;reference=None
    if case.reference_roof is None:
        missing.append('Chưa có biên mái tham chiếu độc lập.')
    else:
        reference=case.reference_roof.shape()
        roof=compare_regions(predicted,reference)
        if case.tolerances.roof_iou_min is not None:
            checks.append(roof['iou']+1e-10>=case.tolerances.roof_iou_min)
        else:missing.append('Chưa thống nhất ngưỡng độ trùng diện tích mái.')
        if case.tolerances.boundary_error_m_max is not None:
            checks.append(roof['boundary_error_m'] is not None and roof['boundary_error_m']<=case.tolerances.boundary_error_m_max+1e-10)
        else:missing.append('Chưa thống nhất dung sai đường biên theo mét.')
    shadows=[]
    for sample in case.shadow_references:
        sun=sample.analytical_sun or sun_position(SunRequest(latitude=cfg.latitude,longitude=cfg.longitude,date=sample.date,hour_local=sample.hour_local))
        context=build_context(cfg,case.project.obstacles,sun)
        predicted_shadow=context.shadow_union if context.shadow_union is not None else Polygon()
        predicted_shadow=predicted_shadow.intersection(predicted)
        if sun.altitude_deg<=0:predicted_shadow=predicted
        observed=unary_union([r.shape() for r in sample.regions])
        # Never crop reference to the prediction: that would conceal a wrong roof.
        if reference is not None:observed=observed.intersection(reference)
        metrics=compare_regions(predicted_shadow,observed)
        shadows.append({'label':sample.label,'source':sample.source,'date':str(sample.date) if sample.date else None,
            'hour_local':sample.hour_local,'analytical':sample.analytical_sun is not None,
            **metrics,'predicted_regions':shape_regions(predicted_shadow),'reference_regions':shape_regions(observed)})
        if case.tolerances.shadow_iou_min is not None:checks.append(metrics['iou']+1e-10>=case.tolerances.shadow_iou_min)
    if not shadows:missing.append('Chưa có bóng tham chiếu.')
    elif case.tolerances.shadow_iou_min is None:missing.append('Chưa thống nhất ngưỡng độ trùng bóng.')
    energy=None
    if case.energy_reference is not None:
        ref=case.energy_reference
        if not case.panels:missing.append('Chưa có bố trí tấm để đối chiếu sản lượng.')
        elif not(ref.same_layout_confirmed and ref.same_weather_inputs_confirmed):
            missing.append('Chưa xác nhận cùng bố trí và đầu vào nắng khi so sản lượng.')
        else:
            panels=[p.model_copy(deep=True) for p in case.panels]
            recalculate_panels(cfg,case.project.panel,case.project.obstacles,panels)
            actual=sum(p.annual_energy_kwh for p in panels)
            error=100*abs(actual-ref.annual_energy_kwh)/ref.annual_energy_kwh
            energy={'predicted_kwh':actual,'reference_kwh':ref.annual_energy_kwh,'error_pct':error,'source':ref.source}
            if case.tolerances.energy_error_pct_max is not None:checks.append(error<=case.tolerances.energy_error_pct_max+1e-10)
            else:missing.append('Chưa thống nhất dung sai sản lượng.')
    elif case.kind=='field':missing.append('Chưa có sản lượng đối chiếu độc lập.')
    if case.kind=='field':
        if not case.reviewed_by or not case.evidence_files:missing.append('Chưa ghi người đối chiếu và hồ sơ nguồn.')
        if not case.tolerances.agreed_by:missing.append('Chưa ghi người thống nhất dung sai.')
    status='OUTSIDE_TOLERANCES' if False in checks else 'INCOMPLETE' if missing or not checks else 'SYNTHETIC_PASS' if case.kind=='synthetic' else 'WITHIN_DECLARED_TOLERANCES'
    return {'id':case.id,'label':case.label,'kind':case.kind,'stage':case.stage,'status':status,
        'reference_source':case.reference_source,'reviewed_by':case.reviewed_by,'evidence_files':case.evidence_files,
        'tolerances':case.tolerances.model_dump(),'roof':roof,'shadows':shadows,'energy':energy,
        'missing':missing,'predicted_roof':shape_regions(predicted),'reference_roof':shape_regions(reference),
        'scope':'Ca nhân tạo kiểm tra thuật toán; không chứng minh độ chính xác mái thật.' if case.kind=='synthetic' else 'Kết quả theo nguồn và dung sai người nhập khai báo; chưa chứng nhận độ chính xác thi công.'}
