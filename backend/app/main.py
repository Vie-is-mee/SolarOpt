from __future__ import annotations

from copy import deepcopy
from datetime import date
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, list_versions, save_version
from app.schemas import (
    DesignRequest, DesignResult, RepairRequest, RepairResult, StressRequest, StressResult,
    SunPosition, SunRequest, VerifyRequest, VerifyResult, VisionResult, IrradianceResult,
    UncertaintyRequest, UncertaintyResult,
)
from app.services.dependency import trace_impact
from app.services.gemini_vision import analyze_image
from app.services.optimizer import generate_design
from app.services.solar import fetch_pvgis, sun_position
from app.services.stress import run_stress_tests
from app.services.verifier import verify_design
from app.services.uncertainty import evaluate_uncertainty

load_dotenv()
init_db()

app = FastAPI(title="SolarOpt API", version="1.0.0", description="Backend cho nguyên mẫu SolarOpt AI 2026")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
    }


@app.post("/api/vision/analyze", response_model=VisionResult)
async def vision_analyze(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Tệp quá lớn; giới hạn demo là 12 MB")
    mime = file.content_type or "application/octet-stream"
    if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}:
        raise HTTPException(status_code=415, detail="Chỉ hỗ trợ JPG/PNG/WEBP/GIF/PDF")
    return analyze_image(data, mime)


@app.post("/api/solar/sun-position", response_model=SunPosition)
def get_sun_position(req: SunRequest):
    return sun_position(req)


@app.get("/api/solar/irradiance", response_model=IrradianceResult)
def get_irradiance(
    lat: float = Query(...), lon: float = Query(...), tilt: float = 10.0, azimuth: float = 180.0
):
    return fetch_pvgis(lat, lon, tilt, azimuth)


@app.post("/api/design/generate", response_model=DesignResult)
def design_generate(req: DesignRequest):
    result = generate_design(req)
    save_version(req.config.project_name, "design", f"Generate {req.objective}", result.model_dump())
    return result


@app.post("/api/design/verify", response_model=VerifyResult)
def design_verify(req: VerifyRequest):
    return verify_design(req)


@app.post("/api/design/stress-test", response_model=StressResult)
def design_stress(req: StressRequest):
    return run_stress_tests(req)


@app.post("/api/design/repair", response_model=RepairResult)
def design_repair(req: RepairRequest):
    changed_input = "obstacle_height"
    if len(req.obstacles_before) != len(req.obstacles_after):
        changed_input = "obstacle_geometry"
    else:
        before = {o.id: o for o in req.obstacles_before}
        for after in req.obstacles_after:
            old = before.get(after.id)
            if old and (old.x != after.x or old.y != after.y or old.width_m != after.width_m or old.depth_m != after.depth_m):
                changed_input = "obstacle_geometry"
                break
    impact = trace_impact(changed_input)
    design = generate_design(DesignRequest(
        config=req.config,
        panel=req.panel,
        obstacles=req.obstacles_after,
        sun=req.sun,
        objective=req.objective,
        previous_panels=req.previous_design.panels,
        minimal_repair_weight=req.minimal_repair_weight,
    ))
    verification = verify_design(VerifyRequest(
        config=req.config, panel=req.panel, obstacles=req.obstacles_after, design=design, sun=req.sun
    ))
    save_version(req.config.project_name, "repair", f"Self-heal after {changed_input}", {
        "impact": impact.model_dump(), "design": design.model_dump(), "verification": verification.model_dump()
    })
    return RepairResult(impact=impact, design=design, verification=verification)


@app.post("/api/uncertainty/evaluate", response_model=UncertaintyResult)
def uncertainty_evaluate(req: UncertaintyRequest):
    try:
        return evaluate_uncertainty(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/projects/{project_name}/versions")
def project_versions(project_name: str):
    return list_versions(project_name)
