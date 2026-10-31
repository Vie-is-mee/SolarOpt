# Vercel deployment assessment

Checked against official Vercel documentation on 2026-10-29. This is a feasibility assessment, not a completed deployment or a Postgres migration.

## Feature compatibility

| Feature | Vercel compatibility | Work needed in this repository |
| --- | --- | --- |
| React/Vite UI and auth popup | Supported as static frontend assets. | Set project root to `frontend`, build command `npm run build`, output directory `dist`. Configure production API routing; the development-only Vite proxy does not ship in `dist`. |
| Solar-panel catalog, filters and custom specifications | Supported; catalog is bundled frontend data. | No catalog database service is required. Saving a selected panel still uses the backend/history database. |
| Email/password auth API and cookie sessions | Implementable; FastAPI is supported on Vercel. | Accounts, sessions and login throttling must use shared persistent storage. Use HTTPS and `SOLAROPT_COOKIE_SECURE=true`; preserve the API route and same-site cookie flow. |
| Current local SQLite accounts/history | Not suitable inside Vercel Functions. | Keep the API on a server with persistent disk, or replace the SQLite persistence layer with a remote database. Moving the `.db` file to `/tmp` would not provide durable shared storage. |
| Roof/image/optimizer backend | Possible only after validating function constraints. | Check dependency bundle size, execution limits, upload/response sizes, and concurrency behavior. The current process-local compute semaphore does not provide a deployment-wide concurrency limit. |

Sources: [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite), [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [SQLite support](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel), [function filesystem](https://vercel.com/docs/functions/runtimes), [function limits](https://vercel.com/docs/functions/limitations).

## Lowest-change deployment

Host the frontend on Vercel and keep the existing FastAPI backend plus SQLite on a host with persistent disk. Route frontend `/api` requests to that backend under the same public site using production proxy routing. This preserves the app's cookie and CSRF-header model and avoids a database rewrite. The backend remains responsible for persistent volumes, backups and HTTPS/trusted-proxy configuration. This is an engineering recommendation based on the repository's current architecture.

Do not set a separate unrelated backend origin and assume cookie auth will work unchanged. A cross-site backend requires deliberate cookie/CORS changes; same-origin API routing avoids that complexity. The current Vite proxy only applies during local development/preview.

## If both frontend and API must run on Vercel

1. Provision a remote Postgres database, such as a provider available through Vercel Marketplace. Do not confuse installing an integration with migrating the app: the current Python code still uses SQLite SQL, `sqlite3`, PRAGMAs and a local database path.
2. Replace database access in `backend/app/database.py` and `backend/app/auth.py`. Migrate users, password hashes, sessions, auth-attempt counters and version ownership without exposing legacy unowned rows. Preserve existing numeric panel snapshots.
3. Add a recognized FastAPI entrypoint and production frontend/API routing. Keep secrets server-side and use secure cookies.
4. Move image evidence to private object storage and use authenticated direct uploads when required. Vercel Functions have a **4.5 MB request/response limit**; this app currently supports larger uploads and embedded image evidence. Private file access must still enforce project ownership.
5. Validate the scientific Python dependency bundle and optimizer runtime under Vercel's plan-specific limits. Use shared coordination or a separate worker service if compute load requires it.
6. Verify login/logout, ownership isolation, database persistence across deployments, image restoration, and actual design generation on the hosted environment.

Sources: [Postgres integrations](https://vercel.com/docs/postgres), [FastAPI entrypoints and limits](https://vercel.com/docs/frameworks/backend/fastapi), [function limits](https://vercel.com/docs/functions/limitations), [Blob client uploads for larger files](https://vercel.com/docs/vercel-blob/server-upload).

The auth popup is implemented locally. Cloud database migration, cloud resource provisioning and a live Vercel deployment have not been performed.
