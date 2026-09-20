from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "solaropt.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
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
        conn.commit()


def save_version(project_name: str, version_label: str, reason: str, payload: dict[str, Any]) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO project_versions(project_name,version_label,reason,payload_json) VALUES(?,?,?,?)",
            (project_name, version_label, reason, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_versions(project_name: str) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id,project_name,version_label,reason,payload_json,created_at FROM project_versions WHERE project_name=? ORDER BY id DESC",
            (project_name,),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["payload"] = json.loads(item.pop("payload_json"))
        out.append(item)
    return out
