"""Shared, reproducible preliminary energy calculation, with no network calls.

Annual input is irradiance on an explicitly declared reference plane. Ratios
between that plane and roof faces use pvlib clear-sky transposition on twelve
monthly representative days (24 hourly midpoints, weighted by days/month).
This corrects orientation dependence; it is NOT an hourly weather-year model.

Shading (ShadeSeries): every daylight hour of the same twelve days (about 140 instants) casts
the obstacles' shadows, rasterised on a ~10 cm grid of the roof. Each panel is sampled on its
three bypass-diode substrings; a substring loses beam power in proportion to three times its
shaded share (a third shaded switches it off), the usual simplification for cells in series.
Beam loss is weighted by that instant's clear-sky beam on the panel's plane; diffuse light is
treated as unshaded. Passing explicit shade contexts keeps the earlier nine-instant rule.
"""
from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from threading import Lock
from shapely import prepare

from app.schemas import DesignMetrics, SunPosition, SunRequest
from app.services.geometry import build_context, overlap_ratio, overlap_ratios, panel_shape
from app.services.solar import sun_position

MODEL_NOTE = ("Nắng năm được quy đổi riêng theo hướng/độ dốc từng mặt mái bằng pvlib "
              "với 12 ngày trời quang đại diện; bóng tính cho mọi giờ có nắng của 12 ngày đó, "
              "theo 3 chuỗi cell có diode bypass của mỗi tấm. "
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


@lru_cache(maxsize=2048)
def _plane_months(latitude, longitude, tilt, azimuth, tracker=None):
    """Share of each month in the clear-sky plane-of-array year (12 values summing to 1).
    Same representative days and weights as _plane_sum; tracker=(gcr, max_angle) for 1-axis."""
    import numpy as np
    import pvlib
    position, sky, weights = _sky(latitude, longitude)
    if tracker:
        track = pvlib.tracking.singleaxis(position.apparent_zenith, position.azimuth, axis_tilt=0, axis_azimuth=180,
                                          max_angle=tracker[1], backtrack=True, gcr=tracker[0])
        tilt, azimuth = track["surface_tilt"].fillna(0), track["surface_azimuth"].fillna(180)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, azimuth, position.apparent_zenith, position.azimuth, sky.dni, sky.ghi, sky.dhi,
    )["poa_global"].fillna(0).clip(lower=0).to_numpy() * weights
    months = poa.reshape(12, 24).sum(axis=1)
    total = months.sum()
    return tuple(float(v) for v in (months / total if total > 0 else np.full(12, 1 / 12)))


def monthly_shares(cfg, surface):
    mount = getattr(surface, "mount", None)
    if mount == "tracker":
        return _plane_months(cfg.latitude, cfg.longitude, 0, 180, (round(cfg.tracker_gcr, 4), cfg.tracker_max_angle_deg))
    if mount == "tilted_rack":
        return _plane_months(cfg.latitude, cfg.longitude, surface.mount_tilt, surface.mount_azimuth)
    return _plane_months(cfg.latitude, cfg.longitude, surface.tilt, surface.azimuth)


def monthly_energy(cfg, obstacles, panels):
    """Annual panel energy spread over months by each face's clear-sky irradiance profile.
    The annual shading loss is applied evenly, so this shows seasonality, not monthly weather."""
    if not panels:
        return []
    surfaces = {s.id: s for s in build_context(cfg, obstacles, None).surfaces}
    months = [0.0] * 12
    for panel in panels:
        surface = surfaces.get(panel.face_id)
        shares = monthly_shares(cfg, surface) if surface is not None else (1 / 12,) * 12
        for m, share in enumerate(shares):
            months[m] += panel.annual_energy_kwh * share
    return [round(v, 1) for v in months]


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


@lru_cache(maxsize=2048)
def _plane_components(latitude, longitude, tilt, azimuth, tracker=None):
    """Clear-sky beam and diffuse irradiance (W/m²) on a plane at the 288 representative instants."""
    import numpy as np
    import pvlib
    position, sky, _ = _sky(latitude, longitude)
    if tracker:
        track = pvlib.tracking.singleaxis(position.apparent_zenith, position.azimuth, axis_tilt=0, axis_azimuth=180,
                                          max_angle=tracker[1], backtrack=True, gcr=tracker[0])
        tilt, azimuth = track["surface_tilt"].fillna(0), track["surface_azimuth"].fillna(180)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, azimuth, position.apparent_zenith, position.azimuth, sky.dni, sky.ghi, sky.dhi)
    beam = poa["poa_direct"].fillna(0).clip(lower=0).to_numpy()
    diffuse = poa["poa_diffuse"].fillna(0).clip(lower=0).to_numpy()
    return np.asarray(beam), np.asarray(diffuse)


def plane_components(cfg, surface):
    mount = getattr(surface, "mount", None)
    if mount == "tracker":
        return _plane_components(cfg.latitude, cfg.longitude, 0, 180, (round(cfg.tracker_gcr, 4), cfg.tracker_max_angle_deg))
    if mount == "tilted_rack":
        return _plane_components(cfg.latitude, cfg.longitude, surface.mount_tilt, surface.mount_azimuth)
    return _plane_components(cfg.latitude, cfg.longitude, surface.tilt, surface.azimuth)


SUBSTRINGS = 3                    # bypass diodes per module (60/120-cell and 72/144-cell modules)
ACROSS, ALONG = 2, 6              # sample points per substring: across its width, along the module
# Instants of the "worst shade" rule: equinox / solstice months (15 Mar, Jun, Dec) at 9:30, 12:30 and 14:30, the
# hourly counterpart of the earlier nine representative instants. Energy loss uses every daylight hour.
CHECK_MONTHS, CHECK_HOURS = (2, 5, 11), (9, 12, 14)
MIN_ALTITUDE = 5.0                # lower sun: little beam on the panels and shadows longer than any roof


@dataclass
class ShadeSeries:
    """Shadow raster for every daylight instant: mask[row, col, t] is True where shade falls.
    Time is the last axis so one panel's samples gather a contiguous run of instants."""
    index: object       # positions in the 288-instant grid (month * 24 + hour)
    weights: object     # days in the instant's month
    core: object        # instant is one of the worst-shade check instants
    x0: float
    y0: float
    cell: float
    mask: object

    def sample(self, xs, ys):
        """Shade at drawing points (any array shape) for every instant: bool array (*shape, T)."""
        import numpy as np
        rows, cols, _ = self.mask.shape
        ix = np.clip(np.floor((xs - self.x0) / self.cell).astype(int), 0, cols - 1)
        iy = np.clip(np.floor((ys - self.y0) / self.cell).astype(int), 0, rows - 1)
        return self.mask[iy, ix]


_SERIES = OrderedDict()
_SERIES_LOCK = Lock()


def shade_series(cfg, obstacles, geometry):
    """Build (or reuse) the hourly shadow raster of a project. Cached on geometry, obstacles and site,
    so the three options of one calculation, verification and stress tests share it."""
    import numpy as np
    import shapely
    key = hashlib.sha256(json.dumps([cfg.model_dump(mode="json"), [o.model_dump(mode="json") for o in obstacles]],
                                    sort_keys=True).encode()).hexdigest()
    with _SERIES_LOCK:
        if key in _SERIES:
            _SERIES.move_to_end(key)
            return _SERIES[key]
    position, _, weights = _sky(cfg.latitude, cfg.longitude)
    altitude = 90 - position.apparent_zenith.to_numpy()
    azimuth = position.azimuth.to_numpy()
    index = np.flatnonzero(altitude > MIN_ALTITUDE)
    bounds = shapely.total_bounds([geometry.roof, *(s.polygon for s in geometry.surfaces)])
    # A roof with nothing installable (e.g. all opening) has no extent; a 1 m cell keeps the series valid.
    minx, miny, maxx, maxy = bounds if np.all(np.isfinite(bounds)) else (0., 0., 1., 1.)
    cell = max(.1, ((maxx - minx) * (maxy - miny) / 100_000) ** .5)   # at most ~100k cells
    cols, rows = max(1, int(np.ceil((maxx - minx) / cell))), max(1, int(np.ceil((maxy - miny) / cell)))
    gx, gy = np.meshgrid(minx + (np.arange(cols) + .5) * cell, miny + (np.arange(rows) + .5) * cell)
    gx, gy = gx.ravel(), gy.ravel()
    mask = np.zeros((rows, cols, len(index)), dtype=bool)
    for t, i in enumerate(index):
        sun = SunPosition(altitude_deg=float(altitude[i]), azimuth_deg=float(azimuth[i]), zenith_deg=float(90 - altitude[i]))
        shadow = build_context(cfg, obstacles, sun).shadow_union
        if shadow is not None and not shadow.is_empty:
            prepare(shadow)
            mask[:, :, t] = shapely.contains_xy(shadow, gx, gy).reshape(rows, cols)
    series = ShadeSeries(index=index, weights=np.asarray(weights)[index].astype(float),
                         core=np.isin(index // 24, CHECK_MONTHS) & np.isin(index % 24, CHECK_HOURS),
                         x0=float(minx), y0=float(miny), cell=float(cell), mask=mask)
    with _SERIES_LOCK:
        _SERIES[key] = series
        while len(_SERIES) > 2:
            _SERIES.popitem(last=False)
    return series


def _substring_points(shapes):
    """Sample points of each module's three substrings, from the module rectangles themselves.
    Substrings run along the long side and split the short side in three. Arrays (N, 3, ACROSS*ALONG)."""
    import numpy as np
    import shapely
    c = shapely.get_coordinates(shapes).reshape(-1, 5, 2)
    p0, p1, p2 = c[:, 0], c[:, 1], c[:, 2]          # (maxx,miny) -> (maxx,maxy) -> (minx,maxy), rotated
    h, w = np.linalg.norm(p1 - p0, axis=1), np.linalg.norm(p2 - p1, axis=1)
    uy, ux = (p1 - p0) / h[:, None], (p1 - p2) / w[:, None]
    centre = (p0 + p2) / 2
    portrait = w <= h
    short_dir, long_dir = np.where(portrait[:, None], ux, uy), np.where(portrait[:, None], uy, ux)
    short_len, long_len = np.where(portrait, w, h), np.where(portrait, h, w)
    s = np.arange(SUBSTRINGS)[:, None, None]
    a = (s + (np.arange(ACROSS)[None, :, None] + .5) / ACROSS) / SUBSTRINGS - .5      # (3, ACROSS, 1)
    b = (np.arange(ALONG)[None, None, :] + .5) / ALONG - .5                          # (1, 1, ALONG)
    a, b = np.broadcast_arrays(a, b)
    a, b = a.reshape(SUBSTRINGS, -1), b.reshape(SUBSTRINGS, -1)
    pts = (centre[:, None, None, :] + (a[None] * short_len[:, None, None])[..., None] * short_dir[:, None, None, :]
           + (b[None] * long_len[:, None, None])[..., None] * long_dir[:, None, None, :])
    return pts[..., 0], pts[..., 1]


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
        # Explicit contexts keep the earlier nine-instant rule (tests and callers that pass their own);
        # otherwise the hourly shadow raster and the substring model are used.
        self.series = shade_series(cfg, obstacles, self.geometry) if shade_contexts is None else None
        self.shades = shade_contexts if shade_contexts is not None else []
        for context in self.shades:prepare(context.shadow_union)
        self.surface_regions = [(s, s.polygon.buffer(1e-7)) for s in self.geometry.surfaces]
        for _, region in self.surface_regions:prepare(region)
        self.annual = {s.id: plane_annual_irradiance(cfg, s) for s in self.geometry.surfaces}
        self._weighted = {}

    def _components(self, surface):
        """Day-weighted beam (T,), its sum, and beam + diffuse sum on a surface, at the series instants."""
        if surface.id not in self._weighted:
            beam, diffuse = (v[self.series.index] * self.series.weights for v in plane_components(self.cfg, surface))
            self._weighted[surface.id] = (beam, float(beam.sum()), float(beam.sum() + diffuse.sum()))
        return self._weighted[surface.id]

    def evaluate(self, shape, power_w, surface=None):
        if surface is None:
            surface = next((s for s, region in self.surface_regions if region.covers(shape)), None)
        if self.series is not None:
            import numpy as np
            return self._hourly(np.array([shape]), power_w, [surface])[0]
        covers = [overlap_ratio(shape, c.shadow_union) for c in self.shades]
        mean, worst = sum(covers) / max(1, len(covers)), max(covers, default=0)
        loss = round(min(70., (.72 * mean + .28 * worst) * 78), 2)
        annual = self.annual.get(surface.id, 0) if surface is not None else 0
        kwh = round(power_w / 1000 * annual * self.cfg.performance_ratio * (1 - loss / 100), 2)
        return PanelEnergy(kwh, loss, mean, worst, surface.id if surface is not None else None)


    def evaluate_many(self, shapes, power_w, surfaces):
        """evaluate() for an array of shapes on known surfaces, with identical results:
        shadow overlaps are computed per context in one vectorised call, the sums stay in Python order."""
        if self.series is not None:
            return self._hourly(shapes, power_w, surfaces)
        covers = [overlap_ratios(shapes, c.shadow_union) for c in self.shades]
        out = []
        for i, surface in enumerate(surfaces):
            column = [float(c[i]) for c in covers]
            mean, worst = sum(column) / max(1, len(column)), max(column, default=0)
            loss = round(min(70., (.72 * mean + .28 * worst) * 78), 2)
            annual = self.annual.get(surface.id, 0)
            kwh = round(power_w / 1000 * annual * self.cfg.performance_ratio * (1 - loss / 100), 2)
            out.append(PanelEnergy(kwh, loss, mean, worst, surface.id))
        return out


    def _hourly(self, shapes, power_w, surfaces):
        """Substring model over the hourly shadow raster (see module notes)."""
        import numpy as np
        series, out = self.series, []
        step = 400                                                      # keeps temporaries to a few MB
        per_sub = ACROSS * ALONG
        for start in range(0, len(shapes), step):
            group = surfaces[start:start + step]
            xs, ys = _substring_points(shapes[start:start + step])
            shaded = np.count_nonzero(series.sample(xs, ys), axis=2) / per_sub   # (N, 3, T) shaded share
            beam_loss = np.minimum(1, SUBSTRINGS * shaded).mean(axis=1)           # (N, T)
            geometric = shaded.mean(axis=1)                                        # (N, T)
            # Per-row reductions along the contiguous time axis: each panel's sum is computed the same
            # way whether one panel or a whole grid is evaluated, so verification reproduces the figures.
            known = [i for i, surface in enumerate(group) if surface is not None]
            beam = np.zeros_like(geometric);direct = np.ones(len(group));total = np.ones(len(group))
            for i in known:
                beam[i], direct[i], total[i] = self._components(group[i])
            lost = (beam_loss * beam).sum(axis=1)
            seen = (geometric * beam).sum(axis=1)
            worst = geometric[:, series.core].max(axis=1, initial=0)
            # Plain floats from here: round() on numpy scalars is several times slower.
            lost, seen, worst, direct, total = lost.tolist(), seen.tolist(), worst.tolist(), direct.tolist(), total.tolist()
            for i, surface in enumerate(group):
                if surface is None:
                    out.append(PanelEnergy(0, 0, 0, 0, None))
                    continue
                loss = round(min(100., 100 * lost[i] / total[i]), 2) if total[i] > 0 else 0.
                mean = seen[i] / direct[i] if direct[i] > 0 else 0.
                annual = self.annual.get(surface.id, 0)
                kwh = round(power_w / 1000 * annual * self.cfg.performance_ratio * (1 - loss / 100), 2)
                out.append(PanelEnergy(kwh, loss, mean, worst[i], surface.id))
        return out


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
