"""Small SQLite-backed accounts and revocable, opaque cookie sessions."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from app.database import connect

router = APIRouter(prefix="/api/auth", tags=["accounts"])
COOKIE = "solaropt_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if value.count("@") != 1 or not all(value.split("@")) or any(c.isspace() for c in value):
            raise ValueError("Email không hợp lệ.")
        return value


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${digest}"


DUMMY_HASH = password_hash("dummy-account-password")


def optional_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    row = None
    if token and len(token) <= 128:
        with connect() as conn:
            row = conn.execute(
                "SELECT users.id, users.email FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?",
                (hashlib.sha256(token.encode()).hexdigest(), int(time.time())),
            ).fetchone()
    user = {"id": row[0], "email": row[1]} if row else None
    expected = request.headers.get("X-SolarOpt-User")
    actual = str(user["id"]) if user else "guest"
    if token and user is None:
        request.state.invalid_session = True
    if (token and user is None) or (expected is not None and expected != actual):
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn hoặc tài khoản đã thay đổi. Vui lòng đăng nhập lại.")
    return user


def require_user(user=Depends(optional_user)) -> dict:
    if user is None:
        raise HTTPException(401, "Vui lòng đăng nhập.")
    return user


def same_origin(request: Request) -> None:
    # Browser cross-origin forms cannot send this header. CORS controls allowed origins.
    if request.headers.get("X-SolarOpt-Request") != "1":
        raise HTTPException(403, "Thiếu xác nhận yêu cầu.")


def throttle(request: Request) -> None:
    now = int(time.time())
    client = request.client.host if request.client else "unknown"
    with connect() as conn:
        conn.execute("DELETE FROM auth_attempts WHERE window_start<=?", (now - 900,))
        conn.execute("INSERT INTO auth_attempts VALUES(?,?,1) ON CONFLICT(client) DO UPDATE SET attempts=attempts+1", (client, now))
        attempts = conn.execute("SELECT attempts FROM auth_attempts WHERE client=?", (client,)).fetchone()[0]
    if attempts > 30:
        raise HTTPException(429, "Quá nhiều lần thử. Vui lòng thử lại sau 15 phút.", headers={"Retry-After": "900"})


def create_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        conn.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, now + SESSION_SECONDS))
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv("SOLAROPT_COOKIE_SECURE", "false").lower() == "true", samesite="lax", max_age=SESSION_SECONDS, path="/api")


@router.post("/register", dependencies=[Depends(same_origin), Depends(throttle)], status_code=201)
def register(body: Credentials, response: Response):
    hashed = password_hash(body.password)
    try:
        with connect() as conn:
            cursor = conn.execute("INSERT INTO users(email,password_hash) VALUES(?,?)", (body.email, hashed))
            user_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Email đã được sử dụng.")
    create_session(response, user_id)
    return {"id": user_id, "email": body.email}


@router.post("/login", dependencies=[Depends(same_origin), Depends(throttle)])
def login(body: Credentials, response: Response):
    with connect() as conn:
        row = conn.execute("SELECT id,email,password_hash FROM users WHERE email=?", (body.email,)).fetchone()
    stored = row[2] if row else DUMMY_HASH
    if not hmac.compare_digest(stored, password_hash(body.password, stored.split("$")[1])) or row is None:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng.")
    create_session(response, row[0])
    return {"id": row[0], "email": row[1]}


@router.get("/me")
def me(user=Depends(require_user)):
    return user


@router.post("/logout", dependencies=[Depends(same_origin)])
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE, "")
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE, path="/api")
    return {"ok": True}
