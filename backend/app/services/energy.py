"""Shared, reproducible preliminary energy calculation, with no network calls.

Annual input is irradiance on an explicitly declared reference plane. Ratios
between that plane and roof faces use pvlib clear-sky transposition on twelve
monthly representative days (24 hourly midpoints, weighted by days/month).
This corrects orientation dependence; it is NOT an hourly weather-year model.
Shading retains the MVP's nine representative instants and empirical loss rule.
"""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from shapely import prepare

from app.schemas import DesignMetrics, SunRequest
from app.services.geometry import build_context, overlap_ratio, panel_shape
from app.services.solar import sun_position

MODEL_NOTE = ("Nắng năm được quy đổi riêng theo hướng/độ dốc từng mặt mái bằng pvlib "
              "với 12 ngày trời quang đại diện; bóng dùng 9 thời điểm. "
              "Chưa phải mô phỏng 8760 giờ với thời tiết thực hoặc đã đối chuẩn.")


@lru_cache(maxsize=128)
def _sky(latitude, longitude):
    import numpy as np
    import pandas as pd
    import pvlib
    times = pd.DatetimeIndex([
        f"2026-{month:02d}-15 {hour:02d}:30:00"
        for month in range(1, 13) for hour in range(24)
    ]).tz_localize("Asia/Ho_Chi_Minh")
    position = pvlib.solarposition.get_solarposition(times, latitude, longitude)
    sky = pvlib.location.Location(latitude, longitude, tz="Asia/Ho_Chi_Minh").get_clearsky(times)
    weights = np.repeat([monthrange(2026, m)[1] for m in range(1, 13)], 24)
    return position, sky, weights


@lru_cache(maxsize=2048)
def _plane_sum(latitude, longitude, tilt, azimuth):
    import pvlib
    position, sky, weights = _sky(latitude, longitude)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, azimuth, position.apparent_zenith, position.azimuth,
        sky.dni, sky.ghi, sky.dhi,
    )["poa_global"].fillna(0).clip(lower=0)
    return float((poa.to_numpy() * weights).sum()) / 1000


@lru_cache(maxsize=256)
def _tracker_sum(latitude, longitude, gcr, max_angle):
    """Clear-sky plane-of-array sum for a horizontal 1-axis tracker on a N-S axis, with backtracking
    so rows never shade each other (pvlib); same representative days and weights as _plane_sum."""
    import pvlib
    position, sky, weights = _sky(latitude, longitude)
    track = pvlib.tracking.singleaxis(position.apparent_zenith, position.azimuth, axis_tilt=0, axis_azimuth=180,
                                      max_angle=max_angle, backtrack=True, gcr=gcr)
    poa = pvlib.irradiance.get_total_irradiance(
        track["surface_tilt"].fillna(0), track["surface_azimuth"].fillna(180), position.apparent_zenith, position.azimuth,
        sky.dni, sky.ghi, sky.dhi,
    )["poa_global"].fillna(0).clip(lower=0)
    return float((poa.to_numpy() * weights).sum()) / 1000


def plane_annual_irradiance(cfg, surface):
    """Annual irradiance on the panels of a face: the face itself, a tilted rack, or a tracker."""
    reference = _plane_sum(cfg.latitude, cfg.longitude,
                           cfg.irradiance_reference_tilt_deg, cfg.irradiance_reference_azimuth_deg)
    if reference <= 0:
        raise ValueError("Không xác định được bức xạ trên mặt tham chiếu; kiểm tra vị trí và hướng.")
    mount = getattr(surface, "mount", None)
    if mount == "tracker":
        target = _tracker_sum(cfg.latitude, cfg.longitude, round(cfg.tracker_gcr, 4), cfg.tracker_max_angle_deg)
    elif mount == "tilted_rack":
        target = _plane_sum(cfg.latitude, cfg.longitude, surface.mount_tilt, surface.mount_azimuth)
    else:
        target = _plane_sum(cfg.latitude, cfg.longitude, surface.tilt, surface.azimuth)
    return cfg.annual_irradiance_kwh_m2 * target / reference


def representative_contexts(cfg, obstacles):
    contexts = []
    for day in (date(2026, 3, 21), date(2026, 6, 21), date(2026, 12, 21)):
        for hour in (9., 12., 15.):
            sun = sun_position(SunRequest(latitude=cfg.latitude, longitude=cfg.longitude,
                                          date=day, hour_local=hour))
            if sun.altitude_deg > 3:
                contexts.append(build_context(cfg, obstacles, sun))
    return contexts


@dataclass(frozen=True)
class PanelEnergy:
    annual_kwh: float
    loss_pct: float
    mean_cover: float
    worst_cover: float
    face_id: str | None


class EnergyContext:
    def __init__(self, cfg, obstacles, geometry=None, shade_contexts=None):
        self.cfg = cfg
        self.geometry = geometry if geometry is not None else build_context(cfg, obstacles, None)
        self.shades = shade_contexts if shade_contexts is not None else representative_contexts(cfg, obstacles)
        for context in self.shades:prepare(context.shadow_union)
        self.surface_regions = [(s, s.polygon.buffer(1e-7)) for s in self.geometry.surfaces]
        for _, region in self.surface_regions:prepare(region)
        self.annual = {s.id: plane_annual_irradiance(cfg, s) for s in self.geometry.surfaces}

    def evaluate(self, shape, power_w, surface=None):
        if surface is None:
            surface = next((s for s, region in self.surface_regions if region.covers(shape)), None)
        covers = [overlap_ratio(shape, c.shadow_union) for c in self.shades]
        mean, worst = sum(covers) / max(1, len(covers)), max(covers, default=0)
        loss = round(min(70., (.72 * mean + .28 * worst) * 78), 2)
        annual = self.annual.get(surface.id, 0) if surface is not None else 0
        kwh = round(power_w / 1000 * annual * self.cfg.performance_ratio * (1 - loss / 100), 2)
        return PanelEnergy(kwh, loss, mean, worst, surface.id if surface is not None else None)


def recalculate_panels(cfg, spec, obstacles, panels):
    context = EnergyContext(cfg, obstacles)
    evaluations = []
    for panel in panels:
        value = context.evaluate(panel_shape(panel.x, panel.y, panel.width_m, panel.height_m, panel.rotation_deg), spec.power_w)
        panel.annual_energy_kwh, panel.shading_loss_pct = value.annual_kwh, value.loss_pct
        panel.face_id = value.face_id or "outside"
        evaluations.append(value)
    return context, evaluations


def summarize(cfg, spec, panels, roof_area, preserved_count=0, previous_count=0):
    energy = sum(p.annual_energy_kwh for p in panels)
    return DesignMetrics(
        panel_count=len(panels), peak_power_kwp=round(len(panels) * spec.power_w / 1000, 3),
        annual_energy_kwh=round(energy, 1), annual_energy_mwh=round(energy / 1000, 3),
        estimated_cost_vnd=round(len(panels) * spec.price_vnd, 0),
        average_shading_loss_pct=round(sum(p.shading_loss_pct for p in panels) / max(1, len(panels)), 2),
        maximum_shading_loss_pct=max((p.shading_loss_pct for p in panels), default=0),
        roof_utilization_pct=round(100 * sum(p.width_m*p.height_m for p in panels) / max(roof_area, 1e-6), 1),
        preserved_panel_count=preserved_count,
        layout_preservation_rate_pct=round(100 * preserved_count / max(1, previous_count), 1) if previous_count else 0,
    )
