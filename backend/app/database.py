from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "solaropt.db"


@contextmanager
def connect():
    path = Path(os.getenv("SOLAROPT_DB_PATH") or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS project_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            version_label TEXT NOT NULL,
            reason TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("CREATE TABLE IF NOT EXISTS auth_attempts (client TEXT PRIMARY KEY, window_start INTEGER NOT NULL, attempts INTEGER NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at INTEGER NOT NULL)")
        if "user_id" not in {row[1] for row in conn.execute("PRAGMA table_info(project_versions)")}:
            conn.execute("ALTER TABLE project_versions ADD COLUMN user_id INTEGER REFERENCES users(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS versions_owner_project ON project_versions(user_id, project_name, id)")
        # Freemium plans (app/billing.py): plan per user, usage events, upgrade requests.
        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "plan" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
        if "plan_until" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN plan_until INTEGER")
        if "role" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.execute("CREATE TABLE IF NOT EXISTS orgs (id INTEGER PRIMARY KEY, name TEXT NOT NULL, owner_id INTEGER NOT NULL REFERENCES users(id), plan TEXT NOT NULL DEFAULT 'free', plan_until INTEGER, created_at INTEGER NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS org_members (org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE, user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE, role TEXT NOT NULL, added_at INTEGER NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS usage_events (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, project_key TEXT, created_at INTEGER NOT NULL)")
        conn.execute("CREATE INDEX IF NOT EXISTS usage_owner_kind ON usage_events(owner, kind, created_at)")
        conn.execute("CREATE TABLE IF NOT EXISTS upgrade_requests (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, plan TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', created_at INTEGER NOT NULL)")
        conn.commit()


def save_version(project_name: str, version_label: str, reason: str, payload: dict[str, Any], user_id: int | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO project_versions(project_name,version_label,reason,payload_json,user_id) VALUES(?,?,?,?,?)",
            (project_name, version_label, reason, json.dumps(payload, ensure_ascii=False), user_id),
        )
        conn.commit()
        return int(cur.lastrowid)


def _owners(user_id: int | list[int] | None) -> list[int | None]:
    return list(user_id) if isinstance(user_id, list) else [user_id]


def list_versions(project_name: str | None, user_id: int | list[int] | None = None) -> list[dict[str, Any]]:
    """user_id: one owner, or the member ids of a team that shares history."""
    owners = _owners(user_id)
    marks = ",".join("?" * len(owners))
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT id,project_name,version_label,reason,payload_json,created_at FROM project_versions WHERE (? IS NULL OR project_name=?) AND (user_id IN ({marks}) OR (? IS NULL AND user_id IS NULL)) ORDER BY id DESC LIMIT 50",
            (project_name, project_name, *owners, owners[0] if len(owners) == 1 else 0),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["payload"] = json.loads(item.pop("payload_json"))
        evidence=item['payload'].get('evidence')
        item['has_evidence']=bool(evidence and (evidence.get('source_image') or evidence.get('reference_image')))
        if evidence:
            item['payload']['evidence']={**evidence,'source_image':None,'reference_image':None}
        out.append(item)
    return out


def get_version(project_name:str,version_id:int,user_id:int | list[int] | None = None):
    owners=_owners(user_id);marks=",".join("?"*len(owners))
    with connect() as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute(f'SELECT id,project_name,version_label,reason,payload_json,created_at FROM project_versions WHERE project_name=? AND id=? AND (user_id IN ({marks}) OR (? IS NULL AND user_id IS NULL))',(project_name,version_id,*owners,owners[0] if len(owners)==1 else 0)).fetchone()
    if row is None:return None
    item=dict(row);item['payload']=json.loads(item.pop('payload_json'))
    return item
