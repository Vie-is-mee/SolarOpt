from __future__ import annotations

from copy import deepcopy
from datetime import date
import os
from pathlib import Path
from time import perf_counter
from threading import BoundedSemaphore

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from typing import Literal
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import COOKIE, router as auth_router, optional_user, require_user
from app.billing import router as billing_router, ProjectQuota, check_ai, record_ai
from fastapi import Request
from app.database import init_db, list_versions, save_version, get_version
from app.schemas import (
    DesignRequest, DesignResult, RepairRequest, RepairResult, StressRequest, StressResult, StressPreviewRequest,
    SunPosition, SunRequest, VerifyRequest, VerifyResult, VisionResult, IrradianceResult,
    UncertaintyRequest, UncertaintyResult, SceneRequest, ProjectConfig,
)
from app.services.dependency import trace_impact
from app.services.vision import analyze_images, provider_status, VisionError
from app.services.scene import simulate_scene
from app.services.optimizer import generate_design
from app.services.solar import fetch_pvgis, sun_position
from app.services.stress import run_stress_tests, preview_stress
from app.services.verifier import verify_design
from app.services.uncertainty import evaluate_uncertainty
from app.services.roof_extract import TraceRequest, extract_roof, prepare_image

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
init_db()

app = FastAPI(title="SolarOpt API", version="2.0.0", description="Bộ tính toán và trích xuất ảnh cho SolarOpt Studio")

app.include_router(auth_router)
app.include_router(billing_router)


@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    if getattr(request.state, "invalid_session", False):
        response.delete_cookie(COOKIE, path="/api")
    if request.url.path.startswith(("/api/auth/", "/api/history", "/api/projects/")):
        response.headers["Cache-Control"] = "private, no-store"
    return response


compute_slots = BoundedSemaphore(max(1, int(os.getenv("SOLAROPT_MAX_COMPUTE", "1"))))
heavy_paths = {"/api/design/stress-preview", "/api/design/generate", "/api/design/repair", "/api/design/stress-test", "/api/uncertainty/evaluate", "/api/roof/trace", "/api/vision/analyze"}


@app.middleware("http")
async def bound_compute(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.cookies.get(COOKIE) and request.headers.get("X-SolarOpt-Request") != "1":
        return JSONResponse(status_code=403, content={"detail": "Thiếu xác nhận yêu cầu."})
    if request.method != "POST" or request.url.path not in heavy_paths:
        return await call_next(request)
    if not compute_slots.acquire(blocking=False):
        return JSONResponse(status_code=429, headers={"Retry-After": "5"}, content={"detail": "Máy chủ đang xử lý tác vụ khác. Vui lòng thử lại sau vài giây."})
    try:
        return await call_next(request)
    finally:
        compute_slots.release()


@app.exception_handler(ValueError)
async def invalid_value(request, exc):
    return JSONResponse(status_code=422, content={"detail":str(exc)})
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
        "ai": provider_status(),
        "version": "2.0.0",
    }


@app.post("/api/vision/analyze", response_model=VisionResult)
async def vision_analyze(file: UploadFile = File(...), context_files: list[UploadFile] = File(default=[]), input_kind: str = Form("drone"), roof_width_m: float | None = Form(None), roof_height_m: float | None = Form(None), user=Depends(require_user)):
    if input_kind not in {"drone", "plan", "partial"}:
        raise HTTPException(422, "Loại đầu vào không hợp lệ.")
    if len(context_files)>2:
        raise HTTPException(422, "Tối đa một ảnh chính và hai ảnh chi tiết.")
    files = []
    for upload in [file,*context_files]:
        data = await upload.read(12*1024*1024+1)
        if len(data)>12*1024*1024:
            raise HTTPException(413, "Mỗi tệp tối đa 12 MB.")
        if upload.content_type not in {"image/jpeg","image/png","image/webp","application/pdf"}:
            raise HTTPException(415, "Chỉ hỗ trợ JPG/PNG/WEBP/PDF.")
        files.append((data,upload.content_type))
    check_ai(user)
    try:
        result = await run_in_threadpool(analyze_images,files,input_kind,roof_width_m,roof_height_m)
    except VisionError as exc:
        raise HTTPException(exc.status,str(exc)) from exc
    # Cached and "AI not configured" answers cost nothing, so they do not use the quota.
    if result.mode != "manual" and not result.cached:
        record_ai(user)
    return result


@app.post("/api/solar/scene")
def solar_scene(req: SceneRequest):
    return simulate_scene(req)


@app.post("/api/roof/prepare")
async def roof_prepare(file: UploadFile = File(...)):
    data=await file.read(12*1024*1024+1)
    if len(data)>12*1024*1024: raise HTTPException(413,"Mỗi tệp tối đa 12 MB.")
    if file.content_type not in {"image/jpeg","image/png","image/webp","application/pdf"}:raise HTTPException(415,"Loại tệp không hỗ trợ.")
    try:return await run_in_threadpool(prepare_image,data,file.content_type)
    except VisionError as exc:raise HTTPException(exc.status,str(exc)) from exc


class RoofTemplateRequest(BaseModel):
    config: ProjectConfig
    shape: str
    ridge_axis: Literal["x", "y"] = "x"
    rise_m: float = Field(default=2.0, ge=0, le=50)
    low_side: Literal["start", "end"] = "start"
    tolerance_m: float = Field(default=.05, gt=0, le=.5)
    panel_pitch_m: float | None = Field(default=None, gt=0, le=10)


@app.post("/api/roof/template")
def roof_template(req: RoofTemplateRequest):
    from app.services.roof_templates import generate_faces
    try:
        faces, notes = generate_faces(req.config, req.shape, req.ridge_axis, req.rise_m, req.low_side, req.tolerance_m, req.panel_pitch_m)
        ProjectConfig(**{**req.config.model_dump(), "roof_faces": [f.model_dump() for f in faces]})
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"roof_faces": faces, "notes": notes}


@app.post("/api/roof/trace")
async def roof_trace(req: TraceRequest):
    return await run_in_threadpool(extract_roof,req)


@app.post("/api/solar/sun-position", response_model=SunPosition)
def get_sun_position(req: SunRequest):
    return sun_position(req)


@app.get("/api/solar/irradiance", response_model=IrradianceResult)
def get_irradiance(
    lat: float = Query(...), lon: float = Query(...), tilt: float = 10.0, azimuth: float = 180.0
):
    return fetch_pvgis(lat, lon, tilt, azimuth)


@app.post("/api/design/generate", response_model=DesignResult)
def design_generate(req: DesignRequest, request: Request, user=Depends(optional_user)):
    quota = ProjectQuota(request, user, req.config.project_name)
    quota.check()
    result = generate_design(req)
    if result.panels:
        quota.record()
    if user:
        save_version(req.config.project_name, "design", f"Thiết kế: {req.objective}", {"config":req.config.model_dump(),"panel":req.panel.model_dump(),"obstacles": [o.model_dump() for o in req.obstacles],"design":result.model_dump(),"evidence":req.evidence.model_dump(mode='json') if req.evidence else None}, user_id=user["id"])
    return result


@app.post("/api/design/verify", response_model=VerifyResult)
def design_verify(req: VerifyRequest):
    return verify_design(req)


@app.post("/api/design/stress-test", response_model=StressResult)
def design_stress(req: StressRequest):
    return run_stress_tests(req)


@app.post("/api/design/stress-preview")
def design_stress_preview(req: StressPreviewRequest):
    return preview_stress(req)


@app.post("/api/projects/validate")
def validate_project(req: DesignRequest):
    return {"valid": True}


@app.post("/api/design/repair", response_model=RepairResult)
def design_repair(req: RepairRequest, request: Request, user=Depends(optional_user)):
    quota = ProjectQuota(request, user, req.config.project_name)
    quota.check()
    changed = []
    before = {o.id: o for o in req.obstacles_before}
    after = {o.id: o for o in req.obstacles_after}
    if before.keys() != after.keys() or any(
        any(getattr(before[oid], field) != getattr(after[oid], field)
            for field in ("x", "y", "width_m", "depth_m", "scope", "shape", "rotation_deg", "points", "base_elevation_m"))
        for oid in before.keys() & after.keys()
    ):
        changed.append("obstacle_geometry")
    if any(before[oid].height_m != after[oid].height_m for oid in before.keys() & after.keys()):
        changed.append("obstacle_height")
    if req.previous_config:
        for node, fields in {
            "roof_dimensions": ("roof_width_m", "roof_height_m", "roof_polygon", "roof_faces", "roof_openings"),
            "roof_orientation": ("north_rotation_deg", "roof_azimuth_deg", "roof_tilt_deg", "latitude", "longitude", "roof_elevation_m"),
            "irradiance": ("annual_irradiance_kwh_m2", "irradiance_reference_tilt_deg", "irradiance_reference_azimuth_deg", "performance_ratio"),
            "budget": ("budget_vnd",),
            "design_rules": ("setback_m", "obstacle_clearance_m", "panel_gap_m", "layout_angle_deg", "layout_edge_reserve_m", "target_energy_kwh_year"),
        }.items():
            if any(getattr(req.previous_config, field) != getattr(req.config, field) for field in fields):
                changed.append(node)
    if req.previous_panel and req.previous_panel != req.panel:
        changed.append("panel_spec")
    if not changed:
        changed.append("objective")
    changed_input = ", ".join(changed)
    impact = trace_impact(changed)
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
    if user:
        save_version(req.config.project_name, "repair", f"Self-heal after {changed_input}", {
            "config":req.config.model_dump(),"panel":req.panel.model_dump(),"obstacles":[o.model_dump() for o in req.obstacles_after],"impact": impact.model_dump(), "design": design.model_dump(), "verification": verification.model_dump(),"evidence":req.evidence.model_dump(mode='json') if req.evidence else None
        }, user_id=user["id"])
    if design.panels:
        quota.record()
    return RepairResult(impact=impact, design=design, verification=verification)


@app.post("/api/uncertainty/evaluate", response_model=UncertaintyResult)
def uncertainty_evaluate(req: UncertaintyRequest):
    try:
        return evaluate_uncertainty(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/history")
def account_history(user=Depends(require_user)):
    return list_versions(None, user["id"])


@app.get("/api/projects/{project_name}/versions")
def project_versions(project_name: str, user=Depends(require_user)):
    return list_versions(project_name, user["id"])


@app.get('/api/projects/{project_name}/versions/{version_id}')
def project_version(project_name:str,version_id:int,user=Depends(require_user)):
    version=get_version(project_name,version_id,user["id"])
    if version is None:raise HTTPException(404,'Không tìm thấy phiên bản của dự án này.')
    return version


@app.post("/api/projects/approve")
def approve_project(req: VerifyRequest, user=Depends(require_user)):
    if not req.config.geometry_confirmed or any(not o.confirmed for o in req.obstacles):
        raise HTTPException(409, "Kỹ sư cần xác nhận hình học và tất cả vật cản trước khi lưu bản duyệt.")
    verification = verify_design(req)
    if not verification.valid:
        raise HTTPException(409, "Phương án chưa đạt các kiểm tra bắt buộc.")
    version_id = save_version(req.config.project_name,"approved","Kỹ sư xác nhận trong phạm vi kiểm tra MVP",{**req.model_dump(mode='json'),"verification":verification.model_dump()}, user_id=user["id"])
    return {"version_id":version_id,"verification":verification,"scope":"Xác nhận nội bộ bản sơ bộ; không phải chứng nhận đủ điều kiện thi công."}
