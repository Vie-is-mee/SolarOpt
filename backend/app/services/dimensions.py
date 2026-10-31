"""Turn dimension labels read from a drawing into metres and check that they agree on one scale.

The vision model only reads text and marks the two ends of each dimension line. Units, axis and
scale consistency are decided here, deterministically, so a misread number shows up as a scale
outlier instead of silently becoming a roof size. Results are suggestions for the engineer.
"""
from __future__ import annotations
import math
import re
from statistics import median

SCALE_TOLERANCE = .05   # labels whose m/px differ from the median by more than this are outliers
COVER_RATIO = .85       # a label spanning >= this share of the roof bbox is taken as the overall size
UNIT_FACTOR = {"mm": .001, "cm": .01, "m": 1.0}


def parse_length(text: str, value: float | None = None, unit: str | None = None) -> tuple[float | None, str]:
    """Return (metres, how) for a label. Explicit units in the text win over the model's guess."""
    raw = (text or "").strip().lower().replace(" ", " ")
    match = re.search(r"(\d[\d.,\s]*)\s*(mm|cm|m)?\b", raw)
    number, text_unit = None, None
    if match:
        digits, text_unit = match.group(1).strip().replace(" ", ""), match.group(2)
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", digits):
            number = float(re.sub(r"[.,]", "", digits))   # 12.000 / 12,000 = thousands separators
        else:
            try:
                number = float(digits.replace(",", "."))
            except ValueError:
                number = None
    if number is None and value is not None and value > 0:
        number = float(value)
    if number is None or number <= 0:
        return None, "Không đọc được số"
    chosen = text_unit or (unit if unit in UNIT_FACTOR else None)
    if chosen:
        return number * UNIT_FACTOR[chosen], f"đơn vị {chosen}"
    # Vietnamese architectural drawings are usually dimensioned in mm without a unit.
    if number >= 200:
        return number / 1000, "không ghi đơn vị, hiểu là mm"
    if number <= 30:
        return number, "không ghi đơn vị, hiểu là m"
    return None, "Không rõ đơn vị (cm hay mm?)"


def _axis(dx: float, dy: float) -> str:
    if abs(dx) >= 3 * abs(dy):
        return "horizontal"
    if abs(dy) >= 3 * abs(dx):
        return "vertical"
    return "other"


def analyze_dimensions(labels: list[dict], image_w: int, image_h: int, roof_bbox_pct: list[float] | None):
    """labels: [{text, value?, unit?, start:{x,y}, end:{x,y}}] in % of the main image.
    roof_bbox_pct: [x, y, w, h] in % of the image, or None when no roof outline is known."""
    readings = []
    for item in labels[:20]:
        start, end = item.get("start") or {}, item.get("end") or {}
        try:
            x1, y1, x2, y2 = (float(start["x"]), float(start["y"]), float(end["x"]), float(end["y"]))
        except (KeyError, TypeError, ValueError):
            x1 = y1 = x2 = y2 = None
        metres, how = parse_length(str(item.get("text", "")), item.get("value"), item.get("unit"))
        reading = {"text": str(item.get("text", ""))[:40], "value_m": round(metres, 4) if metres else None, "interpretation": how,
                   "axis": "other", "length_px": None, "m_per_px": None, "outlier": False}
        if None not in (x1, y1, x2, y2) and all(0 <= v <= 100 for v in (x1, y1, x2, y2)):
            dx, dy = (x2 - x1) / 100 * image_w, (y2 - y1) / 100 * image_h
            length = math.hypot(dx, dy)
            reading.update(axis=_axis(dx, dy), start={"x": x1, "y": y1}, end={"x": x2, "y": y2})
            if length >= 8:
                reading["length_px"] = round(length, 1)
                if metres:
                    reading["m_per_px"] = metres / length
        readings.append(reading)

    scales = [r["m_per_px"] for r in readings if r["m_per_px"]]
    scale = median(scales) if scales else None
    if scale:
        for r in readings:
            if r["m_per_px"]:
                r["outlier"] = abs(r["m_per_px"] / scale - 1) > SCALE_TOLERANCE
    spread = (max(abs(s / scale - 1) for s in scales) * 100) if scale and len(scales) > 1 else None
    consistent = None if len(scales) < 2 else not any(r["outlier"] for r in readings)

    width = height = None
    width_basis = height_basis = ""
    if roof_bbox_pct and scale:
        bw_px, bh_px = roof_bbox_pct[2] / 100 * image_w, roof_bbox_pct[3] / 100 * image_h
        for axis, span in (("horizontal", bw_px), ("vertical", bh_px)):
            covering = [r for r in readings if r["axis"] == axis and r["value_m"] and r["length_px"] and not r["outlier"]
                        and r["length_px"] >= COVER_RATIO * span]
            if covering:
                best = max(covering, key=lambda r: r["length_px"])
                value, basis = best["value_m"], f"số đo tổng '{best['text']}'"
            elif consistent is not False:
                value, basis = span * scale, "biên mái × tỉ lệ chung của các số đo"
            else:
                continue
            if axis == "horizontal":
                width, width_basis = round(value, 2), basis
            else:
                height, height_basis = round(value, 2), basis

    for r in readings:
        if r["m_per_px"] is not None:
            r["m_per_px"] = round(r["m_per_px"], 6)
    notes = []
    if consistent is False:
        notes.append(f"Các số đo lệch tỉ lệ tới {spread:.0f}%: có thể đọc sai số, sai đơn vị hoặc bản vẽ không theo tỉ lệ. Kiểm tra từng số trước khi dùng.")
    elif len(scales) == 1:
        notes.append("Chỉ có một số đo kèm đường kích thước nên chưa kiểm tra chéo được tỉ lệ.")
    return {"labels": readings, "scale_m_per_px": round(scale, 6) if scale else None,
            "scale_spread_pct": round(spread, 1) if spread is not None else None, "consistent": consistent,
            "suggested_width_m": width, "suggested_height_m": height,
            "width_basis": width_basis, "height_basis": height_basis, "notes": notes}
