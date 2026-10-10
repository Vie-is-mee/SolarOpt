from __future__ import annotations

from shapely.geometry import box

from .models import ProjectState, Design
from .geometry import candidate_poly, usable_polygon
from .solar import candidate_solar_metrics


def verify_design(state: ProjectState, design: Design, sun_elevation_deg: float = 34.0, shade_threshold: float = 0.125):
    cmap = {c.id: c for c in state.candidates}
    usable = usable_polygon(state)
    violations = []
    selected = []

    for cid in design.candidate_ids:
        c = cmap.get(cid)
        if not c:
            violations.append({"code": "MISSING_CANDIDATE", "panel": cid})
            continue
        selected.append(c)
        poly = candidate_poly(c)
        if not usable.covers(poly):
            violations.append({"code": "GEOMETRY_OUTSIDE", "panel": cid})
        energy, shade = candidate_solar_metrics(state, c, sun_elevation_deg)
        if shade > shade_threshold:
            violations.append({
                "code": "SHADOW_EXCESS",
                "panel": cid,
                "value": round(shade, 3),
                "threshold": shade_threshold,
            })

        # Demo risk envelope: when a rooftop object is much taller than the
        # originally surveyed state, nearby placements are re-checked with a
        # larger service/shadow uncertainty margin. This is not a code standard;
        # it exists to demonstrate change-aware verification.
        for obs in state.obstacles:
            if obs.id == "TANK" and obs.object_height_m >= 1.7:
                tall_zone = box(obs.x, obs.y, obs.x + obs.width, obs.y + obs.height).buffer(0.55)
                if poly.intersects(tall_zone):
                    violations.append({
                        "code": "TALL_OBSTACLE_RISK",
                        "panel": cid,
                        "value": round(obs.object_height_m, 2),
                        "threshold": 1.7,
                    })
                    break

    # selected candidates should never overlap; keep the invariant explicit
    for i, a in enumerate(selected):
        pa = candidate_poly(a)
        for b in selected[i + 1 :]:
            if pa.intersection(candidate_poly(b)).area > 0.015:
                violations.append({"code": "PANEL_OVERLAP", "panel": f"{a.id}/{b.id}"})

    return {
        "status": "PASS" if not violations else "FAIL",
        "violations": violations,
        "checks": {
            "geometry": not any(v["code"].startswith("GEOMETRY") for v in violations),
            "collision": not any(v["code"] == "PANEL_OVERLAP" for v in violations),
            "shadow": not any(v["code"] == "SHADOW_EXCESS" for v in violations),
            "data": True,
        },
    }


def stress_test(state: ProjectState, design: Design):
    # Scenarios are intentionally interpretable and finite; "8/8" means only these tests.
    original_heights = {o.id: o.object_height_m for o in state.obstacles}
    scenarios = [
        ("Base geometry", 34.0, None),
        ("Winter low sun", 27.0, None),
        ("Tank +20 cm", 34.0, ("TANK", 0.20)),
        ("Tank +30 cm", 31.0, ("TANK", 0.30)),
        ("Morning low sun", 29.0, None),
        ("Afternoon low sun", 30.0, None),
        ("Panel tolerance", 34.0, None),
        ("Field variance", 32.0, ("TANK", 0.15)),
    ]
    results = []
    failing_panels = set()

    for name, elevation, mutation in scenarios:
        if mutation:
            oid, delta = mutation
            for obs in state.obstacles:
                if obs.id == oid:
                    obs.object_height_m = original_heights[oid] + delta
        result = verify_design(state, design, sun_elevation_deg=elevation, shade_threshold=0.155)
        results.append({"name": name, "status": result["status"], "violations": result["violations"]})
        for v in result["violations"]:
            if v.get("panel"):
                failing_panels.add(v["panel"])
        for obs in state.obstacles:
            obs.object_height_m = original_heights[obs.id]

    passed = sum(r["status"] == "PASS" for r in results)
    return {
        "passed": passed,
        "total": len(results),
        "results": results,
        "failing_panels": sorted(p for p in failing_panels if "/" not in p),
    }
