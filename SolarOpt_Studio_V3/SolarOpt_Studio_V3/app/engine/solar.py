from __future__ import annotations

import math
from shapely.geometry import box
from shapely.affinity import translate

from .models import ProjectState, Candidate
from .geometry import candidate_poly


def shadow_polygon(obstacle, sun_elevation_deg: float = 34.0, sun_from_south: bool = True):
    base = box(obstacle.x, obstacle.y, obstacle.x + obstacle.width, obstacle.y + obstacle.height)
    elevation = max(8.0, sun_elevation_deg)
    shadow_len = obstacle.object_height_m / math.tan(math.radians(elevation))
    # In this demo north is +Y; afternoon/winter shade is approximated as stretching north.
    if sun_from_south:
        ext = box(
            obstacle.x - 0.15,
            obstacle.y,
            obstacle.x + obstacle.width + 0.15,
            obstacle.y + obstacle.height + shadow_len,
        )
    else:
        ext = box(
            obstacle.x - 0.15,
            obstacle.y - shadow_len,
            obstacle.x + obstacle.width + 0.15,
            obstacle.y + obstacle.height,
        )
    return base.union(ext)


def candidate_solar_metrics(state: ProjectState, c: Candidate, sun_elevation_deg: float = 34.0):
    poly = candidate_poly(c)
    overlap = 0.0
    for obs in state.obstacles:
        if obs.kind in {"obstacle", "unknown"}:
            sh = shadow_polygon(obs, sun_elevation_deg=sun_elevation_deg)
            overlap = max(overlap, poly.intersection(sh).area / max(poly.area, 1e-9))

    # small north/south gradient makes placements visibly different
    roof_max_y = max(y for _, y in state.roof_polygon)
    center_y = c.y + c.height / 2
    solar_gradient = 0.97 + 0.03 * (center_y / max(roof_max_y, 1.0))
    orientation_factor = 1.00 if c.orientation == "portrait" else 0.985
    # annual yield proxy based on module power; deterministic for demo
    base = state.panel.power_w * 1.48
    shade_loss = min(0.75, overlap * 0.72)
    energy = base * solar_gradient * orientation_factor * (1 - shade_loss)
    return round(energy, 2), round(shade_loss, 4)


def score_candidates(state: ProjectState, sun_elevation_deg: float = 34.0):
    for c in state.candidates:
        energy, shade = candidate_solar_metrics(state, c, sun_elevation_deg)
        c.energy_kwh = energy
        c.shade_loss = shade
    return state.candidates
