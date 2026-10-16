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
        conn.commit()


def save_version(project_name: str, version_label: str, reason: str, payload: dict[str, Any]) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO project_versions(project_name,version_label,reason,payload_json) VALUES(?,?,?,?)",
            (project_name, version_label, reason, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_versions(project_name: str) -> list[dict[str, Any]]:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id,project_name,version_label,reason,payload_json,created_at FROM project_versions WHERE project_name=? ORDER BY id DESC LIMIT 50",
            (project_name,),
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


def get_version(project_name:str,version_id:int):
    with connect() as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT id,project_name,version_label,reason,payload_json,created_at FROM project_versions WHERE project_name=? AND id=?',(project_name,version_id)).fetchone()
    if row is None:return None
    item=dict(row);item['payload']=json.loads(item.pop('payload_json'))
    return item
