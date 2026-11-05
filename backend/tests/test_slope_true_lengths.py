"""On a sloped face, setbacks and gaps are lengths on the roof surface, as installers measure them."""
import math

import pytest
from shapely.geometry import box

from app.schemas import DesignRequest, PanelSpec, ProjectConfig, VerifyRequest
from app.services.geometry import build_context, panel_shape, surfaces, unfold
from app.services.optimizer import generate_design
from app.services.roof_templates import generate_faces
from app.services.verifier import verify_design

PANEL = PanelSpec()


def _gable(rise, rot=0.0):
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, budget_vnd=1e9, north_rotation_deg=rot)
    faces, _ = generate_faces(cfg, "gable", "x", rise)
    return ProjectConfig(**{**cfg.model_dump(), "roof_faces": [f.model_dump() for f in faces]})


def test_unfold_and_fold_are_inverse_and_stretch_only_the_fall_line():
    cfg = _gable(3, rot=30)
    s = surfaces(cfg)[0]
    c = math.cos(math.radians(s.tilt))
    shape = box(1, 1, 3, 2)
    assert unfold(unfold(shape, s, cfg), s, cfg, fold=True).symmetric_difference(shape).area < 1e-9
    assert unfold(shape, s, cfg).area == pytest.approx(shape.area / c)


@pytest.mark.parametrize("rise", [2.0, 3.5])
def test_setback_and_gaps_are_measured_on_the_roof(rise):
    cfg = _gable(rise)
    design = generate_design(DesignRequest(config=cfg, panel=PANEL, objective="max_energy"))
    planes = {s.id: s for s in surfaces(cfg)}
    bounds = {p.id: panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg).bounds for p in design.panels}
    for p in design.panels:
        s = planes[p.face_id]
        c = math.cos(math.radians(s.tilt))
        _, y0, _, y1 = bounds[p.id]
        # Face 0 slopes down to y = 0 (its eave), face 1 down to y = 9: distance up the roof from the eave.
        plan = y0 if s.azimuth == 180 else 9 - y1
        assert plan / c >= cfg.setback_m - 1e-6
    # Rows on one face: the gap on the roof is at least the configured gap and not more than needed.
    for face in planes:
        rows = sorted({(round(bounds[p.id][1], 4), round(bounds[p.id][3], 4)) for p in design.panels if p.face_id == face})
        c = math.cos(math.radians(planes[face].tilt))
        for (a0, a1), (b0, b1) in zip(rows, rows[1:]):
            true_gap = (b0 - a1) / c
            assert cfg.panel_gap_m - 2e-4 <= true_gap <= cfg.panel_gap_m + .02   # bounds rounded to 0,1 mm above
    assert verify_design(VerifyRequest(config=cfg, panel=PANEL, design=design)).valid


def test_steep_roof_fits_more_rows_than_plan_measures_would():
    """At 38° the plan setback and gaps shrink by cos: the first row starts lower on the drawing."""
    cfg = _gable(3.5)
    ctx = build_context(cfg, [], None)
    first = surfaces(cfg)[0]
    lowest = min(y for poly in getattr(ctx.usable_roof, "geoms", [ctx.usable_roof]) for _, y in poly.exterior.coords)
    assert lowest == pytest.approx(cfg.setback_m * math.cos(math.radians(first.tilt)), abs=1e-6)


def test_verifier_flags_a_gap_short_on_the_roof_even_if_plan_looks_fine():
    cfg = _gable(3.5)
    design = generate_design(DesignRequest(config=cfg, panel=PANEL, objective="max_energy"))
    face = design.panels[0].face_id
    same = sorted([p for p in design.panels if p.face_id == face], key=lambda p: (p.y, p.x))
    a = same[0]
    assert a.rotation_deg % 180 == 0, "steep face: portrait rows along the contour"
    b = next(p for p in same if p.y > a.y + 1e-6 and abs(p.x - a.x) < 1e-6)
    c = math.cos(math.radians(next(s for s in surfaces(cfg) if s.id == face).tilt))
    # A plan gap of 0,08·cos is exactly 0,08 on the roof: allowed although it looks short in plan;
    # a plan gap of 0,06 is 0,076 on the roof: too tight.
    ok_y, tight_y = a.y + a.height_m + .08 * c + 1e-4, a.y + a.height_m + .06
    for y, valid in ((ok_y, True), (tight_y, False)):
        moved = design.model_copy(update={"panels": [p.model_copy(update={"y": y}) if p.id == b.id else p for p in design.panels]})
        gap = {c.id: c.status for c in verify_design(VerifyRequest(config=cfg, panel=PANEL, design=moved)).checks}["panel_gap"]
        assert (gap == "PASS") == valid, (y, gap)


@pytest.mark.parametrize("width,depth,rise,least", [(12, 8.21, 2, 14), (12, 9, 2, 14), (14, 10, 2.5, 22)])
def test_hip_ends_get_panels(width, depth, rise, least):
    """Triangular hip ends fit rows only when the face grid is anchored near the eave: the search tries
    offsets across the spare length, not just flush or centred."""
    cfg = ProjectConfig(roof_width_m=width, roof_height_m=depth, budget_vnd=1e9)
    faces, _ = generate_faces(cfg, "hip", "x", rise)
    cfg = ProjectConfig(**{**cfg.model_dump(), "roof_faces": [f.model_dump() for f in faces]})
    design = generate_design(DesignRequest(config=cfg, panel=PANEL, objective="max_energy"))
    on = {p.face_id for p in design.panels}
    assert len(design.panels) >= least and {"hip-2", "hip-3"} <= on
    assert verify_design(VerifyRequest(config=cfg, panel=PANEL, design=design)).valid
