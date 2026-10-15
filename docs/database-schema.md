# Database schema

The ORM currently defines:

| Table | Ownership / purpose |
|---|---|
| `users` | Email and Argon2 password hash |
| `sessions` | SHA-256 hash of an opaque cookie token, owner ID, expiration |
| `transactions` | Date, original description, positive Decimal amount, direction/type/category, fingerprint, source and optional model confidence |
| `import_jobs` | User-scoped filename/status, short-lived parsed preview rows, warning metadata and source type; no raw upload |
| `budgets` | User, category, INR limit, first day of the monthly period |
| `savings_goals` | User, goal name, target/saved INR values and optional date |
| `recurring_status` | User-scoped status for a normalized recurring candidate |
| `user_settings` | Preferred IANA timezone and INR currency |

Foreign keys use `ON DELETE CASCADE`; account deletion also explicitly deletes user-owned records for SQLite portability. Transaction uniqueness is `(user_id, fingerprint)`. Identical description/date/amount/direction rows are therefore considered duplicates for one user; users can correct the source description/date before confirming.

`backend/alembic/versions/0001_initial_schema.py` provides initial schema creation and upgrades the original prototype's missing import metadata/category-confidence columns. Local automatic table creation is a convenience toggle; use Alembic with `AUTO_CREATE_SCHEMA=false` for deployment.

## Calculation definitions

- Income: credits excluding transfers.
- Expenses: debits excluding transfers.
- Net cash flow: income minus expenses.
- Savings rate: net cash flow divided by income; null when income is zero.
- Category totals: debit transactions excluding transfers.
- Budget usage: same-category debits in its calendar month, excluding transfers.
- Goal progress: saved amount divided by target amount, capped at 100%.
- Refund classification is rule-based and can be incorrect; the original direction and type remain visible/editable.
