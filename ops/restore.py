"""Restore a verified backup. Stop backend and backup services before invoking."""
import argparse
import os
from pathlib import Path
import sqlite3
from contextlib import closing


def restore(source: Path, destination: Path):
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src:
        if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Invalid backup")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Restore integrity check failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    parser.add_argument("--offline", action="store_true", required=True)
    args = parser.parse_args()
    restore(args.backup, Path(os.getenv("SOLAROPT_DB_PATH", "backend/solaropt.db")))
    print("Restore verified")
