# Accounts and private history

SolarOpt uses the existing SQLite database; no external auth or database service is required. Schema additions run automatically at backend startup and preserve existing versions.

Use **Đăng nhập / Đăng ký** above the workspace to open the dedicated auth popup and create an account with an email and a password of 10–128 characters. Signed-in design generation, repair, and approval save versions to that account. History shows the latest 50 versions across all projects; restoring a version also restores its source evidence. Guest calculations remain available but do not save server history. Approval requires login.

Browser drafts and image evidence are separated by account. They remain on that browser; saved server versions are available after login on another device. Existing guest drafts remain under the guest profile. Historical versions without an owner remain in the database and are not assigned to new accounts automatically.

## Configuration

- `SOLAROPT_DB_PATH`: SQLite file, default `backend/solaropt.db`. Existing backup and restore scripts cover accounts, sessions, and history together.
- `SOLAROPT_COOKIE_SECURE=true`: required for HTTPS hosting; already enabled in Docker Compose. Leave false for local HTTP development.
- Serve frontend and API on the same site through the existing Vite/Caddy proxy. For separate origins, explicitly allow the frontend in `CORS_ORIGINS`; wildcard origins are not supported with credentials. The request header `X-SolarOpt-Request: 1` is required for auth mutations and authenticated writes. Workspace requests also send `X-SolarOpt-User` with the displayed user ID or `guest`; the API rejects a mismatch with the cookie session before reading or saving history.

Passwords use salted scrypt hashes. Opaque session tokens are stored as SHA-256 hashes, expire after seven days, and are revoked on logout. Cookies use HttpOnly and SameSite=Lax. Login and registration share a persisted limit of 30 attempts per client IP per 15 minutes. Behind a proxy, configure trusted forwarding correctly; otherwise users may share a rate-limit bucket. Email verification and password recovery are not included in this lightweight implementation.

## API

- `POST /api/auth/register`, `POST /api/auth/login`: JSON `{ "email": "user@example.com", "password": "your-long-password" }`; return user ID/email and set session cookie.
- `GET /api/auth/me`: current user, or 401.
- `POST /api/auth/logout`: revoke current session and clear cookie.
- `GET /api/history`: latest 50 account-owned versions across projects.
- Existing project version list/detail endpoints now require login and enforce ownership; another user's version returns 404.

Reference: [Python scrypt](https://docs.python.org/3/library/hashlib.html#hashlib.scrypt), [Starlette cookie options](https://www.starlette.dev/responses/#set-cookie).

The popup supports Escape, backdrop dismissal, keyboard focus containment and a guest-mode action. Dismissal is disabled while an auth request is pending. See [Vercel deployment assessment](VERCEL_DEPLOYMENT.md) before deploying the SQLite-backed API to serverless hosting.

Account changes are synchronized between tabs and revalidated on focus. Expired or revoked sessions return 401 instead of silently downgrading a signed-in calculation to an unsaved guest calculation. Invalid cookies are cleared, and the UI offers login again. Browser drafts remain under their original account key.
