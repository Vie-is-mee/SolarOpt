from __future__ import annotations

from .models import ProjectState, Design, Candidate
from .geometry import roof_polygon, candidate_poly
from shapely.geometry import box


def greedy_optimize(state: ProjectState, mode: str = "balanced", preserve_ids: set[str] | None = None, excluded_ids: set[str] | None = None) -> Design:
    preserve_ids = preserve_ids or set()
    excluded_ids = excluded_ids or set()
    candidates = state.candidates
    by_id = {c.id: c for c in candidates}

    # Different design personalities, but deterministic.
    def value(c: Candidate):
        if mode == "energy":
            return c.energy_kwh - 250 * c.shade_loss
        if mode == "robust":
            edge_margin = min(c.x, c.y)
            return c.energy_kwh - 720 * c.shade_loss + min(edge_margin, 1.2) * 18
        # balanced: reward staying close to prior design during repair
        keep_bonus = 95 if c.id in preserve_ids else 0
        return c.energy_kwh - 480 * c.shade_loss + keep_bonus

    ordered = sorted(candidates, key=lambda c: (value(c), c.energy_kwh), reverse=True)
    chosen: list[Candidate] = []
    blocked: set[str] = set()

    # If repairing, lock valid preserved candidates first.
    for cid in preserve_ids:
        c = by_id.get(cid)
        if c and cid not in blocked and c.shade_loss <= 0.115:
            chosen.append(c)
            blocked.add(cid)
            blocked.update(c.conflicts)

    tall_tank = next((o for o in state.obstacles if o.id == "TANK" and o.object_height_m >= 1.7), None)
    tall_zone = None
    if tall_tank is not None:
        tall_zone = box(tall_tank.x, tall_tank.y, tall_tank.x + tall_tank.width, tall_tank.y + tall_tank.height).buffer(0.55)

    for c in ordered:
        if c.id in blocked or c.id in excluded_ids:
            continue
        if tall_zone is not None and candidate_poly(c).intersects(tall_zone):
            continue
        # layout accepts modest shade, verifier handles stricter scenario tests
        if c.shade_loss > 0.115:
            continue
        chosen.append(c)
        blocked.add(c.id)
        blocked.update(c.conflicts)

    ids = [c.id for c in chosen]
    energy = round(sum(c.energy_kwh for c in chosen), 1)
    cost = len(chosen) * state.panel.price_vnd
    panel_area = sum(c.width * c.height for c in chosen)
    roof_area = roof_polygon(state).area
    utilization = round(100 * panel_area / roof_area, 1)

    version = (state.design.version + 1) if state.design else 1
    return Design(
        id=f"D{version}",
        version=version,
        label={"energy": "Maximum Energy", "robust": "Most Robust"}.get(mode, "Balanced"),
        candidate_ids=ids,
        energy_kwh=energy,
        cost_vnd=cost,
        roof_utilization=utilization,
    )


def repair_design(state: ProjectState, failing_ids: list[str]) -> tuple[Design, dict]:
    old = state.design
    old_ids = set(old.candidate_ids if old else [])
    preserve = old_ids - set(failing_ids)
    repaired = greedy_optimize(state, mode="balanced", preserve_ids=preserve, excluded_ids=set(failing_ids))

    new_ids = set(repaired.candidate_ids)
    removed = sorted(old_ids - new_ids)
    added = sorted(new_ids - old_ids)
    kept = sorted(old_ids & new_ids)
    delta = {
        "kept": len(kept),
        "removed": removed,
        "added": added,
        "changed_count": len(removed) + len(added),
        "energy_before": old.energy_kwh if old else None,
        "energy_after": repaired.energy_kwh,
    }
    repaired.notes.append(f"Minimal-change repair kept {len(kept)} existing placements.")
    return repaired, delta
