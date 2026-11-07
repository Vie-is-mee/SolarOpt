from __future__ import annotations

from copy import deepcopy
from datetime import date
import os
from pathlib import Path
from time import perf_counter
from threading import BoundedSemaphore
import asyncio
from app.memory import limit_arenas, release_memory

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from typing import Literal
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import COOKIE, ensure_env_admin, router as auth_router, optional_user, require_user
from app.billing import router as billing_router, ProjectQuota, chat_block, check_ai, record_ai, record_chat, team_member_ids, project_ref, visible_versions, hidden_projects
from fastapi import Request
from app.database import init_db, list_versions, save_version, get_version
from app.schemas import (
    DesignRequest, DesignResult, RepairRequest, RepairResult, StressRequest, StressResult, StressPreviewRequest,
    SunPosition, SunRequest, VerifyRequest, VerifyResult, VisionResult, IrradianceResult,
    UncertaintyRequest, UncertaintyResult, SceneRequest, ProjectConfig,
)
from app.services.advisor.agent import propose
from app.services.assistant import AssistantReply, AssistantRequest, answer as assistant_answer
from app.services.advisor.llm import default_client
from app.services.advisor.models import AdvisorRequest, Proposal
from app import demo
from app.services.dependency import trace_impact
from app.services.electrical import CATALOG, ElectricalRequest, ElectricalResult, design_electrical
from app.services.site import SiteReview, SiteReviewRequest, review_site
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
ensure_env_admin()

app = FastAPI(title="SolarOpt API", version="2.0.0", description="Bộ tính toán và trích xuất ảnh cho SolarOpt Studio")

limit_arenas()
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
# Interactive calculations (the shadow scene is requested several times a second while the hour slider
# plays) wait their turn instead of running side by side in the thread pool: each one allocates a lot.
light_paths = {"/api/solar/scene", "/api/design/electrical", "/api/site/review", "/api/design/verify", "/api/design/evaluate",
               "/api/solar/weather", "/api/roof/template", "/api/projects/validate"}
light_slots = asyncio.Semaphore(max(1, int(os.getenv("SOLAROPT_MAX_LIGHT", "2"))))
_served = 0
heavy_paths = {"/api/advisor/propose", "/api/assistant/chat", "/api/design/mounting-compare", "/api/design/stress-preview", "/api/design/generate", "/api/design/repair", "/api/design/stress-test", "/api/uncertainty/evaluate", "/api/roof/trace", "/api/vision/analyze"}


@app.middleware("http")
async def bound_compute(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.cookies.get(COOKIE) and request.headers.get("X-SolarOpt-Request") != "1":
        return JSONResponse(status_code=403, content={"detail": "Thiếu xác nhận yêu cầu."})
    global _served
    if request.method == "POST" and request.url.path in light_paths:
        async with light_slots:
            response = await call_next(request)
        _served += 1
        if _served % 25 == 0:
            release_memory()
        return response
    if request.method != "POST" or request.url.path not in heavy_paths:
        return await call_next(request)
    if not compute_slots.acquire(blocking=False):
        return JSONResponse(status_code=429, headers={"Retry-After": "5"}, content={"detail": "Máy chủ đang xử lý tác vụ khác. Vui lòng thử lại sau vài giây."})
    try:
        return await call_next(request)
    finally:
        compute_slots.release()
        release_memory()


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
async def vision_analyze(file: UploadFile = File(...), context_files: list[UploadFile] = File(default=[]), input_kind: str = Form("drone"), roof_width_m: float | None = Form(None), roof_height_m: float | None = Form(None), demo_mode: bool = Form(False), user=Depends(optional_user)):
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
    key = demo.vision_key(files, input_kind, roof_width_m, roof_height_m)
    # A replay calls no model and costs nothing, so it needs neither an account nor quota.
    if demo_mode and (record := demo.load("vision", key)):
        result = VisionResult.model_validate(record["result"])
        result.replay, result.elapsed_ms = demo.label(record), 0
        result.events = [{"stage": "demo", "status": "complete", "detail": result.replay}]
        return result
    if user is None:
        raise HTTPException(401, "Vui lòng đăng nhập.")
    check_ai(user)
    try:
        result = await run_in_threadpool(analyze_images,files,input_kind,roof_width_m,roof_height_m)
    except VisionError as exc:
        raise HTTPException(exc.status,str(exc)) from exc
    if demo.recording_enabled() and result.mode != "manual" and not result.cached:
        demo.save("vision", key, result.model_dump(), result.model, result.elapsed_ms)
    # Cached and "AI not configured" answers cost nothing, so they do not use the quota.
    if result.mode != "manual" and not result.cached:
        record_ai(user)
    return result


@app.get("/api/advisor/status")
def advisor_status():
    client = default_client()
    return {"llm": client is not None, "model": getattr(client, "model", ""), "provider": provider_status()["provider"]}


@app.post("/api/advisor/propose", response_model=Proposal)
def advisor_propose(req: AdvisorRequest, request: Request, user=Depends(optional_user)):
    # Each proposal runs up to four layouts; it counts against the project quota like a design run.
    key = demo.advisor_key(req)
    if req.demo and (record := demo.load("advisor", key)):
        result = Proposal.model_validate(record["result"])
        result.replay, result.elapsed_ms = demo.label(record), 0
        return result
    # Recording runs only on a developer machine (env flag), so it is not held to the guest quota.
    quota = None if demo.recording_enabled() else ProjectQuota(request, user, req.config)
    if quota:
        quota.check()
    # Guests get the rule-based planner: a paid AI call needs an account.
    guest_rules = user is None and req.use_llm and not demo.recording_enabled()
    if guest_rules:
        req = req.model_copy(update={"use_llm": False})
    try:
        # A recording should hold the model's full reasoning, so it gets the normal time budget, not the stage one.
        result = propose(req.model_copy(update={"demo": False}) if demo.recording_enabled() else req)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if guest_rules:
        result.notice = "Đăng nhập để dùng trợ lý AI; đề xuất dưới đây do bộ quy tắc của SolarOpt lập từ cùng số liệu."
    if quota:
        quota.record()
    if demo.recording_enabled() and result.mode == "llm":
        demo.save("advisor", key, result.model_dump(), result.model, result.elapsed_ms, demo.advisor_inputs(req))
    return result


@app.post("/api/assistant/chat", response_model=AssistantReply)
def assistant_chat(req: AssistantRequest, user=Depends(optional_user)):
    # Answers read facts and may run one what-if layout; edits come back as proposals the engineer confirms.
    key = demo.assistant_key(req)
    if req.demo and (record := demo.load("assistant", key)):
        result = AssistantReply.model_validate(record["result"])
        result.replay, result.elapsed_ms = demo.label(record), 0
        return result
    # Each AI answer is billed per account; guests and exhausted plans get the rule-based reader instead.
    billed = req.use_llm and not demo.recording_enabled()
    blocked = chat_block(user) if billed else None
    if blocked:
        req = req.model_copy(update={"use_llm": False})
    result = assistant_answer(req.model_copy(update={"demo": False}) if demo.recording_enabled() else req)
    if blocked:
        result.notice = blocked
    elif billed and result.mode == "llm":
        record_chat(user)
    if demo.recording_enabled() and result.mode == "llm":
        demo.save("assistant", key, result.model_dump(), result.model, result.elapsed_ms, demo.assistant_inputs(req))
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
    strips: int | None = Field(default=None, ge=2, le=20, description="Curved roofs: number of flat strips; None follows the panel rows")
    # Stacked roof part: x, y (bottom-left), width, depth on the drawing; its eave defaults to the roof below.
    region: list[float] | None = Field(default=None, min_length=4, max_length=4)
    eave_m: float | None = Field(default=None, ge=0, le=300)


@app.post("/api/roof/template")
def roof_template(req: RoofTemplateRequest):
    from app.services.roof_templates import generate_faces, height_below, stack_faces, stacked_prefix
    try:
        if req.region:
            x, y, w, d = req.region
            if w <= 0 or d <= 0:
                raise ValueError("Vùng mái phụ cần chiều rộng và chiều sâu dương.")
            region = (x, y, x + w, y + d)
            eave = req.eave_m if req.eave_m is not None else height_below(req.config, region)
            n = stacked_prefix(req.config)
            part, notes = generate_faces(req.config, req.shape, req.ridge_axis, req.rise_m, req.low_side, req.tolerance_m, req.panel_pitch_m,
                                         req.strips, region, eave, prefix=f"sub{n}-", label_prefix=f"Mái phụ {n} · ")
            if not part:
                raise ValueError("Vùng mái phụ nằm ngoài biên mái.")
            faces = stack_faces(req.config, part, region)
            notes = [f"Mái phụ {n}: diềm cao {eave:.2f} m".replace(".", ",") + (" (lấy theo đỉnh mái bên dưới)." if req.eave_m is None else "."),
                     *[t for t in notes if not t.startswith("Kích thước tấm")], "Các mặt mái bên dưới vùng này được cắt bỏ; phần còn lại giữ nguyên độ dốc và hướng."]
        else:
            faces, notes = generate_faces(req.config, req.shape, req.ridge_axis, req.rise_m, req.low_side, req.tolerance_m, req.panel_pitch_m, req.strips)
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


class WeatherRequest(BaseModel):
    latitude: float = Field(ge=-89, le=89)
    longitude: float = Field(ge=-180, le=180)
    tilt_deg: float = Field(default=10, ge=0, le=60, description="Main roof plane, for the temperature loss")
    azimuth_deg: float = Field(default=180, ge=0, le=360)
    mounting: Literal["flush", "tilted_rack", "tracker"] = "flush"
    temp_coeff_pct: float = Field(default=-0.32, ge=-1, le=0)


@app.post("/api/solar/weather")
def solar_weather(req: WeatherRequest):
    """Typical-year weather (PVGIS TMY) on the month-hour grid and the temperature loss of the main plane."""
    from app.services.weather import fetch_weather
    weather, losses = fetch_weather(req.latitude, req.longitude, req.tilt_deg, req.azimuth_deg, req.mounting, req.temp_coeff_pct)
    return {"weather": weather, "losses": losses, "performance_ratio": losses.performance_ratio()}


@app.post("/api/design/generate", response_model=DesignResult)
def design_generate(req: DesignRequest, request: Request, user=Depends(optional_user)):
    quota = ProjectQuota(request, user, req.config)
    quota.check()
    result = generate_design(req)
    if result.panels:
        quota.record()
    if user:
        save_version(req.config.project_name, "design", f"Thiết kế: {req.objective}", {"config":req.config.model_dump(),"panel":req.panel.model_dump(),"obstacles": [o.model_dump() for o in req.obstacles],"design":result.model_dump(),"evidence":req.evidence.model_dump(mode='json') if req.evidence else None}, user_id=user["id"], owner=quota.owner, project_key=quota.key)
    return result


@app.post("/api/design/mounting-compare")
def design_mounting_compare(req: DesignRequest, request: Request, user=Depends(optional_user)):
    from app.services.mounting import compare_mountings
    quota = ProjectQuota(request, user, req.config)
    quota.check()
    result = compare_mountings(req)
    if any(o["panels"] for o in result["options"]):
        quota.record()
    return result


@app.post("/api/design/verify", response_model=VerifyResult)
def design_verify(req: VerifyRequest):
    return verify_design(req)


@app.post("/api/design/evaluate")
def design_evaluate(req: VerifyRequest):
    """Numbers and checks for a layout the engineer edited by hand (moved or removed panels)."""
    from app.services.manual_layout import evaluate_layout
    return evaluate_layout(req)


@app.get("/api/electrical/inverters")
def electrical_inverters():
    return CATALOG


@app.post("/api/design/electrical", response_model=ElectricalResult)
def design_electrical_route(req: ElectricalRequest):
    return design_electrical(req)


@app.post("/api/site/review", response_model=SiteReview)
def site_review_route(req: SiteReviewRequest):
    return review_site(req)


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
    quota = ProjectQuota(request, user, req.config)
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
        }, user_id=user["id"], owner=quota.owner, project_key=quota.key)
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
    # Versions of a project whose paid storage lapsed past the grace days are no longer served.
    return visible_versions(list_versions(None, team_member_ids(user["id"])))


@app.get("/api/projects/{project_name}/versions")
def project_versions(project_name: str, user=Depends(require_user)):
    return visible_versions(list_versions(project_name, team_member_ids(user["id"])))


@app.get('/api/projects/{project_name}/versions/{version_id}')
def project_version(project_name:str,version_id:int,user=Depends(require_user)):
    version=get_version(project_name,version_id,team_member_ids(user["id"]))
    if version is None:raise HTTPException(404,'Không tìm thấy phiên bản của dự án này.')
    if (version.get('owner'),version.get('project_key')) in hidden_projects({version.get('owner')} - {None}):
        raise HTTPException(410,'Dữ liệu dự án này đã hết hạn lưu trữ (không gia hạn). Liên hệ quản trị viên nếu cần khôi phục trước khi bị xóa hẳn.')
    return version


@app.post("/api/projects/approve")
def approve_project(req: VerifyRequest, user=Depends(require_user)):
    if not req.config.geometry_confirmed or any(not o.confirmed for o in req.obstacles):
        raise HTTPException(409, "Kỹ sư cần xác nhận hình học và tất cả vật cản trước khi lưu bản duyệt.")
    verification = verify_design(req)
    if not verification.valid:
        raise HTTPException(409, "Phương án chưa đạt các kiểm tra bắt buộc.")
    owner, key = project_ref(user, req.config)
    version_id = save_version(req.config.project_name,"approved","Kỹ sư xác nhận trong phạm vi kiểm tra MVP",{**req.model_dump(mode='json'),"verification":verification.model_dump()}, user_id=user["id"], owner=owner, project_key=key)
    return {"version_id":version_id,"verification":verification,"scope":"Xác nhận nội bộ bản sơ bộ; không phải chứng nhận đủ điều kiện thi công."}
