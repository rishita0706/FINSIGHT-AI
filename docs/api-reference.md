# API reference

All application endpoints use `/api/v1`. Interactive OpenAPI docs are served at `/docs`; the JSON spec is `/openapi.json`. Mutating requests require `X-Requested-With: FinSight` and an authenticated session cookie, except public health checks. Error responses use FastAPI's `detail` field. Monetary values are serialized as decimal strings in INR.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Transactions | `GET/POST /transactions`, `GET/PATCH/DELETE /transactions/{id}`, `GET /transactions/export` |
| Imports | `POST /imports`, `GET /imports`, `GET /imports/{id}`, `GET/PATCH /imports/{id}/preview`, `POST /imports/{id}/confirm`, `DELETE /imports/{id}` |
| Analytics | `GET /analytics/overview`, `/analytics/cash-flow`, `/analytics/categories`, `/analytics/monthly-comparison` |
| Budgets | `GET/POST /budgets`, `PATCH/DELETE /budgets/{id}` |
| Goals | `GET/POST /goals`, `PATCH/DELETE /goals/{id}` |
| Recurring and insights | `GET /recurring`, `POST /recurring/{merchant}/confirm`, `/dismiss`, `GET /insights`, `GET /forecasts` |
| Assistant/knowledge | `POST /assistant/query`, `GET /knowledge/documents`, `GET /knowledge/documents/{id}` |
| Settings/data | `GET/PATCH /settings`, `POST /settings/export`, `DELETE /settings/transactions`, `DELETE /settings/account` |
| Health | `GET /health`, `GET /ready` |

Every owner-scoped read/update/delete checks both record ID and user ID. A resource belonging to another user returns 404. Import confirmation is atomic and is not repeatable. Import preview patch requests accept one or more rows keyed by source line number. Unreadable PDF and invalid CSV errors use 422; uploads larger than 2 MB use 413.

Conversation history CRUD, per-document database CRUD, PDF OCR, bank-provider APIs, export of uploaded source files, and rate-limit management endpoints are not implemented.
