from __future__ import annotations

from collections import deque

from app.schemas import DependencyImpact


DEPENDENCIES: dict[str, list[str]] = {
    "roof_geometry": ["feasible_region", "layout"],
    "roof_dimensions": ["roof_geometry"],
    "roof_orientation": ["sun_geometry", "irradiance", "energy"],
    "obstacle_geometry": ["feasible_region", "shadow_map"],
    "obstacle_height": ["shadow_map"],
    "shadow_map": ["feasible_region", "energy"],
    "panel_spec": ["candidate_grid", "layout", "electrical", "cost", "energy"],
    "candidate_grid": ["layout"],
    "feasible_region": ["layout"],
    "layout": ["energy", "electrical", "cost", "verification"],
    "irradiance": ["energy"],
    "energy": ["roi", "verification"],
    "cost": ["roi", "verification"],
    "electrical": ["verification"],
    "verification": ["report"],
    "roi": ["report"],
}

ALL_NODES = sorted(set(DEPENDENCIES) | {x for vs in DEPENDENCIES.values() for x in vs})


def trace_impact(changed_input: str) -> DependencyImpact:
    q = deque([changed_input])
    seen = {changed_input}
    affected: list[str] = []
    while q:
        cur = q.popleft()
        for nxt in DEPENDENCIES.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                affected.append(nxt)
                q.append(nxt)
    reused = [n for n in ALL_NODES if n not in seen]
    ratio = 100.0 * len(affected) / max(1, len(ALL_NODES))
    return DependencyImpact(
        changed_input=changed_input,
        affected_nodes=affected,
        reused_nodes=reused,
        recomputation_ratio_pct=round(ratio, 1),
    )
