"""Demo recordings: real AI answers saved once, replayed on stage so a pitch never waits on a busy free model.

A recording is keyed by the inputs that decide the answer (image bytes, or the roof, obstacles, panel, customer
and engineer notes for the advisor). Change any of them and there is no match, so the request goes to the live
model as usual. Every replay says so, with the recording date, the model and how long the live call took.
Recording is on only when SOLAROPT_DEMO_RECORD=1; files live in backend/demo_recordings/ and are committed.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.getenv("SOLAROPT_DEMO_DIR", Path(__file__).resolve().parent.parent / "demo_recordings"))

# Config fields that shape the advisor's answer; budget, target and reserve are what the advisor itself proposes.
ADVISOR_CONFIG_FIELDS = ("latitude", "longitude", "roof_width_m", "roof_height_m", "roof_azimuth_deg", "roof_tilt_deg",
                         "north_rotation_deg", "roof_elevation_m", "roof_polygon", "roof_faces", "roof_openings", "setback_m",
                         "panel_gap_m", "obstacle_clearance_m", "mounting", "annual_irradiance_kwh_m2", "performance_ratio")


def recording_enabled() -> bool:
    return os.getenv("SOLAROPT_DEMO_RECORD", "").strip() == "1"


def _rounded(value):
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    return value


def _hash(payload) -> str:
    return hashlib.sha256(json.dumps(_rounded(payload), ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def vision_key(files: list[tuple[bytes, str]], input_kind: str, width: float | None, height: float | None) -> str:
    digest = hashlib.sha256()
    for data, mime in files:
        digest.update(mime.encode())
        digest.update(data)
    return _hash({"kind": "vision", "input": input_kind, "width": width, "height": height, "files": digest.hexdigest()})


def advisor_key(req) -> str:
    return _hash(advisor_inputs(req))


def advisor_inputs(req) -> dict:
    config = req.config.model_dump()
    # Obstacle ids are minted per session (timestamps), so only the geometry is part of the key.
    obstacles = [{k: o[k] for k in ("x", "y", "width_m", "depth_m", "height_m", "scope", "shape", "rotation_deg", "points")}
                 for o in (ob.model_dump() for ob in req.obstacles)]
    return {"kind": "advisor", "config": {k: config.get(k) for k in ADVISOR_CONFIG_FIELDS}, "obstacles": obstacles,
            "panel": req.panel.model_dump(), "need": req.need, "customer": req.customer.model_dump(),
            "finance": req.finance.model_dump(), "feedback": req.feedback,
            "previous": req.previous.summary if req.previous else None}


def assistant_key(req) -> str:
    return _hash(assistant_inputs(req))


def assistant_inputs(req) -> dict:
    """The chat replays only for the same conversation on the same roof and layout."""
    config = req.config.model_dump()
    obstacles = [{k: o[k] for k in ("x", "y", "width_m", "depth_m", "height_m", "scope", "shape", "rotation_deg", "points")}
                 for o in (ob.model_dump() for ob in req.obstacles)]
    design = req.design.metrics if req.design else None
    return {"kind": "assistant", "messages": [[t.role, t.content] for t in req.messages],
            "config": {k: config.get(k) for k in ADVISOR_CONFIG_FIELDS + ("budget_vnd", "layout_edge_reserve_m")}, "obstacles": obstacles,
            "panel": req.panel.model_dump(), "design": [design.panel_count, round(design.annual_energy_kwh, -1)] if design else None,
            "economics": req.economics}


def load(kind: str, key: str) -> dict | None:
    path = ROOT / f"{kind}-{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save(kind: str, key: str, result: dict, model: str, elapsed_ms: float, inputs: dict | None = None) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    # The inputs are kept so a replay that stops matching can be traced to the field that changed.
    record = {"recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": model,
              "live_elapsed_ms": round(elapsed_ms), "inputs": inputs, "result": result}
    (ROOT / f"{kind}-{key}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def label(record: dict) -> str:
    when = record.get("recorded_at", "")
    try:
        when = datetime.fromisoformat(when).astimezone().strftime("%d/%m/%Y %H:%M")
    except ValueError:
        pass
    seconds = record.get("live_elapsed_ms", 0) / 1000
    return f"Phát lại kết quả AI thật đã ghi lúc {when} · mô hình {record.get('model') or 'không rõ'} · lần gọi thật mất {seconds:.0f} giây"
