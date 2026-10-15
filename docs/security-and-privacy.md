# Security and privacy notes

## Implemented controls

- Passwords are hashed with Argon2id; raw session tokens are opaque, HttpOnly and SameSite=Lax, and only SHA-256 token hashes are stored.
- State-changing requests require the `X-Requested-With: FinSight` header. CORS defaults to explicit local frontend origins and can be overridden.
- Authentication has an in-process IP and per-account attempt window. It is not distributed across workers and must be replaced or supplemented by an edge/WAF limiter for production.
- ORM query paths include the authenticated owner ID. Cross-user tests cover transaction, import, budget and goal boundaries.
- Monetary calculations use Decimal/Numeric. Uploads are limited to 2 MB; PDF parsing is capped at 200 pages; no OCR subprocess runs.
- Raw PDF/CSV bytes are not stored. Parsed rows are held in a review job for up to 24 hours, are purged lazily on import/list/preview activity, and are discarded after confirm. Users can delete their history/account.
- Logs do not include statement content or passwords by design. Do not enable verbose request-body logging.

## Limitations and operator duties

This is not a certified banking system. Review dependency reports, configure HTTPS, `COOKIE_SECURE=true`, production CORS, managed secrets, database backups/restore, access monitoring, a distributed rate limiter and retention/deletion policies before public use. Database backups are operator-controlled; deleting a live account cannot remove its data from already-created backups. Test account and deletion flows before storing real records.

Do not upload documents you are not authorized to process. Imported descriptions are user data and should not be submitted to a third-party LLM; the current app does not call one.
