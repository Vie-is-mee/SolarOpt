"""Online SQLite backup with integrity verification; source is never copied raw."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import time
from contextlib import closing


def backup(source: Path, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (datetime.now(timezone.utc).strftime("solaropt-%Y%m%dT%H%M%S%fZ") + ".db")
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Backup integrity check failed")
    # Retain the newest 14 successful snapshots, all inside the backup directory.
    for old in sorted(directory.glob("solaropt-*.db"), reverse=True)[14:]:
        old.unlink()
    print(f"Backup verified: {target.name}", flush=True)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            backup(Path(os.getenv("SOLAROPT_DB_PATH", "backend/solaropt.db")), Path(os.getenv("SOLAROPT_BACKUP_DIR", "backups")))
        except Exception as exc:
            print(f"BACKUP FAILED: {type(exc).__name__}", flush=True)
            if not args.loop:
                raise
        if not args.loop:
            break
        time.sleep(86400)
