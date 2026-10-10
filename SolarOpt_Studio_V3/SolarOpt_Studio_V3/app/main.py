from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.engine.orchestrator import (
    new_demo_state,
    run_autopilot,
    change_tank_height,
    change_panel,
    uncertainty_probe,
    configure_project,
    select_design_option,
    snapshot,
)

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
STATIC = BASE / "static"
UPLOADS = BASE / "uploads"
DEMO_INPUT = ROOT / "demo_input"
UPLOADS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SolarOpt Studio Demo", version="0.3.0")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")
app.mount("/demo", StaticFiles(directory=str(DEMO_INPUT)), name="demo")

STATE = new_demo_state()


class HeightChange(BaseModel):
    height_m: float


class PanelChange(BaseModel):
    panel_id: str


class UncertaintyProbe(BaseModel):
    high_impact: bool = True


class ProjectConfig(BaseModel):
    panel_id: str = "LONGI_580"
    latitude: float = 10.776
    longitude: float = 106.701
    roof_tilt_deg: float = 15.0
    roof_azimuth_deg: float = 178.0
    edge_setback_m: float = 0.45
    objective: str = "balanced"
    budget_vnd: int = 120_000_000
    inverter_name: str = "Huawei SUN2000-12K-MAP0"


class DesignOptionSelection(BaseModel):
    option_id: str


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "solaropt-studio-demo"}


@app.get("/api/state")
def get_state():
    return snapshot(STATE)


@app.post("/api/reset")
def reset():
    global STATE
    STATE = new_demo_state()
    return snapshot(STATE)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf"}
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, "Hỗ trợ PNG, JPG, WEBP, SVG hoặc PDF trong demo này.")
    content = await file.read()
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(400, "File quá 12 MB.")
    safe_name = f"{uuid4().hex[:10]}{suffix}"
    target = UPLOADS / safe_name
    target.write_bytes(content)
    STATE.uploaded_file = {
        "name": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "url": f"/uploads/{safe_name}",
    }
    STATE.source_label = file.filename or "File đã tải lên"
    return {"ok": True, "file": STATE.uploaded_file, "state": snapshot(STATE)}


@app.post("/api/configure")
def configure(payload: ProjectConfig):
    try:
        return configure_project(
            STATE,
            panel_id=payload.panel_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            roof_tilt_deg=payload.roof_tilt_deg,
            roof_azimuth_deg=payload.roof_azimuth_deg,
            edge_setback_m=payload.edge_setback_m,
            objective=payload.objective,
            budget_vnd=payload.budget_vnd,
            inverter_name=payload.inverter_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/autopilot")
def autopilot():
    return run_autopilot(STATE)


@app.post("/api/change/tank-height")
def tank_height(payload: HeightChange):
    if payload.height_m < 0.1 or payload.height_m > 4.0:
        raise HTTPException(400, "height_m must be between 0.1 and 4.0")
    return change_tank_height(STATE, payload.height_m)


@app.post("/api/change/panel")
def panel_change(payload: PanelChange):
    try:
        return change_panel(STATE, payload.panel_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/uncertainty")
def uncertainty(payload: UncertaintyProbe):
    return uncertainty_probe(STATE, payload.high_impact)


@app.post("/api/design/select")
def design_select(payload: DesignOptionSelection):
    try:
        return select_design_option(STATE, payload.option_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
