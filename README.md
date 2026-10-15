# FinSight AI — backend core (work in progress)

**Implemented & tested:** registration/login/logout (Argon2id, HttpOnly SameSite=Lax session cookie, custom-header CSRF check),
per-user isolation (404 on foreign IDs), transaction CRUD with Decimal money, CSV import (preview → confirm, duplicate detection,
row-level errors, atomic confirm), analytics overview (transfers excluded; savings rate documented in `app/logic.py`).

**Not implemented yet:** PDF import (returns 501), frontend, Alembic/PostgreSQL/pgvector, ML, RAG, assistant, budgets, goals,
recurring, forecasts, rate limiting, Docker/CI, export/deletion endpoints. Uses SQLite by default (`DATABASE_URL` overrides).

Run (PowerShell): `cd backend; pip install -r requirements.txt; python -m pytest -q; uvicorn app.main:app --reload`
