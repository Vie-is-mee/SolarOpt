"""Turn a roof type and a few measurements into planar faces the engine already understands.

Every roof is represented as planar facets: flat = 1, shed = 1, gable (A) = 2, hip = 4, and curved
roofs (barrel vault, parabolic) as strips whose chord stays within a tolerance of the true curve, or
as many strips as the engineer asks for (one per panel row on a segmented vault). Shading, irradiance
and packing then work per face without special cases. Curved strips share a group so the edge setback
applies only around the whole vault, not at every internal seam.

A roof can be built in parts: a smaller roof stacked on a region of the main one (a raised gable over
a stairwell, a second tier, a cross gable) replaces the faces below it in plan and keeps their planes
elsewhere; it stands higher, so it shades the faces around it.
"""
from __future__ import annotations
import math
from shapely.affinity import translate
from shapely.geometry import Point, Polygon, box
from app.schemas import ProjectConfig, RoofFace
from app.services.geometry import roof_polygon, surface_z, surfaces, _parts

SHAPES = ("flat", "shed", "gable", "hip", "barrel", "parabolic")
MAX_TILT = 60.0
MAX_STRIPS = 20


def _clean_ring(part):
    """Outer ring of a face, rounded to 0,1 mm, at most 80 vertices and still a valid polygon.
    Rounding a sliver can make it cross itself; such a ring is repaired or dropped instead of failing the roof."""
    shape = Polygon(part.exterior)
    for tolerance in (0, .002, .01, .03):
        simple = shape.simplify(tolerance, preserve_topology=True) if tolerance else shape
        coords = list(simple.exterior.coords)[:-1]
        if len(coords) > 80:
            continue
        ring = [(round(x, 4), round(y, 4)) for x, y in coords]
        ring = [p for i, p in enumerate(ring) if p != ring[i - 1]]
        if len(ring) >= 3:
            candidate = Polygon(ring)
            if candidate.is_valid and candidate.area >= .05:
                return ring
    return None


def _profile(shape, span, rise):
    if shape == "parabolic":
        return lambda u: 4 * rise * u * (span - u) / span ** 2
    radius = (span ** 2 / 4 + rise ** 2) / (2 * rise)
    return lambda u: math.sqrt(max(0.0, radius ** 2 - (u - span / 2) ** 2)) - (radius - rise)


def _strips(shape, span, rise, tolerance, pitch, setback, count=None):
    """Plan boundaries across the span. Interior seams sit at setback + k*pitch so panel rows that
    start at the outer setback end exactly on a seam; strips are as wide as the tolerance allows.
    With a count, the usable width inside the setbacks is split into that many equal strips."""
    z = _profile(shape, span, rise)
    if count:
        inner = span - 2 * setback if span > 2 * setback + 1e-6 else span
        lead = setback if inner < span else 0.0
        width = inner / count
        return [0.0] + [lead + i * width for i in range(1, count)] + [span], z
    def deviation(a, b):
        za, zb = z(a), z(b)
        return max(z(a + (b - a) * t / 20) - (za + (zb - za) * t / 20) for t in range(21))
    unit = pitch if pitch and pitch > 0 else span / 40
    for k in range(max(1, int(span // unit)), 0, -1):
        width = k * unit
        cuts = [0.0] + [setback + i * width for i in range(1, 400) if setback + i * width < span - 1e-6] + [span]
        if len(cuts) - 1 <= 20 and max(deviation(a, b) for a, b in zip(cuts, cuts[1:])) <= tolerance:
            return cuts, z
    # Tolerance unreachable (tight curve): keep one panel row per strip so rows still align with
    # seams; the caller reports the actual deviation instead of hiding it.
    cuts = [0.0] + [setback + i * unit for i in range(1, 400) if setback + i * unit < span - 1e-6] + [span]
    return cuts, z


def generate_faces(config: ProjectConfig, shape: str, ridge_axis: str = "x", rise_m: float = 2.0,
                   low_side: str = "start", tolerance_m: float = .05, panel_pitch_m: float | None = None,
                   strips: int | None = None, region: tuple[float, float, float, float] | None = None,
                   eave_m: float | None = None, prefix: str = "", label_prefix: str = ""):
    """Faces of one roof over the whole frame, or over region = (x0, y0, x1, y1) of the drawing with its
    eave at eave_m (a roof part stacked on the main roof)."""
    if shape not in SHAPES:
        raise ValueError("Dạng mái không hỗ trợ.")
    if strips is not None and not 2 <= strips <= MAX_STRIPS:
        raise ValueError(f"Số dải vòm phải từ 2 đến {MAX_STRIPS}.")
    x0, y0, x1, y1 = region or (0.0, 0.0, config.roof_width_m, config.roof_height_m)
    if x1 - x0 < .5 or y1 - y0 < .5:
        raise ValueError("Vùng mái phụ cần rộng và sâu ít nhất 0,5 m.")
    W, D = x1 - x0, y1 - y0
    eave = config.roof_elevation_m if eave_m is None else eave_m
    along_x = ridge_axis == "x"            # ridge parallel to x: slopes run across y
    span = D if along_x else W
    rot = config.north_rotation_deg
    notes = []
    if shape != "flat" and rise_m <= 0:
        raise ValueError("Độ cao đỉnh so với diềm phải lớn hơn 0.")

    def rect(a, b):                         # strip a..b across the span, full length along the ridge
        return box(0, a, W, b) if along_x else box(a, 0, b, D)

    def bearing(sign):                      # compass direction of +u (sign=1) or -u (sign=-1)
        return (rot + (0 if along_x else 90) + (0 if sign > 0 else 180)) % 360

    planes = []                             # (polygon, z(x,y), tilt, azimuth, label, group)
    u_of = (lambda x, y: y) if along_x else (lambda x, y: x)
    if shape == "flat":
        planes.append((box(0, 0, W, D), lambda x, y: eave, 0.0, 180.0, "Mái bằng", None))
    elif shape == "shed":
        tilt = math.degrees(math.atan2(rise_m, span))
        high = span if low_side == "start" else 0.0
        z = lambda x, y: eave + rise_m * (1 - abs(u_of(x, y) - high) / span)
        planes.append((box(0, 0, W, D), z, tilt, bearing(-1 if low_side == "start" else 1), "Mái một dốc", None))
    elif shape in ("gable", "hip"):
        half = span / 2
        tilt = math.degrees(math.atan2(rise_m, half))
        slope = rise_m / half
        if shape == "gable":
            for a, b, sign, name in ((0, half, -1, "Mái dốc 1"), (half, span, 1, "Mái dốc 2")):
                edge = 0 if sign < 0 else span
                planes.append((rect(a, b), lambda x, y, e=edge: eave + slope * abs(u_of(x, y) - e), tilt, bearing(sign), name, None))
        else:
            L = W if along_x else D             # length along the ridge
            r0, r1 = (half, L - half) if L > span else (L / 2, L / 2)
            def P(along, across):               # (along ridge, across span) -> plan (x, y)
                return (along, across) if along_x else (across, along)
            faces = [
                ([P(0, 0), P(L, 0), P(r1, half), P(r0, half)], lambda x, y: eave + slope * u_of(x, y), bearing(-1), "Mái dốc trước"),
                ([P(0, span), P(r0, half), P(r1, half), P(L, span)], lambda x, y: eave + slope * (span - u_of(x, y)), bearing(1), "Mái dốc sau"),
                ([P(0, 0), P(r0, half), P(0, span)], lambda x, y: eave + slope * (x if along_x else y), (rot + (270 if along_x else 180)) % 360, "Mái đầu hồi 1"),
                ([P(L, 0), P(L, span), P(r1, half)], lambda x, y: eave + slope * (L - (x if along_x else y)), (rot + (90 if along_x else 0)) % 360, "Mái đầu hồi 2"),
            ]
            for pts, z, az, name in faces:
                planes.append((Polygon(pts), z, tilt, az, name, None))
    else:
        cuts, profile = _strips(shape, span, rise_m, tolerance_m, panel_pitch_m, config.setback_m, strips)
        worst = 0.0
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            za, zb = profile(a), profile(b)
            tilt = math.degrees(math.atan2(abs(zb - za), b - a))
            worst = max(worst, max(profile(a + (b - a) * t / 20) - (za + (zb - za) * t / 20) for t in range(21)))
            z = lambda x, y, a=a, b=b, za=za, zb=zb: eave + za + (zb - za) * (u_of(x, y) - a) / (b - a)
            az = bearing(1 if zb < za else -1) if abs(zb - za) > 1e-9 else 180.0
            planes.append((rect(a, b), z, tilt, az, f"Dải vòm {i + 1}", prefix + "vault"))
        how = "theo số dải kỹ sư chọn" if strips else "tự động theo hàng tấm và dung sai"
        notes.append(f"Chia {len(cuts) - 1} dải phẳng ({how}); lệch lớn nhất so với đường cong {f'{worst * 100:.1f}'.replace('.', ',')} cm" + (f" (vượt dung sai {tolerance_m * 100:.0f} cm: cần ray uốn, tăng số dải hoặc dùng tấm dẻo)." if worst > tolerance_m + 1e-9 else "."))

    # Faces follow the outer outline; courtyards are cut later from the roof itself, so a face never needs holes.
    outline = Polygon(roof_polygon(config).exterior) if roof_polygon(config).geom_type == "Polygon" else roof_polygon(config)
    faces = []
    for index, (local, z, tilt, az, label, group) in enumerate(planes):
        poly = translate(local, x0, y0)
        for part_index, part in enumerate(_parts(poly.intersection(outline))):
            if part.area < .05:
                continue
            ring = _clean_ring(part)
            if ring is None:
                continue
            c = part.centroid
            installable = tilt <= MAX_TILT
            faces.append(RoofFace(id=f"{prefix}{shape}-{index}" + (f"-{part_index}" if part_index else ""), label=label_prefix + label,
                                  polygon=[{"x": x, "y": y} for x, y in ring],
                                  elevation_m=round(min(300, z(c.x - x0, c.y - y0)), 4), tilt_deg=round(min(MAX_TILT, tilt), 3),
                                  azimuth_deg=round(az % 360, 3), installable=installable, group=group))
    if any(not f.installable for f in faces):
        notes.append(f"Phần dốc hơn {MAX_TILT:.0f}° được đánh dấu không lắp pin.")
    if len(faces) > 24:
        raise ValueError("Quá nhiều mặt mái; tăng dung sai hoặc giảm kích thước.")
    if region is None and not roof_polygon(config).equals(box(0, 0, W, D)):
        notes.append("Biên mái không phải hình chữ nhật: mặt mái được cắt theo biên; kiểm tra lại hướng nóc và cao độ.")
    if any(f.tilt_deg > 1 for f in faces):
        notes.append("Trên mặt dốc, tấm, khe và khoảng lùi được tính theo chiều dài thật trên mái (mặt bằng co theo cos độ dốc); tọa độ định vị có cột đo theo dốc.")
    return faces, notes


def height_below(config: ProjectConfig, region: tuple[float, float, float, float]) -> float:
    """Highest point of the existing roof under a region (corners and centre): a stacked roof starts there."""
    x0, y0, x1, y1 = region
    points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, (y0 + y1) / 2)]
    planes = surfaces(config)
    heights = []
    for x, y in points:
        p = Point(x, y)
        for s in planes:
            if s.polygon.buffer(1e-6).covers(p):
                heights.append(surface_z(s, x, y, config))
    return round(max(heights), 3) if heights else config.roof_elevation_m


def stacked_prefix(config: ProjectConfig) -> int:
    used = {f.id.split("-", 1)[0] for f in config.roof_faces if f.id.startswith("sub")}
    n = 1
    while f"sub{n}" in used:
        n += 1
    return n


def _hole_free(part):
    """A face is one ring: a piece with a hole (a stacked roof inside it) is split through the hole."""
    if not part.interiors:
        return [part]
    cx = Polygon(part.interiors[0]).centroid.x
    minx, miny, maxx, maxy = part.bounds
    out = []
    for half in (box(minx - 1, miny - 1, cx, maxy + 1), box(cx, miny - 1, maxx + 1, maxy + 1)):
        for piece in _parts(part.intersection(half)):
            out += _hole_free(piece)
    return out


def stack_faces(config: ProjectConfig, new_faces: list[RoofFace], region: tuple[float, float, float, float]) -> list[RoofFace]:
    """Existing roof (faces, or the plain roof when there are none) minus the region in plan, each piece
    on its own plane, plus the new faces. Nothing overlaps in plan, so every check works unchanged."""
    cut = box(*region)
    kept: list[RoofFace] = []
    for s in surfaces(config):
        for k, part in enumerate(p for piece in _parts(s.polygon.difference(cut)) for p in _hole_free(piece)):
            if part.area < .05:
                continue
            ring = _clean_ring(part)
            if ring is None:
                continue
            c = Polygon(ring).centroid
            base = "main" if s.id == "base" else s.id
            kept.append(RoofFace(id=base if k == 0 else f"{base}-p{k}", label="Mái chính" if s.id == "base" else s.label,
                                 polygon=[{"x": x, "y": y} for x, y in ring], elevation_m=round(min(300, surface_z(s, c.x, c.y, config)), 4),
                                 tilt_deg=round(s.tilt, 3), azimuth_deg=round(s.azimuth % 360, 3), installable=s.installable, group=s.group))
    faces = kept + new_faces
    if len(faces) > 24:
        raise ValueError(f"Mái ghép có {len(faces)} mặt, vượt 24 mặt; giảm số dải vòm hoặc gộp bớt mái phụ.")
    return faces
