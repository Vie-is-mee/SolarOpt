"""Project-based plans, paid project storage, team accounts and the admin console.

A plan sells a number of projects per billing cycle: the single-project plan lasts 30 days from activation, a yearly
plan resets every 365 days, and nothing carries over. One "project" use = the first successful layout computation of a
project (its name at its location); on a paid plan, working on it again within 12 months is free, because a site job
outlasts a cycle and must not be charged twice.

Each project a customer uses is stored while the cycle that counted it lasts (a trial project for a week). After
that an active yearly plan keeps as many stored projects free as it sells; the others are charged per month by the
tier of STORAGE_TIERS their number falls in. Unpaid data stays visible for the grace days, is then hidden from the
account, and scripts/purge_expired_projects.py deletes it.

Payment is not integrated: users send a request and an admin activates the plan or the storage. Admins
(users.role='admin', granted only on the server) have no limits and their projects are never expired. A team with an
active paid plan pools its members' usage and shares project history.
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.auth import client_ip as _client_ip, optional_user, require_user, same_origin
from app.database import connect

DAY = 24 * 60 * 60
MONTH = 30 * DAY
YEAR = 365 * DAY
PERIOD_SECONDS = {"month": MONTH, "year": YEAR}
TRIAL_KEEP_DAYS = 7
STORAGE_TIERS = ((8, 299_000), (24, 599_000), (60, 899_000), (150, 1_490_000))   # up to N stored projects, đ/month
STORAGE_MONTHS_FREE_PER_YEAR = 2
UNLIMITED = {"projects": None, "ai_reads": None, "chat": None}
LIMIT_KEYS = ("projects", "ai_reads", "chat")
# Prices of 08/11/2026; competitor comparison and cost model: docs/GIA_VA_CHI_PHI_THUONG_MAI.md section 11.
# AI allowances are per cycle and sized at 20 image reads and 300 assistant answers per project.
PLANS = {
    "free": {"name": "Dùng thử", "price_vnd": 0, "period": None, "projects": 1, "ai_reads": 5, "chat": 30, "seats": 1,
             "features": ["1 dự án để dùng thử", "5 lượt AI đọc ảnh, 30 câu hỏi trợ lý AI", f"Dữ liệu giữ {TRIAL_KEEP_DAYS} ngày"]},
    "single": {"name": "Dự án lẻ", "price_vnd": 5_990_000, "period": "month", "projects": 1, "ai_reads": 20, "chat": 300, "seats": 1,
               "features": ["1 dự án trong 30 ngày", "20 lượt AI đọc ảnh, 300 câu hỏi trợ lý AI", "1 kỹ sư", "Hỗ trợ tới 3 giờ"]},
    "start": {"name": "Start", "price_vnd": 17_900_000, "period": "year", "projects": 8, "ai_reads": 160, "chat": 2400, "seats": 2,
              "features": ["8 dự án trong 12 tháng", "160 lượt AI đọc ảnh, 2.400 câu hỏi trợ lý AI", "Nhóm tới 2 kỹ sư", "Hỗ trợ tới 6 giờ mỗi năm", "Lưu miễn phí 8 dự án khi còn gói"]},
    "team": {"name": "Team", "price_vnd": 34_900_000, "period": "year", "projects": 24, "ai_reads": 480, "chat": 7200, "seats": 5,
             "features": ["24 dự án trong 12 tháng", "480 lượt AI đọc ảnh, 7.200 câu hỏi trợ lý AI", "Nhóm tới 5 kỹ sư", "Hỗ trợ tới 18 giờ mỗi năm", "Lưu miễn phí 24 dự án khi còn gói"]},
    "pro": {"name": "Pro", "price_vnd": 54_900_000, "period": "year", "projects": 60, "ai_reads": 1200, "chat": 18000, "seats": 10,
            "features": ["60 dự án trong 12 tháng", "1.200 lượt AI đọc ảnh, 18.000 câu hỏi trợ lý AI", "Nhóm tới 10 kỹ sư", "Hỗ trợ tới 30 giờ mỗi năm", "Lưu miễn phí 60 dự án khi còn gói"]},
    # Plans of 07/11/2026: no longer sold; an account that holds one keeps its limits until it ends.
    "month_1": {"name": "Tháng · 1 dự án", "price_vnd": 5_990_000, "period": "month", "projects": 1, "ai_reads": 20, "chat": 300, "seats": 3, "retired": True},
    "month_2": {"name": "Tháng · 2 dự án", "price_vnd": 7_990_000, "period": "month", "projects": 2, "ai_reads": 40, "chat": 600, "seats": 5, "retired": True},
    "year_3": {"name": "Năm · 3 dự án", "price_vnd": 15_000_000, "period": "year", "projects": 3, "ai_reads": 60, "chat": 900, "seats": 5, "retired": True},
    "year_7": {"name": "Năm · 7 dự án", "price_vnd": 30_000_000, "period": "year", "projects": 7, "ai_reads": 140, "chat": 2100, "seats": 10, "retired": True},
}
STATE_LABELS = {"included": "Trong thời hạn gói", "paid": "Đã trả phí lưu trữ", "grace": "Quá hạn, sắp xóa", "expired": "Đã hết hạn, chờ xóa",
                "purged": "Đã xóa"}

router = APIRouter(tags=["billing"])


def guest_daily_projects() -> int:
    return max(0, int(os.getenv("SOLAROPT_GUEST_DAILY_PROJECTS", "2")))


def on_sale(plan: str) -> bool:
    return plan in PLANS and not PLANS[plan].get("retired")


def storage_grace_days() -> int:
    return max(0, int(os.getenv("SOLAROPT_STORAGE_GRACE_DAYS", "30")))


def storage_fee(projects: int) -> int | None:
    """Monthly fee for keeping this many projects; None above the last tier, which is quoted by hand."""
    return 0 if projects <= 0 else next((fee for top, fee in STORAGE_TIERS if projects <= top), None)


def storage_bill(projects: int, months: int) -> int | None:
    fee = storage_fee(projects)
    return None if fee is None else fee * (months - STORAGE_MONTHS_FREE_PER_YEAR * (months // 12))


def project_key(name: str, latitude: float | None = None, longitude: float | None = None) -> str:
    """Name plus location (about 1 km), so one paid project cannot be reused for roofs in other places by keeping its name."""
    key = " ".join(name.strip().lower().split())[:120] or "dự án"
    return key if latitude is None or longitude is None else f"{key} @{latitude:.2f},{longitude:.2f}"


def client_ip(request: Request) -> str:
    return _client_ip(request)


def _active(plan, until) -> str:
    return plan if plan in PLANS and (plan == "free" or (until is not None and until > time.time())) else "free"


def is_admin(user) -> bool:
    if not user:
        return False
    with connect() as conn:
        row = conn.execute("SELECT role FROM users WHERE id=?", (user["id"],)).fetchone()
    return bool(row) and row[0] == "admin"


def team_of(user_id: int):
    """(org_id, name, member role, active plan, plan_until, owner_id, plan_started) or None."""
    with connect() as conn:
        row = conn.execute("SELECT orgs.id, orgs.name, org_members.role, orgs.plan, orgs.plan_until, orgs.owner_id, orgs.plan_started FROM org_members "
                           "JOIN orgs ON orgs.id=org_members.org_id WHERE org_members.user_id=?", (user_id,)).fetchone()
    return None if row is None else (row[0], row[1], row[2], _active(row[3], row[4]), row[4], row[5], row[6])


def team_member_ids(user_id: int) -> list[int]:
    """Users whose project history this user may read: the whole team when its plan is paid."""
    team = team_of(user_id)
    if team is None or team[3] == "free":
        return [user_id]
    with connect() as conn:
        return [r[0] for r in conn.execute("SELECT user_id FROM org_members WHERE org_id=?", (team[0],))]


def current_plan(user_id: int) -> tuple[str, int | None, int | None]:
    """(active plan, started, until) of a user's own plan."""
    with connect() as conn:
        row = conn.execute("SELECT plan, plan_started, plan_until FROM users WHERE id=?", (user_id,)).fetchone()
    if row is None or _active(row[0], row[2]) == "free":
        return "free", None, None
    return row[0], row[1], row[2]


def _limits(plan_id: str, started, until, now: int) -> dict:
    """Allowances of the current cycle: a paid cycle starts at activation and repeats every month or year; the trial never resets."""
    plan = PLANS[plan_id]
    if plan["period"] is None:
        since, end = 0, None
    else:
        length = PERIOD_SECONDS[plan["period"]]
        started = started or (until - length if until else now)
        since = started + max(0, now - started) // length * length
        end = min(since + length, until) if until else since + length
    return {**{k: plan[k] for k in LIMIT_KEYS}, "since": since, "until": end}


def scope(user):
    """(owner key, limits, plan id, label). Admins are unlimited; a paid team pools usage."""
    now = int(time.time())
    if user is None:
        return None, {"projects": guest_daily_projects(), "ai_reads": 0, "chat": 0, "since": now - DAY, "until": None}, "guest", "Khách"
    if is_admin(user):
        return f"u:{user['id']}", {**UNLIMITED, "since": 0, "until": None}, "admin", "Quản trị viên"
    team = team_of(user["id"])
    if team and team[3] != "free":
        return f"o:{team[0]}", _limits(team[3], team[6], team[4], now), team[3], f"{PLANS[team[3]]['name']} · {team[1]}"
    plan_id, started, until = current_plan(user["id"])
    return f"u:{user['id']}", _limits(plan_id, started, until, now), plan_id, PLANS[plan_id]["name"]


def usage_for(owner: str, limits: dict) -> dict:
    since = limits["since"]
    with connect() as conn:
        projects = conn.execute("SELECT COUNT(DISTINCT project_key) FROM usage_events WHERE owner=? AND kind='project' AND created_at>=?",
                                (owner, since)).fetchone()[0]
        ai = conn.execute("SELECT COUNT(*) FROM usage_events WHERE owner=? AND kind='ai' AND created_at>=?", (owner, since)).fetchone()[0]
        chat = conn.execute("SELECT COUNT(*) FROM usage_events WHERE owner=? AND kind='chat' AND created_at>=?", (owner, since)).fetchone()[0]
    return {"projects": projects, "ai_reads": ai, "chat": chat}


def project_ref(user, config) -> tuple[str | None, str]:
    """(owner, project key) under which a signed-in user's saved versions are stored and billed."""
    owner = scope(user)[0] if user else None
    return owner, project_key(config.project_name, config.latitude, config.longitude)


class ProjectQuota:
    """Check before computing, record after success; the same project inside the cycle is free."""

    def __init__(self, request: Request, user, config):
        self.owner, self.limits, self.plan, _ = scope(user)
        if user is None:
            self.owner = f"ip:{client_ip(request)}"
        self.name = config.project_name.strip()[:120] or "Dự án"
        self.key, self.user = project_key(config.project_name, config.latitude, config.longitude), user

    def counted(self) -> bool:
        paid = self.limits["until"] is not None
        since = int(time.time()) - YEAR if paid else self.limits["since"]
        with connect() as conn:
            return conn.execute("SELECT 1 FROM usage_events WHERE owner=? AND kind='project' AND project_key=? AND created_at>=? LIMIT 1",
                                (self.owner, self.key, since)).fetchone() is not None

    def check(self) -> None:
        if self.limits["projects"] is None or self.counted():
            return
        if usage_for(self.owner, self.limits)["projects"] >= self.limits["projects"]:
            if self.user is None:
                raise HTTPException(402, f"Chế độ khách được thử {self.limits['projects']} dự án mỗi ngày. Đăng ký để dùng thử có AI và lưu dữ liệu {TRIAL_KEEP_DAYS} ngày.")
            raise HTTPException(402, f"Đã dùng hết {self.limits['projects']} dự án của gói trong chu kỳ này. Mua thêm gói hoặc mở lại dự án đã tính trong 12 tháng qua.")

    def record(self) -> None:
        if not self.counted():
            with connect() as conn:
                conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,?,?)", (self.owner, "project", self.key, int(time.time())))
        if self.user is not None and self.plan != "admin":
            _cover(self.owner, self.key, self.name, self.limits)


def _cover(owner: str, key: str, name: str, limits: dict) -> None:
    """Data of a project is kept until the end of the paid cycle that used it; a trial project for a week from first use."""
    now = int(time.time())
    with connect() as conn:
        if limits["until"] is None:
            conn.execute("INSERT OR IGNORE INTO project_storage(owner,project_key,project_name,first_used,covered_until) VALUES(?,?,?,?,?)",
                         (owner, key, name, now, now + TRIAL_KEEP_DAYS * DAY))
        else:
            conn.execute("INSERT INTO project_storage(owner,project_key,project_name,first_used,covered_until) VALUES(?,?,?,?,?) "
                         "ON CONFLICT(owner,project_key) DO UPDATE SET covered_until=MAX(covered_until, excluded.covered_until), "
                         "project_name=excluded.project_name, purged_at=NULL", (owner, key, name, now, limits["until"]))


def _retention(covered_until: int, storage_until, purged_at, now: int) -> dict:
    keep_until = max(covered_until, storage_until or 0)
    delete_after = keep_until + storage_grace_days() * DAY
    state = ("purged" if purged_at else "included" if now <= covered_until else "paid" if now <= keep_until
             else "grace" if now <= delete_after else "expired")
    return {"keep_until": keep_until, "delete_after": delete_after, "state": state, "state_label": STATE_LABELS[state]}


def _free_slots(owner: str) -> list[int]:
    """[stored projects an active yearly plan keeps free, when that plan ends]."""
    kind, _, key = owner.partition(":")
    if kind not in ("u", "o"):
        return [0, 0]
    with connect() as conn:
        row = conn.execute(f"SELECT plan, plan_until FROM {'users' if kind == 'u' else 'orgs'} WHERE id=?", (key,)).fetchone()
    if row is None or _active(row[0], row[1]) == "free" or PLANS[row[0]]["period"] != "year":
        return [0, 0]
    return [PLANS[row[0]]["projects"], row[1]]


def storage_rows(owners: list[str] | None = None) -> list[dict]:
    """Stored projects with their retention state, newest first; owners=None lists everyone (admin)."""
    now = int(time.time())
    where, args = ("", ()) if owners is None else (f"WHERE owner IN ({','.join('?' * len(owners))})", tuple(owners))
    with connect() as conn:
        rows = conn.execute(f"SELECT owner, project_key, project_name, first_used, covered_until, storage_until, purged_at FROM project_storage {where} "
                            "ORDER BY first_used DESC LIMIT 1000", args).fetchall()
    out, slots = [], {}
    for o, k, n, f, c, s, p in rows:
        retention = _retention(c, s, p, now)
        if retention["state"] in ("grace", "expired"):
            free = slots.setdefault(o, _free_slots(o))
            if free[0] > 0:
                free[0] -= 1
                retention = _retention(free[1], s, p, now)
        out.append({"owner": o, "project_key": k, "project_name": n, "first_used": f, "covered_until": c, "storage_until": s, "purged_at": p, **retention})
    return out


def storage_accounts(owners: list[str] | None = None) -> list[dict]:
    """One line per owner with projects that are outside every plan: how many, their tier fee, any open request."""
    counts = {}
    for r in storage_rows(owners):
        if r["state"] in ("paid", "grace", "expired"):
            counts[r["owner"]] = counts.get(r["owner"], 0) + 1
    with connect() as conn:
        pending = dict(conn.execute("SELECT owner, SUM(months) FROM storage_requests WHERE status='pending' GROUP BY owner").fetchall())
    return [{"owner": o, "projects": n, "fee_vnd_month": storage_fee(n), "pending_months": pending.get(o)} for o, n in counts.items()]


def hidden_projects(owners: set[str]) -> set[tuple[str, str]]:
    """(owner, key) of projects whose data is past the grace days: no longer shown, waiting for the purge."""
    return {(r["owner"], r["project_key"]) for r in storage_rows(sorted(owners)) if r["state"] in ("expired", "purged")} if owners else set()


def visible_versions(versions: list[dict]) -> list[dict]:
    hidden = hidden_projects({v["owner"] for v in versions if v.get("owner")})
    return [v for v in versions if (v.get("owner"), v.get("project_key")) not in hidden]


def check_ai(user) -> None:
    owner, limits, _, _ = scope(user)
    if limits["ai_reads"] is not None and usage_for(owner, limits)["ai_reads"] >= limits["ai_reads"]:
        raise HTTPException(402, f"Đã dùng hết {limits['ai_reads']} lượt AI đọc ảnh của gói trong chu kỳ này. Mua thêm gói hoặc nhập số liệu thủ công.")


def record_ai(user) -> None:
    owner = scope(user)[0]
    with connect() as conn:
        conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,NULL,?)", (owner, "ai", int(time.time())))


def chat_block(user) -> str | None:
    """Why the assistant may not call the AI model for this user, or None when it may.
    Guests and exhausted plans still get answers, from the rule-based reader, so no paid call leaks."""
    if user is None:
        return "Đăng nhập để dùng trợ lý AI; câu trả lời dưới đây do bộ quy tắc của SolarOpt lập từ số liệu đã tính."
    owner, limits, _, _ = scope(user)
    if limits["chat"] is not None and usage_for(owner, limits)["chat"] >= limits["chat"]:
        return f"Đã dùng hết {limits['chat']} câu hỏi trợ lý AI của gói trong chu kỳ này; câu trả lời dưới đây do bộ quy tắc lập. Mua thêm gói để dùng tiếp AI."
    return None


def record_chat(user) -> None:
    owner = scope(user)[0]
    with connect() as conn:
        conn.execute("INSERT INTO usage_events(owner,kind,project_key,created_at) VALUES(?,?,NULL,?)", (owner, "chat", int(time.time())))


def _catalog():
    return {k: {key: v[key] for key in ("name", "price_vnd", "period", "projects", "ai_reads", "chat", "features", "seats")}
            | {"price_per_project_vnd": round(v["price_vnd"] / v["projects"]) if v["price_vnd"] else 0} for k, v in PLANS.items() if on_sale(k)}


def _team_payload(user_id: int):
    team = team_of(user_id)
    if team is None:
        return None
    org_id, name, role, plan, until, _, _ = team
    with connect() as conn:
        members = [{"id": r[0], "email": r[1], "role": r[2]} for r in conn.execute(
            "SELECT users.id, users.email, org_members.role FROM org_members JOIN users ON users.id=org_members.user_id "
            "WHERE org_id=? ORDER BY org_members.role DESC, users.email", (org_id,))]
    return {"id": org_id, "name": name, "role": role, "plan": plan, "plan_name": PLANS[plan]["name"],
            "plan_until": until if plan != "free" else None, "seats": PLANS[plan]["seats"], "members": members}


def _storage_terms() -> dict:
    return {"tiers": [{"max_projects": top, "fee_vnd_month": fee} for top, fee in STORAGE_TIERS], "months_free_per_year": STORAGE_MONTHS_FREE_PER_YEAR,
            "grace_days": storage_grace_days(), "trial_keep_days": TRIAL_KEEP_DAYS}


@router.get("/api/account/usage")
def account_usage(request: Request, user=Depends(optional_user)):
    owner, limits, plan, label = scope(user)
    if user is None:
        owner = f"ip:{client_ip(request)}"
    out = {"plan": plan, "plan_name": label, "limits": {**{k: limits[k] for k in LIMIT_KEYS}, "cycle_end": limits["until"]},
           "used": usage_for(owner, limits), "plans": _catalog(), "storage_terms": _storage_terms(), "storage_due": 0,
           "is_admin": plan == "admin", "plan_until": None, "pending_request": None, "team": None}
    if user is not None:
        with connect() as conn:
            until = conn.execute("SELECT plan_until FROM users WHERE id=?", (user["id"],)).fetchone()[0]
            pending = conn.execute("SELECT plan FROM upgrade_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (user["id"],)).fetchone()
        team = _team_payload(user["id"])
        shared = team is not None and team["plan"] != "free" and plan != "admin"
        out.update(plan_until=team["plan_until"] if shared else (until if plan in PLANS and plan != "free" else None),
                   pending_request=pending[0] if pending else None, team=team,
                   storage_due=sum(r["state"] == "grace" for r in storage_rows(_storage_owners(user))))
    return out


class UpgradeRequest(BaseModel):
    plan: str
    note: str = Field(default="", max_length=500)


@router.post("/api/account/upgrade-request", dependencies=[Depends(same_origin)], status_code=201)
def upgrade_request(body: UpgradeRequest, user=Depends(require_user)):
    if not on_sale(body.plan) or body.plan == "free":
        raise HTTPException(422, "Gói không hợp lệ.")
    with connect() as conn:
        conn.execute("UPDATE upgrade_requests SET status='replaced' WHERE user_id=? AND status='pending'", (user["id"],))
        conn.execute("INSERT INTO upgrade_requests(user_id,plan,note,created_at) VALUES(?,?,?,?)", (user["id"], body.plan, body.note.strip(), int(time.time())))
    return {"ok": True}


# ---- Project storage ---------------------------------------------------------------------------

def _storage_owners(user) -> list[str]:
    """The current billing owner and the user's own key (projects made before joining a team stay there)."""
    return sorted({scope(user)[0], f"u:{user['id']}"})


@router.get("/api/account/storage")
def account_storage(user=Depends(require_user)):
    if is_admin(user):
        return {**_storage_terms(), "unlimited": True, "projects": [], "billable": 0, "fee_vnd_month": 0, "pending_months": None}
    owners = _storage_owners(user)
    accounts = storage_accounts(owners)
    fees = [a["fee_vnd_month"] for a in accounts]
    return {**_storage_terms(), "unlimited": False, "projects": storage_rows(owners), "billable": sum(a["projects"] for a in accounts),
            "fee_vnd_month": None if None in fees else sum(fees), "pending_months": next((a["pending_months"] for a in accounts if a["pending_months"]), None)}


class StorageRequest(BaseModel):
    months: int = Field(default=1, ge=1, le=24)


@router.post("/api/account/storage-request", dependencies=[Depends(same_origin)], status_code=201)
def storage_request(body: StorageRequest, user=Depends(require_user)):
    accounts = storage_accounts(_storage_owners(user))
    if not accounts:
        raise HTTPException(409, "Chưa có dự án nào cần đóng phí lưu trữ.")
    with connect() as conn:
        for a in accounts:
            conn.execute("UPDATE storage_requests SET status='replaced' WHERE owner=? AND status='pending'", (a["owner"],))
            conn.execute("INSERT INTO storage_requests(owner,project_key,months,user_id,status,created_at) VALUES(?,'*',?,?,'pending',?)",
                         (a["owner"], body.months, user["id"], int(time.time())))
    bills = [storage_bill(a["projects"], body.months) for a in accounts]
    return {"ok": True, "fee_vnd": None if None in bills else sum(bills)}


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
    org_id, _, _, plan, _, _, _ = _owned_team(user)
    with connect() as conn:
        target = conn.execute("SELECT id FROM users WHERE email=?", (body.email.strip().lower(),)).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM org_members WHERE org_id=?", (org_id,)).fetchone()[0]
    if target is None:
        raise HTTPException(404, "Chưa có tài khoản với email này. Nhờ kỹ sư đăng ký trước rồi thêm lại.")
    if team_of(target[0]):
        raise HTTPException(409, "Người này đã thuộc một nhóm.")
    if count >= PLANS[plan]["seats"]:
        raise HTTPException(402, f"Gói {PLANS[plan]['name']} của nhóm có {PLANS[plan]['seats']} chỗ. Chọn gói nhiều chỗ hơn để thêm kỹ sư.")
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
        out.append({"id": uid, "email": email, "role": role, "plan": active, "plan_name": label, "plan_until": until,
                    "limits": {k: limits[k] for k in LIMIT_KEYS}, "used": usage_for(owner, limits), "pending_request": requests.get(uid),
                    "team": {"id": team[0], "name": team[1], "role": team[2]} if team else None})
    return out


@router.get("/api/admin/teams")
def admin_teams(admin=Depends(require_admin)):
    now = int(time.time())
    with connect() as conn:
        rows = conn.execute("SELECT orgs.id, orgs.name, orgs.plan, orgs.plan_until, orgs.plan_started, users.email, "
                            "(SELECT COUNT(*) FROM org_members WHERE org_id=orgs.id) FROM orgs JOIN users ON users.id=orgs.owner_id ORDER BY orgs.id DESC").fetchall()
        requests = {r[0]: {"plan": r[1], "note": r[2]} for r in conn.execute(
            "SELECT orgs.id, upgrade_requests.plan, upgrade_requests.note FROM upgrade_requests JOIN orgs ON orgs.owner_id=upgrade_requests.user_id WHERE upgrade_requests.status='pending'")}
    out = []
    for org_id, name, plan, until, started, owner_email, members in rows:
        active = _active(plan, until)
        limits = _limits(active, started if active != "free" else None, until if active != "free" else None, now)
        out.append({"id": org_id, "name": name, "plan": active, "plan_name": PLANS[active]["name"], "plan_until": until, "owner": owner_email, "members": members,
                    "seats": PLANS[active]["seats"], "used": usage_for(f"o:{org_id}", limits), "limits": {k: limits[k] for k in LIMIT_KEYS},
                    "pending_request": requests.get(org_id)})
    return out


@router.get("/api/admin/storage")
def admin_storage(admin=Depends(require_admin)):
    with connect() as conn:
        users = {f"u:{r[0]}": r[1] for r in conn.execute("SELECT id, email FROM users")}
        teams = {f"o:{r[0]}": f"Nhóm {r[1]}" for r in conn.execute("SELECT id, name FROM orgs")}
    label = lambda r: r | {"owner_label": users.get(r["owner"]) or teams.get(r["owner"]) or r["owner"]}
    return {**_storage_terms(), "projects": [label(r) for r in storage_rows()], "accounts": [label(a) for a in storage_accounts()]}


class StorageExtend(BaseModel):
    owner: str = Field(min_length=3, max_length=40)
    months: int = Field(default=1, ge=1, le=36)


@router.post("/api/admin/storage", dependencies=[Depends(same_origin)])
def admin_extend_storage(body: StorageExtend, admin=Depends(require_admin)):
    """Record a paid storage extension for an owner: each project runs from the later of today and its end of retention."""
    rows = [r for r in storage_rows([body.owner]) if r["state"] in ("paid", "grace", "expired")]
    if not rows:
        raise HTTPException(404, "Không có dự án nào cần gia hạn.")
    now = int(time.time())
    with connect() as conn:
        for r in rows:
            conn.execute("UPDATE project_storage SET storage_until=? WHERE owner=? AND project_key=?",
                         (max(now, r["keep_until"]) + body.months * MONTH, body.owner, r["project_key"]))
        conn.execute("UPDATE storage_requests SET status='done' WHERE owner=? AND status='pending'", (body.owner,))
    return {"owner": body.owner, "projects": len(rows), "storage_until": max(now, max(r["keep_until"] for r in rows)) + body.months * MONTH}


class PlanChange(BaseModel):
    plan: str
    periods: int = Field(default=1, ge=1, le=36)   # months for a monthly plan, years for a yearly one


def _until(body: PlanChange) -> tuple[int | None, int | None]:
    """(started, until) for a plan activated now."""
    if not on_sale(body.plan):
        raise HTTPException(422, "Gói không hợp lệ.")
    period = PLANS[body.plan]["period"]
    if period is None:
        return None, None
    now = int(time.time())
    return now, now + body.periods * PERIOD_SECONDS[period]


@router.post("/api/admin/users/{user_id}/plan", dependencies=[Depends(same_origin)])
def admin_set_plan(user_id: int, body: PlanChange, admin=Depends(require_admin)):
    started, until = _until(body)
    with connect() as conn:
        if conn.execute("UPDATE users SET plan=?, plan_started=?, plan_until=? WHERE id=?", (body.plan, started, until, user_id)).rowcount == 0:
            raise HTTPException(404, "Không tìm thấy người dùng.")
        conn.execute("UPDATE upgrade_requests SET status='done' WHERE user_id=? AND status='pending'", (user_id,))
    return {"id": user_id, "plan": body.plan, "plan_until": until}


@router.post("/api/admin/teams/{org_id}/plan", dependencies=[Depends(same_origin)])
def admin_set_team_plan(org_id: int, body: PlanChange, admin=Depends(require_admin)):
    started, until = _until(body)
    with connect() as conn:
        row = conn.execute("SELECT owner_id FROM orgs WHERE id=?", (org_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy nhóm.")
        conn.execute("UPDATE orgs SET plan=?, plan_started=?, plan_until=? WHERE id=?", (body.plan, started, until, org_id))
        conn.execute("UPDATE upgrade_requests SET status='done' WHERE user_id=? AND status='pending'", (row[0],))
    return {"id": org_id, "plan": body.plan, "plan_until": until}
