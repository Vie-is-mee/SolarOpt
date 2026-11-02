import dataclasses

import numpy as np
import pytest

from app.schemas import ProjectConfig, RectObstacle
from app.services.energy import EnergyContext
from app.services.geometry import build_context, panel_shape, panel_shapes

W, H = 1.134, 2.278   # portrait module: three substrings side by side across its 1.134 m width


def clear_roof_context():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9)
    context = EnergyContext(cfg, [], build_context(cfg, [], None))
    # Private copy of the (cached) all-clear raster, so painting shade here never leaks into other tests.
    context.series = dataclasses.replace(context.series, mask=context.series.mask.copy())
    return context


def paint(context, minx, miny, maxx, maxy, instants=slice(None)):
    s = context.series
    rows, cols, _ = s.mask.shape
    xs = s.x0 + (np.arange(cols) + .5) * s.cell
    ys = s.y0 + (np.arange(rows) + .5) * s.cell
    inside = (ys[:, None] > miny) & (ys[:, None] < maxy) & (xs[None, :] > minx) & (xs[None, :] < maxx)
    cells = s.mask[inside]
    cells[:, instants] = True
    s.mask[inside] = cells


def beam_share(context, shape):
    surface = next(s for s, region in context.surface_regions if region.covers(shape))
    _, direct, total = context._components(surface)
    return direct / total


def test_thin_shade_across_all_substrings_costs_more_than_its_area():
    context = clear_roof_context()
    shape = panel_shape(1, 1, W, H)
    paint(context, 0, 0, 3, 1 + H / 6)            # bottom sixth of the module, every hour
    value = context.evaluate(shape, 580)
    share = beam_share(context, shape)
    assert value.mean_cover == pytest.approx(1 / 6)
    # Each substring is a sixth shaded -> loses half its beam power (3 x 1/6), not a sixth.
    assert value.loss_pct == pytest.approx(100 * share * .5, abs=.01)


def test_shade_on_one_substring_costs_a_third():
    context = clear_roof_context()
    shape = panel_shape(1, 1, W, H)
    paint(context, 0, 0, 1 + W / 3, 9)            # the whole left substring, every hour
    value = context.evaluate(shape, 580)
    share = beam_share(context, shape)
    assert value.mean_cover == pytest.approx(1 / 3)
    assert value.loss_pct == pytest.approx(100 * share / 3, abs=.01)


def test_morning_shade_costs_less_than_noon_shade():
    hours = clear_roof_context().series.index % 24
    shape = panel_shape(1, 1, W, H)
    morning, noon = clear_roof_context(), clear_roof_context()
    paint(morning, 0, 0, 3, 4, hours == 6)
    paint(noon, 0, 0, 3, 4, hours == 11)
    assert 0 < morning.evaluate(shape, 580).loss_pct < noon.evaluate(shape, 580).loss_pct


def test_one_panel_and_a_whole_grid_give_identical_figures():
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9)
    obstacles = [RectObstacle(id='tank', x=6, y=4, width_m=1.5, depth_m=1.5, height_m=2.5)]
    context = EnergyContext(cfg, obstacles, build_context(cfg, obstacles, None))
    xs, ys = [1, 3.5, 6.1, 8.3], [.5, 2.1, 5.9, 6.4]
    shapes = panel_shapes(xs, ys, W, H, 17.5)
    surface = context.geometry.surfaces[0]
    many = context.evaluate_many(shapes, 580, [surface] * len(xs))
    for shape, value in zip(shapes, many):
        assert context.evaluate(shape, 580, surface) == value
    assert any(v.loss_pct > 0 for v in many)
