# Database schema

The authoritative schema is defined by `backend/app/models.py` and applied by ordered Alembic revisions in `backend/alembic/versions/`. The initial revision creates concrete tables and constraints; it does not call `metadata.create_all`. Revision `0002_assistant_knowledge_and_limits` adds chat history, vector documents/chunks, model usage, and shared auth rate limits.

| Table | Ownership / purpose |
|---|---|
| `users` | Unique account email and Argon2 password hash |
| `sessions` | SHA-256 hash of an opaque cookie token, owner, expiration |
| `transactions` | Positive `Numeric(14,2)` amount, direction/type/category, source, fingerprint |
| `import_jobs` | User-owned review rows and warnings; raw file/password are not stored |
| `budgets`, `savings_goals`, `recurring_status`, `user_settings` | User-owned planning/preferences |
| `conversations`, `messages` | Persistent assistant history; conversation deletion cascades to messages |
| `knowledge_documents`, `knowledge_chunks` | Versioned source metadata and chunk embeddings |
| `model_runs` | Provider/model/purpose, success and token counts; account deletion nulls owner ID |
| `auth_rate_limits` | Atomic five-minute authentication-attempt windows shared by API workers |

User-owned records use `ON DELETE CASCADE`, except model-run audit records use `SET NULL`. Key checks constrain transaction direction/type and positive amounts, budget and goal values, valid message roles, and nonnegative token counts. Indexes support owner/date queries, conversation chronology, source-version uniqueness, and vector cosine search. PostgreSQL uses `vector(1536)`; SQLite uses JSON only as a local/test compatibility representation and does not execute vector search.

Transaction uniqueness is `(user_id, fingerprint)`, where fingerprints include transaction date, normalized description, amount, and direction. Duplicate detection is scoped to one user.

## Calculation definitions

- Income: credits excluding transfers.
- Expenses: debits excluding transfers.
- Net cash flow: income minus expenses.
- Savings rate: net cash flow divided by income; null when income is zero.
- Category totals: debit transactions excluding transfers.
- Budget usage: same-category debits within its calendar month, excluding transfers.
- Goal progress: saved amount divided by target amount, capped at 100%.
- Refund classification is rule-based and may be wrong; imported rows remain reviewable before confirmation.

Local schema initialization can be enabled for quick starts, but deployment must set `AUTO_CREATE_SCHEMA=false` and apply `alembic upgrade head`.
