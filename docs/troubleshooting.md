# Troubleshooting

- **Python dependencies fail on Windows:** use Python 3.13 (the README quick-start creates a Python 3.13 environment) and retry `python -m pip install -r backend\requirements.txt`.
- **PostgreSQL is unavailable:** use SQLite quick-start, or check `docker compose ps` / PostgreSQL logs and confirm port 5432 is unused.
- **Migration errors:** run `python -m alembic upgrade head` from `backend` with the same `DATABASE_URL` used by the API.
- **401 / login:** register first. The app stores an HttpOnly cookie; use the frontend origin and do not disable browser cookies.
- **403 on a mutation:** API writes need `X-Requested-With: FinSight`; the typed frontend client adds it automatically.
- **CORS:** set `CORS_ORIGINS` to the exact frontend origin, including scheme and port, then restart the API.
- **PDF extraction returns no rows:** use selectable text PDF or CSV; scanned PDFs/OCR are unsupported. Verify that the file is not encrypted and inspect the import error.
- **Unsupported statement layout:** CSV/manual entry is the fallback. Generic PDF extraction is not universal.
- **Port conflict:** use a free Vite/API/PostgreSQL port and update `VITE_API_URL`, `CORS_ORIGINS`, and Compose mappings consistently.
- **Missing assistant API key:** no key is required. The local deterministic assistant is the only implemented mode.
- **Frontend dependency issue:** use Node 22 and `npm ci` from `frontend`.
