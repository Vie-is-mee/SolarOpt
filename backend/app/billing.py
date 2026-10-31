"""Plans, usage quotas, team accounts and the admin console for the freemium model.

One "project" use = the first successful layout computation of a project name within the plan's
window; recomputing the same project (or its three objectives) is free. AI image reads are counted
per uncached call. Payment is not integrated: users send an upgrade request and an admin activates
the plan. Admins (users.role='admin', granted only with scripts/manage_admin.py on the server) have
no limits. A team with an active paid plan pools its members' usage and shares project history.
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
UNLIMITED = {"projects": None, "project_window": None, "ai_reads": None}
# Prices are hypotheses to validate with customers, not a published tariff.
PLANS = {
    "free": {"name": "Miễn phí", "price_vnd_month": 0, "projects": 5, "project_window": None, "ai_reads": 10, "seats": 1,
             "features": ["5 dự án tính phương án", "10 lượt AI đọc ảnh mỗi 30 ngày", "Lịch sử riêng theo tài khoản"]},
    "pro": {"name": "Cá nhân Pro", "price_vnd_month": 399_000, "projects": 30, "project_window": WINDOW, "ai_reads": 100, "seats": 1,
            "features": ["30 dự án mỗi 30 ngày", "100 lượt AI đọc ảnh mỗi 30 ngày", "Lịch sử riêng theo tài khoản"]},
    "business": {"name": "Doanh nghiệp", "price_vnd_month": 2_500_000, "projects": 300, "project_window": WINDOW, "ai_reads": 1000, "seats": 5,
                 "features": ["Nhóm tới 5 kỹ sư dùng chung hạn mức", "300 dự án mỗi 30 ngày", "1.000 lượt AI đọc ảnh mỗi 30 ngày", "Lịch sử dự án chung trong nhóm"]},
}

router = APIRouter(tags=["billing"])


def guest_daily_projects() -> int:
    return max(0, int(os.getenv("SOLAROPT_GUEST_DAILY_PROJECTS", "2")))


def project_key(name: str) -> str:
    return " ".join(name.strip().lower().split())[:120] or "dự án"


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _active(plan, until) -> str:
    return plan if plan in PLANS and (plan == "free" or until is None or until > time.time()) else "free"


def is_admin(user) -> bool:
    if not user:
        return False
    with connect() as conn:
        row = conn.execute("SELECT role FROM users WHERE id=?", (user["id"],)).fetchone()
    return bool(row) and row[0] == "admin"


def team_of(user_id: int):
    """(org_id, name, member role, active plan, plan_until, owner_id) or None."""
    with connect() as conn:
        row = conn.execute("SELECT orgs.id, orgs.name, org_members.role, orgs.plan, orgs.plan_until, orgs.owner_id FROM org_members "
                           "JOIN orgs ON orgs.id=org_members.org_id WHERE org_members.user_id=?", (user_id,)).fetchone()
    return None if row is None else (row[0], row[1], row[2], _active(row[3], row[4]), row[4], row[5])


def team_member_ids(user_id: int) -> list[int]:
    """Users whose project history this user may read: the whole team when its plan is paid."""
    team = team_of(user_id)
    if team is None or team[3] == "free":
        return [user_id]
    with connect() as conn:
        return [r[0] for r in conn.execute("SELECT user_id FROM org_members WHERE org_id=?", (team[0],))]


def current_plan(user_id: int) -> str:
    with connect() as conn:
        row = conn.execute("SELECT plan, plan_until FROM users WHERE id=?", (user_id,)).fetchone()
    return _active(*row) if row else "free"


def scope(user):
    """(owner key, limits, plan id, label). Admins are unlimited; a paid team pools usage."""
    if user is None:
        return None, {"projects": guest_daily_projects(), "project_window": DAY, "ai_reads": 0}, "guest", "Khách"
    if is_admin(user):
        return f"u:{user['id']}", dict(UNLIMITED), "admin", "Quản trị viên"
    team = team_of(user["id"])
    if team and team[3] != "free":
        plan = PLANS[team[3]]
        return f"o:{team[0]}", {k: plan[k] for k in ("projects", "project_window", "ai_reads")}, team[3], f"{plan['name']} · {team[1]}"
    plan_id = current_plan(user["id"])
    plan = PLANS[plan_id]
    return f"u:{user['id']}", {k: plan[k] for k in ("projects", "project_window", "ai_reads")}, plan_id, plan["name"]


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
        self.owner, self.limits, _, _ = scope(user)
        if user is None:
            self.owner = f"ip:{client_ip(request)}"
        self.key, self.user = project_key(name), user

    def counted(self) -> bool:
        with connect() as conn:
            return conn.execute("SELECT 1 FROM usage_events WHERE owner=? AND kind='project' AND project_key=? AND created_at>? LIMIT 1",
                                (self.owner, self.key, _since(self.limits["project_window"]))).fetchone() is not None

    def check(self) -> None:
        if self.limits["projects"] is None or self.counted():
            return
        if usage_for(self.owner, self.limits)["projects"] >= self.limits["projects"]:
            if self.user is None:
                raise HTTPException(402, f"Chế độ khách được thử {self.limits['projects']} dự án mỗi ngày. Đăng ký miễn phí để có thêm 5 dự án và lưu lịch sử.")
            raise HTTPException(402, f"Đã dùng hết {self.limits['projects']} dự án của gói hiện tại. Nâng cấp gói hoặc mở lại một dự án đã tính.")

    def record(self) -> None:
        if self.counted():
            return
        with connect() as conn:
            conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,?,?)", (self.owner, "project", self.key, int(time.time())))


def check_ai(user) -> None:
    owner, limits, _, _ = scope(user)
    if limits["ai_reads"] is not None and usage_for(owner, limits)["ai_reads"] >= limits["ai_reads"]:
        raise HTTPException(402, f"Đã dùng hết {limits['ai_reads']} lượt AI đọc ảnh trong 30 ngày. Nâng cấp gói hoặc nhập số liệu thủ công.")


def record_ai(user) -> None:
    owner = scope(user)[0]
    with connect() as conn:
        conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,NULL,?)", (owner, "ai", int(time.time())))


def _catalog():
    return {k: {key: v[key] for key in ("name", "price_vnd_month", "projects", "ai_reads", "features", "seats")}
            | {"project_window_days": v["project_window"] // DAY if v["project_window"] else None} for k, v in PLANS.items()}


def _team_payload(user_id: int):
    team = team_of(user_id)
    if team is None:
        return None
    org_id, name, role, plan, until, _ = team
    with connect() as conn:
        members = [{"id": r[0], "email": r[1], "role": r[2]} for r in conn.execute(
            "SELECT users.id, users.email, org_members.role FROM org_members JOIN users ON users.id=org_members.user_id "
            "WHERE org_id=? ORDER BY org_members.role DESC, users.email", (org_id,))]
    return {"id": org_id, "name": name, "role": role, "plan": plan, "plan_name": PLANS[plan]["name"],
            "plan_until": until if plan != "free" else None, "seats": PLANS[plan]["seats"], "members": members}


@router.get("/api/account/usage")
def account_usage(request: Request, user=Depends(optional_user)):
    owner, limits, plan, label = scope(user)
    if user is None:
        owner = f"ip:{client_ip(request)}"
    out = {"plan": plan, "plan_name": label, "limits": limits, "used": usage_for(owner, limits), "plans": _catalog(),
           "is_admin": plan == "admin", "plan_until": None, "pending_request": None, "team": None}
    if user is not None:
        with connect() as conn:
            until = conn.execute("SELECT plan_until FROM users WHERE id=?", (user["id"],)).fetchone()[0]
            pending = conn.execute("SELECT plan FROM upgrade_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (user["id"],)).fetchone()
        team = _team_payload(user["id"])
        shared = team is not None and team["plan"] != "free" and plan != "admin"
        out.update(plan_until=team["plan_until"] if shared else (until if plan in ("pro", "business") else None),
                   pending_request=pending[0] if pending else None, team=team)
    return out


class UpgradeRequest(BaseModel):
    plan: str
    note: str = Field(default="", max_length=500)


@router.post("/api/account/upgrade-request", dependencies=[Depends(same_origin)], status_code=201)
def upgrade_request(body: UpgradeRequest, user=Depends(require_user)):
    if body.plan not in PLANS or body.plan == "free":
        raise HTTPException(422, "Gói không hợp lệ.")
    team = team_of(user["id"])
    if body.plan == "business" and (team is None or team[2] != "owner"):
        raise HTTPException(409, "Gói Doanh nghiệp áp dụng cho nhóm: hãy tạo nhóm trước (bạn sẽ là chủ nhóm).")
    with connect() as conn:
        conn.execute("UPDATE upgrade_requests SET status='replaced' WHERE user_id=? AND status='pending'", (user["id"],))
        conn.execute("INSERT INTO upgrade_requests(user_id,plan,note,created_at) VALUES(?,?,?,?)", (user["id"], body.plan, body.note.strip(), int(time.time())))
    return {"ok": True}


# ---- Teams -------------------------------------------------------------------------------------

class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=254)


def _owned_team(user):
    team = team_of(user["id"])
    if team is None or team[2] != "owner":
        raise HTTPException(403, "Chỉ chủ nhóm được thực hiện thao tác này.")
    return team


@router.get("/api/team")
def get_team(user=Depends(require_user)):
    return _team_payload(user["id"])


@router.post("/api/team", dependencies=[Depends(same_origin)], status_code=201)
def create_team(body: TeamCreate, user=Depends(require_user)):
    if team_of(user["id"]):
        raise HTTPException(409, "Bạn đã thuộc một nhóm.")
    now = int(time.time())
    with connect() as conn:
        org_id = conn.execute("INSERT INTO orgs(name,owner_id,created_at) VALUES(?,?,?)", (body.name.strip(), user["id"], now)).lastrowid
        conn.execute("INSERT INTO org_members(org_id,user_id,role,added_at) VALUES(?,?,'owner',?)", (org_id, user["id"], now))
    return _team_payload(user["id"])


@router.post("/api/team/members", dependencies=[Depends(same_origin)], status_code=201)
def add_member(body: MemberAdd, user=Depends(require_user)):
    org_id, _, _, plan, _, _ = _owned_team(user)
    with connect() as conn:
        target = conn.execute("SELECT id FROM users WHERE email=?", (body.email.strip().lower(),)).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM org_members WHERE org_id=?", (org_id,)).fetchone()[0]
    if target is None:
        raise HTTPException(404, "Chưa có tài khoản với email này. Nhờ kỹ sư đăng ký trước rồi thêm lại.")
    if team_of(target[0]):
        raise HTTPException(409, "Người này đã thuộc một nhóm.")
    if count >= PLANS[plan]["seats"]:
        raise HTTPException(402, f"Gói {PLANS[plan]['name']} của nhóm có {PLANS[plan]['seats']} chỗ. Nâng cấp gói Doanh nghiệp để thêm kỹ sư.")
    with connect() as conn:
        conn.execute("INSERT INTO org_members(org_id,user_id,role,added_at) VALUES(?,?,'member',?)", (org_id, target[0], int(time.time())))
    return _team_payload(user["id"])


@router.post("/api/team/members/{member_id}/remove", dependencies=[Depends(same_origin)])
def remove_member(member_id: int, user=Depends(require_user)):
    org_id = _owned_team(user)[0]
    with connect() as conn:
        if conn.execute("DELETE FROM org_members WHERE org_id=? AND user_id=? AND role='member'", (org_id, member_id)).rowcount == 0:
            raise HTTPException(404, "Không tìm thấy thành viên (chủ nhóm không tự xóa mình).")
    return _team_payload(user["id"])


@router.post("/api/team/leave", dependencies=[Depends(same_origin)])
def leave_team(user=Depends(require_user)):
    team = team_of(user["id"])
    if team is None:
        raise HTTPException(404, "Bạn chưa thuộc nhóm nào.")
    with connect() as conn:
        if team[2] == "owner":
            if conn.execute("SELECT COUNT(*) FROM org_members WHERE org_id=?", (team[0],)).fetchone()[0] > 1:
                raise HTTPException(409, "Xóa các thành viên trước khi giải tán nhóm.")
            conn.execute("DELETE FROM org_members WHERE org_id=?", (team[0],))
            conn.execute("DELETE FROM orgs WHERE id=?", (team[0],))
        else:
            conn.execute("DELETE FROM org_members WHERE user_id=?", (user["id"],))
    return {"ok": True}


# ---- Admin -------------------------------------------------------------------------------------

def require_admin(user=Depends(require_user)):
    if not is_admin(user):
        raise HTTPException(403, "Chỉ quản trị viên được truy cập.")
    return user


@router.get("/api/admin/users")
def admin_users(admin=Depends(require_admin)):
    with connect() as conn:
        rows = conn.execute("SELECT id,email,plan_until,role FROM users ORDER BY id DESC LIMIT 500").fetchall()
        requests = {r[0]: {"plan": r[1], "note": r[2]} for r in conn.execute("SELECT user_id,plan,note FROM upgrade_requests WHERE status='pending' ORDER BY id")}
    out = []
    for uid, email, until, role in rows:
        owner, limits, active, label = scope({"id": uid, "email": email})
        team = team_of(uid)
        out.append({"id": uid, "email": email, "role": role, "plan": active, "plan_name": label, "plan_until": until, "limits": limits,
                    "used": usage_for(owner, limits), "pending_request": requests.get(uid),
                    "team": {"id": team[0], "name": team[1], "role": team[2]} if team else None})
    return out


@router.get("/api/admin/teams")
def admin_teams(admin=Depends(require_admin)):
    with connect() as conn:
        rows = conn.execute("SELECT orgs.id, orgs.name, orgs.plan, orgs.plan_until, users.email, "
                            "(SELECT COUNT(*) FROM org_members WHERE org_id=orgs.id) FROM orgs JOIN users ON users.id=orgs.owner_id ORDER BY orgs.id DESC").fetchall()
        requests = {r[0]: {"plan": r[1], "note": r[2]} for r in conn.execute(
            "SELECT orgs.id, upgrade_requests.plan, upgrade_requests.note FROM upgrade_requests JOIN orgs ON orgs.owner_id=upgrade_requests.user_id WHERE upgrade_requests.status='pending'")}
    out = []
    for org_id, name, plan, until, owner_email, members in rows:
        active = _active(plan, until)
        limits = {k: PLANS[active][k] for k in ("projects", "project_window", "ai_reads")}
        out.append({"id": org_id, "name": name, "plan": active, "plan_until": until, "owner": owner_email, "members": members,
                    "seats": PLANS[active]["seats"], "used": usage_for(f"o:{org_id}", limits), "limits": limits, "pending_request": requests.get(org_id)})
    return out


class PlanChange(BaseModel):
    plan: str
    months: int = Field(default=1, ge=1, le=36)


def _until(body: PlanChange):
    if body.plan not in PLANS:
        raise HTTPException(422, "Gói không hợp lệ.")
    return None if body.plan == "free" else int(time.time()) + body.months * WINDOW


@router.post("/api/admin/users/{user_id}/plan", dependencies=[Depends(same_origin)])
def admin_set_plan(user_id: int, body: PlanChange, admin=Depends(require_admin)):
    until = _until(body)
    with connect() as conn:
        if conn.execute("UPDATE users SET plan=?, plan_until=? WHERE id=?", (body.plan, until, user_id)).rowcount == 0:
            raise HTTPException(404, "Không tìm thấy người dùng.")
        conn.execute("UPDATE upgrade_requests SET status='done' WHERE user_id=? AND status='pending'", (user_id,))
    return {"id": user_id, "plan": body.plan, "plan_until": until}


@router.post("/api/admin/teams/{org_id}/plan", dependencies=[Depends(same_origin)])
def admin_set_team_plan(org_id: int, body: PlanChange, admin=Depends(require_admin)):
    until = _until(body)
    with connect() as conn:
        row = conn.execute("SELECT owner_id FROM orgs WHERE id=?", (org_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy nhóm.")
        conn.execute("UPDATE orgs SET plan=?, plan_until=? WHERE id=?", (body.plan, until, org_id))
        conn.execute("UPDATE upgrade_requests SET status='done' WHERE user_id=? AND status='pending'", (row[0],))
    return {"id": org_id, "plan": body.plan, "plan_until": until}
