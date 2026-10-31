"""Grant or revoke SolarOpt admin rights. Run on the server only (needs access to the database file).

  python scripts/manage_admin.py grant you@example.com
  python scripts/manage_admin.py revoke you@example.com
  python scripts/manage_admin.py list

Admin rights are never granted through the web API or by email alone: accounts have no email
verification yet, so anyone could otherwise register an admin address first.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import connect, init_db


def main(argv):
    init_db()
    if len(argv) == 2 and argv[1] == "list":
        with connect() as conn:
            for email, in conn.execute("SELECT email FROM users WHERE role='admin' ORDER BY email"):
                print(email)
        return 0
    if len(argv) != 3 or argv[1] not in ("grant", "revoke"):
        print(__doc__)
        return 2
    role = "admin" if argv[1] == "grant" else "user"
    with connect() as conn:
        changed = conn.execute("UPDATE users SET role=? WHERE email=?", (role, argv[2].strip().lower())).rowcount
    if not changed:
        print("Không tìm thấy tài khoản; hãy đăng ký trên web trước.")
        return 1
    print(f"{argv[2]}: {role}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
