from __future__ import annotations

from typing import Iterable
from shapely.geometry import Polygon, box
from shapely.affinity import translate

from .models import ProjectState, Candidate


def roof_polygon(state: ProjectState) -> Polygon:
    return Polygon(state.roof_polygon)


def obstacle_polygon(obstacle, clearance: float = 0.18) -> Polygon:
    return box(
        obstacle.x - clearance,
        obstacle.y - clearance,
        obstacle.x + obstacle.width + clearance,
        obstacle.y + obstacle.height + clearance,
    )


def usable_polygon(state: ProjectState) -> Polygon:
    usable = roof_polygon(state).buffer(-state.edge_setback_m)
    for obs in state.obstacles:
        if obs.kind in {"obstacle", "skylight", "unknown"}:
            usable = usable.difference(obstacle_polygon(obs))
    return usable


def candidate_poly(c: Candidate) -> Polygon:
    return box(c.x, c.y, c.x + c.width, c.y + c.height)


def generate_candidates(state: ProjectState, step_m: float = 0.34):
    usable = usable_polygon(state)
    panel = state.panel
    candidates: list[Candidate] = []
    idx = 1

    minx, miny, maxx, maxy = usable.bounds
    orientations = [
        ("portrait", panel.width_m, panel.height_m),
        ("landscape", panel.height_m, panel.width_m),
    ]

    # several grid offsets create a richer search space without brute-forcing every pixel
    offsets = [0.0, step_m / 2]
    for orient, w, h in orientations:
        for ox in offsets:
            for oy in offsets:
                y = miny + oy
                while y + h <= maxy + 1e-9:
                    x = minx + ox
                    while x + w <= maxx + 1e-9:
                        poly = box(x, y, x + w, y + h)
                        if usable.covers(poly):
                            candidates.append(
                                Candidate(
                                    id=f"C{idx:04d}",
                                    x=round(x, 3),
                                    y=round(y, 3),
                                    width=round(w, 3),
                                    height=round(h, 3),
                                    orientation=orient,
                                )
                            )
                            idx += 1
                        x += step_m
                    y += step_m

    # deduplicate very similar placements
    seen = set()
    unique = []
    for c in candidates:
        key = (round(c.x, 2), round(c.y, 2), round(c.width, 2), round(c.height, 2))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    state.candidates = unique
    return unique


def build_conflicts(candidates: Iterable[Candidate]):
    """Build overlap graph using a coarse spatial hash.

    Candidates are axis-aligned rectangles in roof-plane coordinates, so we can avoid
    expensive all-pairs Shapely intersections. This keeps the demo responsive even
    with ~2k candidate placements.
    """
    candidates = list(candidates)
    conflict_map = {c.id: [] for c in candidates}
    by_id = {c.id: c for c in candidates}
    cell = 2.6  # slightly larger than the longest demo panel side
    buckets: dict[tuple[int, int], list[str]] = {}

    def cells_for(c: Candidate):
        x0 = int(c.x // cell); x1 = int((c.x + c.width) // cell)
        y0 = int(c.y // cell); y1 = int((c.y + c.height) // cell)
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                yield gx, gy

    for c in candidates:
        for key in cells_for(c):
            buckets.setdefault(key, []).append(c.id)

    seen_pairs = set()
    for ids in buckets.values():
        n = len(ids)
        for i in range(n):
            a = by_id[ids[i]]
            for j in range(i + 1, n):
                b = by_id[ids[j]]
                pair = (a.id, b.id) if a.id < b.id else (b.id, a.id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                # positive-area rectangle overlap; touching edges is allowed
                ox = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
                oy = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
                if ox > 0.01 and oy > 0.01:
                    conflict_map[a.id].append(b.id)
                    conflict_map[b.id].append(a.id)

    for c in candidates:
        c.conflicts = conflict_map[c.id]
    return conflict_map
