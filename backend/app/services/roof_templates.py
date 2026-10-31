"""Turn a roof type and a few measurements into planar faces the engine already understands.

Every roof is represented as planar facets: flat = 1, shed = 1, gable (A) = 2, hip = 4, and curved
roofs (barrel vault, parabolic) as strips whose chord stays within a tolerance of the true curve.
Shading, irradiance and packing then work per face without special cases. Curved strips share a
group so the edge setback applies only around the whole vault, not at every internal seam.
"""
from __future__ import annotations
import math
from shapely.geometry import Polygon, box
from app.schemas import ProjectConfig, RoofFace
from app.services.geometry import roof_polygon, _parts

SHAPES = ("flat", "shed", "gable", "hip", "barrel", "parabolic")
MAX_TILT = 60.0


def _profile(shape, span, rise):
    if shape == "parabolic":
        return lambda u: 4 * rise * u * (span - u) / span ** 2
    radius = (span ** 2 / 4 + rise ** 2) / (2 * rise)
    return lambda u: math.sqrt(max(0.0, radius ** 2 - (u - span / 2) ** 2)) - (radius - rise)


def _strips(shape, span, rise, tolerance, pitch, setback):
    """Plan boundaries across the span. Interior seams sit at setback + k*pitch so panel rows that
    start at the outer setback end exactly on a seam; strips are as wide as the tolerance allows."""
    z = _profile(shape, span, rise)
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
                   low_side: str = "start", tolerance_m: float = .05, panel_pitch_m: float | None = None):
    if shape not in SHAPES:
        raise ValueError("Dạng mái không hỗ trợ.")
    W, D = config.roof_width_m, config.roof_height_m
    eave = config.roof_elevation_m
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
        cuts, profile = _strips(shape, span, rise_m, tolerance_m, panel_pitch_m, config.setback_m)
        worst = 0.0
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            za, zb = profile(a), profile(b)
            tilt = math.degrees(math.atan2(abs(zb - za), b - a))
            worst = max(worst, max(profile(a + (b - a) * t / 20) - (za + (zb - za) * t / 20) for t in range(21)))
            z = lambda x, y, a=a, b=b, za=za, zb=zb: eave + za + (zb - za) * (u_of(x, y) - a) / (b - a)
            az = bearing(1 if zb < za else -1) if abs(zb - za) > 1e-9 else 180.0
            planes.append((rect(a, b), z, tilt, az, f"Dải vòm {i + 1}", "vault"))
        notes.append(f"Chia {len(cuts) - 1} dải phẳng; lệch lớn nhất so với đường cong {worst * 100:.1f} cm" + (f" (vượt dung sai {tolerance_m * 100:.0f} cm: cần ray uốn hoặc tấm dẻo)." if worst > tolerance_m + 1e-9 else "."))

    outline = roof_polygon(config)
    faces = []
    for index, (poly, z, tilt, az, label, group) in enumerate(planes):
        for part_index, part in enumerate(_parts(poly.intersection(outline))):
            if part.area < .05:
                continue
            c = part.centroid
            installable = tilt <= MAX_TILT
            faces.append(RoofFace(id=f"{shape}-{index}" + (f"-{part_index}" if part_index else ""), label=label,
                                  polygon=[{"x": round(x, 4), "y": round(y, 4)} for x, y in list(part.exterior.coords)[:-1]][:80],
                                  elevation_m=round(min(300, z(c.x, c.y)), 4), tilt_deg=round(min(MAX_TILT, tilt), 3),
                                  azimuth_deg=round(az % 360, 3), installable=installable, group=group))
    if any(not f.installable for f in faces):
        notes.append(f"Phần dốc hơn {MAX_TILT:.0f}° được đánh dấu không lắp pin.")
    if len(faces) > 24:
        raise ValueError("Quá nhiều mặt mái; tăng dung sai hoặc giảm kích thước.")
    if not roof_polygon(config).equals(box(0, 0, W, D)):
        notes.append("Biên mái không phải hình chữ nhật: mặt mái được cắt theo biên; kiểm tra lại hướng nóc và cao độ.")
    notes.append("Kích thước tấm trên mặt dốc vẫn tính theo mặt bằng (chưa co theo độ dốc) nên số tấm có thể thấp hơn thực tế.")
    return faces, notes
