"""Delete the saved versions of projects whose paid storage ran out more than the grace days ago.

Dry run by default: it lists what would go. Add --apply to delete. The project_storage row is kept with purged_at set,
as the record of when and why the data was removed. Admin projects and versions saved before billing are never touched.
Run it in backend/ with the same SOLAROPT_DB_PATH as the server, for example once a day from cron.
    .venv\\Scripts\\python scripts\\purge_expired_projects.py            # list
    .venv\\Scripts\\python scripts\\purge_expired_projects.py --apply    # delete
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.billing import storage_rows  # noqa: E402
from app.database import connect, init_db  # noqa: E402


def main(apply: bool) -> int:
    init_db()
    expired = [r for r in storage_rows() if r["state"] == "expired"]
    now = int(time.time())
    for r in expired:
        with connect() as conn:
            versions = conn.execute("SELECT COUNT(*) FROM project_versions WHERE owner=? AND project_key=?", (r["owner"], r["project_key"])).fetchone()[0]
            if apply:
                conn.execute("DELETE FROM project_versions WHERE owner=? AND project_key=?", (r["owner"], r["project_key"]))
                conn.execute("UPDATE project_storage SET purged_at=? WHERE owner=? AND project_key=?", (now, r["owner"], r["project_key"]))
        deadline = datetime.fromtimestamp(r["delete_after"]).strftime("%d/%m/%Y %H:%M")
        print(f"{'DELETED' if apply else 'would delete'}  {r['owner']:<10} {r['project_name']:<40} {versions:>4} versions  (deadline {deadline})")
    print(f"{len(expired)} expired project(s){'' if apply else '; dry run, add --apply to delete'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
