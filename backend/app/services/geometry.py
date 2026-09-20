from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from app.schemas import ProjectConfig, RectObstacle, SunPosition


@dataclass
class GeometryContext:
    roof: Polygon
    usable_roof: Polygon
    obstacle_union: Polygon | None
    shadow_union: Polygon | None
    forbidden: Polygon | None


def obstacle_polygon(o: RectObstacle) -> Polygon:
    return box(o.x, o.y, o.x + o.width_m, o.y + o.depth_m)


def shadow_polygon(o: RectObstacle, sun: SunPosition | None) -> Polygon | None:
    if sun is None or sun.altitude_deg <= 1.0:
        return None
    base = obstacle_polygon(o)
    altitude = math.radians(max(sun.altitude_deg, 1.0))
    length = max(0.0, o.height_m / math.tan(altitude))
    az = math.radians(sun.azimuth_deg)
    # Bóng đổ ngược hướng mặt trời. Trục x hướng Đông, y hướng Bắc.
    dx = -math.sin(az) * length
    dy = -math.cos(az) * length
    shifted = translate(base, xoff=dx, yoff=dy)
    return unary_union([base, shifted]).convex_hull


def build_context(config: ProjectConfig, obstacles: list[RectObstacle], sun: SunPosition | None) -> GeometryContext:
    roof = box(0, 0, config.roof_width_m, config.roof_height_m)
    usable = roof.buffer(-config.setback_m, join_style=2)
    if usable.is_empty:
        usable = roof

    obstacle_shapes = []
    shadow_shapes = []
    for o in obstacles:
        obstacle_shapes.append(obstacle_polygon(o).buffer(config.obstacle_clearance_m, join_style=2))
        sh = shadow_polygon(o, sun)
        if sh is not None:
            shadow_shapes.append(sh)

    obstacle_union = unary_union(obstacle_shapes) if obstacle_shapes else None
    shadow_union = unary_union(shadow_shapes) if shadow_shapes else None
    pieces = [g for g in [obstacle_union, shadow_union] if g is not None and not g.is_empty]
    forbidden = unary_union(pieces) if pieces else None
    return GeometryContext(roof=roof, usable_roof=usable, obstacle_union=obstacle_union, shadow_union=shadow_union, forbidden=forbidden)


def panel_shape(x: float, y: float, width: float, height: float) -> Polygon:
    return box(x, y, x + width, y + height)


def overlap_ratio(shape: Polygon, other: Polygon | None) -> float:
    if other is None or other.is_empty or shape.area <= 0:
        return 0.0
    return max(0.0, min(1.0, shape.intersection(other).area / shape.area))
