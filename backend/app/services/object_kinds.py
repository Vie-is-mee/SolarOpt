"""Roof-object vocabulary the vision step may answer in, and the clean-up of what a model sends back.

The kinds are the object library of the Studio (frontend/src/assets.ts). A model answers with one of them or
"other"; when it answers vaguely or an older recording has no kind, the label decides. An unknown object stays
"other": a plain block with its own label is honest, a wrong library model is not.
"""
from __future__ import annotations
import re
import unicodedata

ROOF_KINDS = {
    "tank": "bồn nước đứng, trụ tròn nhìn từ trên xuống",
    "tank_flat": "bồn nước nằm ngang trên chân đế",
    "stair": "tum thang, lồng cầu thang có mái riêng",
    "hatch": "cửa sập lên mái",
    "skylight": "giếng trời, mái kính, tấm lấy sáng",
    "ac": "dàn nóng máy lạnh, thường xếp thành hàng",
    "chimney": "ống khói, ống thông hơi",
    "vent_turbine": "quả cầu thông gió trên mái tôn",
    "solar_heater": "máy nước nóng mặt trời, dàn ống và bình chứa",
    "dish": "chảo vệ tinh, cột ăng-ten",
    "lightning": "kim thu sét",
    "cooling": "tháp giải nhiệt",
    "sign": "biển quảng cáo trên mái",
    "drying": "giàn phơi đồ",
    "parapet": "tường chắn mái, lan can dài",
}
AROUND_KINDS = {
    "tree_round": "cây tán tròn",
    "tree_cone": "cây dáng nón",
    "tree_palm": "cây cau, cây dừa",
    "pole": "cột điện",
    "wall": "vách nhà liền kề cao hơn mái",
    "tower": "nhà cao tầng",
    "house": "nhà bên cạnh",
}
KINDS = {**ROOF_KINDS, **AROUND_KINDS}

_WORDS = [
    ("tank_flat", ("bon nam", "bon ngang", "horizontal tank")),
    ("tank", ("bon nuoc", "bon inox", "bon chua", "water tank", "tank", "bon")),
    ("stair", ("tum thang", "cau thang", "long thang", "stair")),
    ("hatch", ("cua sap", "hatch")),
    ("skylight", ("gieng troi", "mai kinh", "lay sang", "skylight")),
    ("ac", ("dan nong", "cuc nong", "may lanh", "dieu hoa", "air condition", "condenser")),
    ("vent_turbine", ("qua cau", "thong gio mai", "turbine")),
    ("chimney", ("ong khoi", "thong hoi", "thong gio", "ong thong", "chimney", "vent")),
    ("solar_heater", ("nuoc nong", "solar heater", "water heater")),
    ("dish", ("chao", "ang-ten", "ang ten", "antenna", "dish")),
    ("lightning", ("thu set", "chong set", "lightning")),
    ("cooling", ("giai nhiet", "cooling")),
    ("sign", ("bien quang cao", "bien hieu", "sign", "billboard")),
    ("drying", ("gian phoi", "san phoi", "phoi do", "drying")),
    ("parapet", ("lan can", "tuong chan", "parapet")),
    ("tree_palm", ("cay cau", "cay dua", "palm")),
    ("tree_cone", ("cay thong", "pine", "conifer")),
    ("tree_round", ("cay", "tree")),
    ("pole", ("cot dien", "pole")),
    ("wall", ("tuong nha ben", "vach nha", "tuong cao")),
    ("tower", ("nha cao tang", "chung cu", "toa nha", "tower")),
    ("house", ("nha ben", "nha lien ke", "nha hang xom", "house")),
]


def plain(text: str) -> str:
    """Lower-case without Vietnamese marks, so 'Bồn nước' and 'bon nuoc' read the same."""
    decomposed = unicodedata.normalize("NFD", str(text).replace("đ", "d").replace("Đ", "d"))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def infer_kind(label: str) -> str:
    name = plain(label)
    for kind, words in _WORDS:
        if any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", name) for word in words):
            return kind
    return "other"


def resolve_kind(kind, label: str) -> str:
    return kind if kind in KINDS else infer_kind(label)


def scope_of(kind: str, stated=None) -> str:
    if kind in AROUND_KINDS:
        return "around"
    if kind in ROOF_KINDS:
        return "roof"
    return "around" if stated == "around" else "roof"


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value else None


def clean_obstacles(items, limit: int = 40) -> tuple[list[dict], int, list[str]]:
    """Keep what is usable. One broken box must not cost the engineer every good one.
    Returns the kept boxes (image percent), how many were dropped as unusable and the labels trimmed at the image edge."""
    kept, dropped, trimmed_labels = [], 0, []
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            dropped += 1
            continue
        x, y, w, d = (_number(item.get(k)) for k in ("x_pct", "y_pct", "width_pct", "depth_pct"))
        if None in (x, y, w, d) or w <= 0 or d <= 0 or x >= 100 or y >= 100 or x + w <= 0 or y + d <= 0 or max(x + w, y + d) > 115 or min(x, y) < -15:
            dropped += 1
            continue
        # A box a little past the image edge is trimmed; the position then needs a look.
        left, top, right, bottom = max(0, x), max(0, y), min(100, x + w), min(100, y + d)
        trimmed = (right - left) < w - .01 or (bottom - top) < d - .01
        label = str(item.get("label") or "Vật cản")[:60]
        if trimmed:
            trimmed_labels.append(label)
        kind = resolve_kind(item.get("kind"), label)
        height = _number(item.get("height_m"))
        confidence = _number(item.get("confidence"))
        kept.append({"id": str(item.get("id") or f"o{index + 1}")[:40], "label": label, "kind": kind,
                     "scope": scope_of(kind, item.get("scope")),
                     "x_pct": left, "y_pct": top, "width_pct": max(.2, right - left), "depth_pct": max(.2, bottom - top),
                     "height_m": height if height is not None and 0 <= height <= 500 else None,
                     "confidence": min(1, max(0, confidence)) if confidence is not None else .5,
                     "observation": str(item.get("observation") or "")[:200],
                     "requires_placement": bool(item.get("requires_placement")) or trimmed})
    return merge_boxes(kept)[:limit], dropped, trimmed_labels


def _overlap(a: dict, b: dict) -> float:
    """Shared area over the smaller box: a tank reported inside a larger box of itself still counts as the same."""
    w = min(a["x_pct"] + a["width_pct"], b["x_pct"] + b["width_pct"]) - max(a["x_pct"], b["x_pct"])
    d = min(a["y_pct"] + a["depth_pct"], b["y_pct"] + b["depth_pct"]) - max(a["y_pct"], b["y_pct"])
    if w <= 0 or d <= 0:
        return 0
    return w * d / min(a["width_pct"] * a["depth_pct"], b["width_pct"] * b["depth_pct"])


def merge_boxes(boxes: list[dict]) -> list[dict]:
    """One object reported twice stays one: same kind (or an unnamed one) overlapping by half or more."""
    kept: list[dict] = []
    for box in sorted(boxes, key=lambda b: -b["confidence"]):
        twin = next((k for k in kept if _overlap(box, k) >= .5 and (box["kind"] == k["kind"] or "other" in (box["kind"], k["kind"]))), None)
        if twin is None:
            kept.append(box)
        elif twin["kind"] == "other" and box["kind"] != "other":
            twin.update(kind=box["kind"], scope=box["scope"], label=box["label"])
    return kept
