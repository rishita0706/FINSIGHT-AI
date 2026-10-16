# Deployment

## Local Docker

`docker compose up --build` starts PostgreSQL with pgvector, runs `alembic upgrade head`, starts FastAPI, and runs the Vite development server. Local compose defaults are not production secrets.

## Production outline

1. Build `frontend` with `VITE_API_URL` set to the HTTPS API origin. Host the generated `frontend/dist` on a static host.
2. Build `backend/Dockerfile` and deploy it on a container-capable service with a managed PostgreSQL database.
3. Set `DATABASE_URL` to a SQLAlchemy `postgresql+psycopg://` URL; do not expose it to the browser.
4. Set `AUTO_CREATE_SCHEMA=false`, run `alembic upgrade head` as a release step, and use an HTTPS-only cookie (`COOKIE_SECURE=true`).
5. Set `CORS_ORIGINS` to the exact production frontend origin(s), configure TLS and health checks (`/health`, `/ready`), and store credentials in a secrets manager.
6. Configure encrypted database backups and rehearse restore and deletion procedures.
7. Monitor API errors, upload resource use, authentication failures, and database capacity without logging raw statements, credentials, or session tokens.
8. If you enable the optional remote model provider, set its API key/model settings through a secrets manager and review what verified answer text may be sent to it. Leave `LLM_PROVIDER=mock` for fully local assistant operation.

No provider-specific deployment files, paid service configuration, or live deployment URL are included. Hosting prices, quotas, cold starts, database storage and LLM costs depend on the chosen provider; no free tier is assumed to be permanent or suitable for production.

## Windows local PostgreSQL

Set `DATABASE_URL` in PowerShell before starting Alembic and Uvicorn, for example:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://finsight:REPLACE_ME@localhost:5432/finsight"
$env:AUTO_CREATE_SCHEMA = "false"
Set-Location backend
alembic upgrade head
python -m uvicorn app.main:app --reload
```
