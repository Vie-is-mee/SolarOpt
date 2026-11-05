"""Inputs as they arrive from the field: patchy satellite roofs, traced (slanted) outlines, large roofs."""
import random

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from app.schemas import ProjectConfig
from app.services.roof_extract import TraceRequest, data_url, extract_roof
from app.services.roof_templates import SHAPES, generate_faces


def patchy_roof(courtyard=False):
    """A 360 x 220 px roof in three sheet colours with a dark repair patch, on a grey street background.
    With courtyard=True the patch shows the ground instead, as an open courtyard does from above."""
    rng = np.random.default_rng(3)
    ground = np.clip(rng.normal(95, 12, (400, 600, 3)), 0, 255).astype(np.uint8)
    image = ground.copy()
    cv2.rectangle(image, (120, 90), (300, 310), (60, 70, 170), -1)      # red sheets
    cv2.rectangle(image, (300, 90), (480, 310), (150, 150, 140), -1)    # grey replaced sheets
    cv2.rectangle(image, (200, 150), (260, 200), (35, 35, 40), -1)      # dark patch, not a courtyard
    if courtyard:
        image[150:201, 200:261] = ground[150:201, 200:261]
    cv2.rectangle(image, (380, 240), (430, 290), (210, 210, 205), -1)   # bright skylight
    return data_url(image), Polygon([(120, 90), (480, 90), (480, 310), (120, 310)])


@pytest.mark.parametrize("mode", ["orthogonal", "rectangle"])
def test_patchy_roof_traces_to_one_clean_outline_without_fake_courtyards(mode):
    url, truth = patchy_roof()
    result = extract_roof(TraceRequest(image_data_url=url, rect=[17, 19, 66, 61], regularize=mode,
                                       foreground=[{"x": 35, "y": 50}, {"x": 65, "y": 50}]))
    traced = Polygon([(p["x"] * 6, p["y"] * 4) for p in result["polygon_image_pct"]])
    assert traced.intersection(truth).area / traced.union(truth).area > .93
    assert result["roof_openings_pct"] == []
    assert len(result["roof_polygon_pct"]) <= 8
    assert result["roof_width_px"] / result["roof_height_px"] == pytest.approx(360 / 220, rel=.05)


def test_courtyard_survives_when_engineer_marks_it_as_background():
    url, _ = patchy_roof(courtyard=True)
    result = extract_roof(TraceRequest(image_data_url=url, rect=[17, 19, 66, 61], regularize="orthogonal",
                                       foreground=[{"x": 30, "y": 40}], background=[{"x": 38, "y": 43}]))
    assert len(result["roof_openings_pct"]) == 1


def test_every_roof_shape_builds_on_traced_slanted_and_concave_outlines():
    """Rounding faces cut along slanted traced edges used to push them 1e-5 m outside the outline,
    so A-frame, hip and vault roofs all failed with 'Phần mái phải có diện tích…'."""
    rng = random.Random(1)
    for trial in range(40):
        W, D = round(rng.uniform(5, 250), 2), round(rng.uniform(5, 120), 2)
        j = lambda: rng.uniform(0, .1)
        if trial % 2:
            pts = [(j() * W, j() * D), (W - j() * W, 0), (W, D - j() * D), (j() * W, D)]
        else:
            pts = [(0, j() * D), (W * .6 + j(), 0), (W * .62, D * .4 + j()), (W, D * .41), (W - j() * W * .1, D), (j() * W * .1, D - j() * D * .05)]
        holes = [[{"x": W * .3, "y": D * .3}, {"x": W * .35, "y": D * .3}, {"x": W * .35, "y": D * .35}]] if trial % 3 == 0 else []
        cfg = ProjectConfig(roof_width_m=W, roof_height_m=D, roof_polygon=[{"x": round(x, 5), "y": round(y, 5)} for x, y in pts], roof_openings=holes)
        for shape in SHAPES:
            for axis in "xy":
                faces, _ = generate_faces(cfg, shape, axis, 2.0, "start", .05, 1.214)
                assert faces
                ProjectConfig(**{**cfg.model_dump(), "roof_faces": [f.model_dump() for f in faces]})


def test_factory_sized_roofs_are_accepted():
    cfg = ProjectConfig(roof_width_m=240, roof_height_m=60)
    assert cfg.roof_width_m == 240
    with pytest.raises(ValueError):
        ProjectConfig(roof_width_m=301, roof_height_m=60)
