"""Plans, usage quotas and a minimal admin console for the freemium model.

One "project" use = the first successful layout computation of a project name within the plan's
window; recomputing the same project (or its three objectives) is free. AI image reads are counted
per uncached call because each one costs a provider request. Payment is not integrated: users
send an upgrade request and an admin activates the plan for a number of months.
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.auth import optional_user, require_user, same_origin
from app.database import connect

DAY = 24 * 60 * 60
WINDOW = 30 * DAY
# Prices are hypotheses to validate with customers, not a published tariff.
PLANS = {
    "free": {"name": "Miễn phí", "price_vnd_month": 0, "projects": 5, "project_window": None, "ai_reads": 10,
             "features": ["5 dự án tính phương án", "10 lượt AI đọc ảnh mỗi 30 ngày", "Lịch sử riêng theo tài khoản"]},
    "pro": {"name": "Cá nhân Pro", "price_vnd_month": 399_000, "projects": 30, "project_window": WINDOW, "ai_reads": 100,
            "features": ["30 dự án mỗi 30 ngày", "100 lượt AI đọc ảnh mỗi 30 ngày", "Lịch sử riêng theo tài khoản"]},
    "business": {"name": "Doanh nghiệp", "price_vnd_month": 2_500_000, "projects": 300, "project_window": WINDOW, "ai_reads": 1000,
                 "features": ["300 dự án mỗi 30 ngày", "1.000 lượt AI đọc ảnh mỗi 30 ngày", "Tài khoản nhóm nhiều kỹ sư: đang phát triển"]},
}

router = APIRouter(tags=["billing"])


def guest_daily_projects() -> int:
    return max(0, int(os.getenv("SOLAROPT_GUEST_DAILY_PROJECTS", "2")))


def admin_emails() -> set[str]:
    return {e.strip().lower() for e in os.getenv("SOLAROPT_ADMIN_EMAILS", "").split(",") if e.strip()}


def project_key(name: str) -> str:
    return " ".join(name.strip().lower().split())[:120] or "dự án"


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def current_plan(user_id: int) -> str:
    with connect() as conn:
        row = conn.execute("SELECT plan, plan_until FROM users WHERE id=?", (user_id,)).fetchone()
    if not row or row[0] not in PLANS or (row[0] != "free" and row[1] is not None and row[1] <= time.time()):
        return "free"
    return row[0]


def _limits(user):
    """(owner key, limits). Guests have no owner key here; callers key them by client IP."""
    if user is None:
        return None, {"projects": guest_daily_projects(), "project_window": DAY, "ai_reads": 0}
    plan = PLANS[current_plan(user["id"])]
    return f"u:{user['id']}", {"projects": plan["projects"], "project_window": plan["project_window"], "ai_reads": plan["ai_reads"]}


def _since(window):
    return 0 if window is None else int(time.time()) - window


def usage_for(owner: str, limits: dict) -> dict:
    with connect() as conn:
        projects = conn.execute("SELECT COUNT(DISTINCT project_key) FROM usage_events WHERE owner=? AND kind='project' AND created_at>?",
                                (owner, _since(limits["project_window"]))).fetchone()[0]
        ai = conn.execute("SELECT COUNT(*) FROM usage_events WHERE owner=? AND kind='ai' AND created_at>?", (owner, _since(WINDOW))).fetchone()[0]
    return {"projects": projects, "ai_reads": ai}


class ProjectQuota:
    """Check before computing, record after success; the same project inside the window is free."""

    def __init__(self, request: Request, user, name: str):
        self.owner, self.limits = _limits(user)
        if user is None:
            self.owner = f"ip:{client_ip(request)}"
        self.key, self.user = project_key(name), user

    def counted(self) -> bool:
        with connect() as conn:
            return conn.execute("SELECT 1 FROM usage_events WHERE owner=? AND kind='project' AND project_key=? AND created_at>? LIMIT 1",
                                (self.owner, self.key, _since(self.limits["project_window"]))).fetchone() is not None

    def check(self) -> None:
        if self.counted():
            return
        if usage_for(self.owner, self.limits)["projects"] >= self.limits["projects"]:
            if self.user is None:
                raise HTTPException(402, f"Chế độ khách được thử {self.limits['projects']} dự án mỗi ngày. Đăng ký miễn phí để có thêm 5 dự án và lưu lịch sử.")
            raise HTTPException(402, f"Đã dùng hết {self.limits['projects']} dự án của gói hiện tại. Nâng cấp gói hoặc mở lại một dự án đã tính.")

    def record(self) -> None:
        with connect() as conn:
            exists = conn.execute("SELECT 1 FROM usage_events WHERE owner=? AND kind='project' AND project_key=? AND created_at>? LIMIT 1",
                                  (self.owner, self.key, _since(self.limits["project_window"]))).fetchone()
            if not exists:
                conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,?,?)", (self.owner, "project", self.key, int(time.time())))


def check_ai(user) -> None:
    owner, limits = _limits(user)
    if usage_for(owner, limits)["ai_reads"] >= limits["ai_reads"]:
        raise HTTPException(402, f"Đã dùng hết {limits['ai_reads']} lượt AI đọc ảnh trong 30 ngày. Nâng cấp gói hoặc nhập số liệu thủ công.")


def record_ai(user) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,NULL,?)", (f"u:{user['id']}", "ai", int(time.time())))


def is_admin(user) -> bool:
    return bool(user) and user["email"].lower() in admin_emails()


@router.get("/api/account/usage")
def account_usage(request: Request, user=Depends(optional_user)):
    catalog = {k: {key: v[key] for key in ("name", "price_vnd_month", "projects", "ai_reads", "features")} | {"project_window_days": v["project_window"] // DAY if v["project_window"] else None}
               for k, v in PLANS.items()}
    if user is None:
        owner, limits = f"ip:{client_ip(request)}", _limits(None)[1]
        return {"plan": "guest", "plan_name": "Khách", "limits": limits, "used": usage_for(owner, limits), "plans": catalog, "is_admin": False, "plan_until": None}
    plan = current_plan(user["id"])
    with connect() as conn:
        until = conn.execute("SELECT plan_until FROM users WHERE id=?", (user["id"],)).fetchone()[0]
        pending = conn.execute("SELECT plan FROM upgrade_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (user["id"],)).fetchone()
    owner, limits = _limits(user)
    return {"plan": plan, "plan_name": PLANS[plan]["name"], "plan_until": until if plan != "free" else None, "limits": limits,
            "used": usage_for(owner, limits), "plans": catalog, "is_admin": is_admin(user), "pending_request": pending[0] if pending else None}


class UpgradeRequest(BaseModel):
    plan: str
    note: str = Field(default="", max_length=500)


@router.post("/api/account/upgrade-request", dependencies=[Depends(same_origin)], status_code=201)
def upgrade_request(body: UpgradeRequest, user=Depends(require_user)):
    if body.plan not in PLANS or body.plan == "free":
        raise HTTPException(422, "Gói không hợp lệ.")
    with connect() as conn:
        conn.execute("UPDATE upgrade_requests SET status='replaced' WHERE user_id=? AND status='pending'", (user["id"],))
        conn.execute("INSERT INTO upgrade_requests(user_id,plan,note,created_at) VALUES(?,?,?,?)", (user["id"], body.plan, body.note.strip(), int(time.time())))
    return {"ok": True}


def require_admin(user=Depends(require_user)):
    if not is_admin(user):
        raise HTTPException(403, "Chỉ quản trị viên được truy cập.")
    return user


@router.get("/api/admin/users")
def admin_users(admin=Depends(require_admin)):
    with connect() as conn:
        rows = conn.execute("SELECT id,email,plan,plan_until,created_at FROM users ORDER BY id DESC LIMIT 500").fetchall()
        requests = {r[0]: {"plan": r[1], "note": r[2], "created_at": r[3]} for r in conn.execute(
            "SELECT user_id,plan,note,created_at FROM upgrade_requests WHERE status='pending' ORDER BY id")}
    out = []
    for uid, email, plan, until, created in rows:
        user = {"id": uid, "email": email}
        owner, limits = _limits(user)
        out.append({"id": uid, "email": email, "plan": current_plan(uid), "stored_plan": plan, "plan_until": until, "created_at": created,
                    "limits": limits, "used": usage_for(owner, limits), "pending_request": requests.get(uid)})
    return out


class PlanChange(BaseModel):
    plan: str
    months: int = Field(default=1, ge=1, le=36)


@router.post("/api/admin/users/{user_id}/plan", dependencies=[Depends(same_origin)])
def admin_set_plan(user_id: int, body: PlanChange, admin=Depends(require_admin)):
    if body.plan not in PLANS:
        raise HTTPException(422, "Gói không hợp lệ.")
    until = None if body.plan == "free" else int(time.time()) + body.months * WINDOW
    with connect() as conn:
        if conn.execute("UPDATE users SET plan=?, plan_until=? WHERE id=?", (body.plan, until, user_id)).rowcount == 0:
            raise HTTPException(404, "Không tìm thấy người dùng.")
        conn.execute("UPDATE upgrade_requests SET status='done' WHERE user_id=? AND status='pending'", (user_id,))
    return {"id": user_id, "plan": body.plan, "plan_until": until}
