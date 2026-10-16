# API reference

All application routes use `/api/v1`; `/openapi.json` and `/docs` expose the generated OpenAPI contract. Authenticated requests use the HttpOnly `fs_session` cookie. State-changing requests also require `X-Requested-With: FinSight`. Error responses use FastAPI's `detail` field. Currency is INR and monetary values are serialized as decimal strings.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Transactions | `GET/POST /transactions`, `GET/PATCH/DELETE /transactions/{id}`, `GET /transactions/export` |
| Imports | `POST /imports`, `GET /imports`, `GET /imports/{id}`, `GET/PATCH /imports/{id}/preview`, `POST /imports/{id}/confirm`, `DELETE /imports/{id}` |
| Analytics | `GET /analytics/overview`, `/analytics/cash-flow`, `/analytics/categories`, `/analytics/monthly-comparison` |
| Budgets/goals | `GET/POST /budgets`, `PATCH/DELETE /budgets/{id}`, `GET/POST /goals`, `PATCH/DELETE /goals/{id}` |
| Recurring and insights | `GET /recurring`, `POST /recurring/{merchant}/confirm`, `/dismiss`, `GET /insights`, `GET /forecasts` |
| Assistant | `POST /assistant/query`; `GET/POST /conversations`; `GET/DELETE /conversations/{id}`; `POST /conversations/{id}/messages` |
| Knowledge and evaluation | `GET /knowledge/documents`, `GET /knowledge/documents/{id}`, `GET /ml/categorizer/evaluation` |
| Settings/data | `GET/PATCH /settings`, `POST /settings/export`, `DELETE /settings/transactions`, `DELETE /settings/account` |
| Health | `GET /health`, `GET /ready` |

Paths in the table are relative to `/api/v1`. Conversation message requests accept `{ "question": "..." }`; the response returns separate user/assistant messages and retains structured calculation/citation fields. Conversations and their messages are owner-scoped and deletable.

## Import contract

`POST /imports` accepts a multipart `file` and optional request-only PDF `password`. Uploads are limited to 2 MB. PDF parsing is isolated in a bounded worker with a 15-second timeout and 200-page limit. Preview rows are editable by source line number. Confirm runs in one database transaction, skips duplicates, and erases parsed rows. Preview jobs expire after 24 hours. Invalid content/unsupported layouts use 422 or 415; oversized uploads use 413.

## Authorization and calculations

Every owner-scoped read/update/delete includes the authenticated user ID; another user's record resolves to 404. Personal assistant answers use fixed server operations, not model-generated SQL. Calculation values, date ranges, definitions, and citations are structured API data and must be displayed as returned. Educational answers abstain when retrieval finds no sufficiently relevant source.

The optional model provider is disabled by default. When configured as `openai`, only the verified answer text is submitted for phrasing; provider usage is recorded without saving prompts or responses. No endpoint enables live bank or financial-data connectivity.
