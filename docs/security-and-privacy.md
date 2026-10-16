# Security and privacy

## Implemented controls

- Passwords use Argon2id. Session tokens are opaque, random, HttpOnly, SameSite=Lax cookies; only SHA-256 hashes are stored. A successful login revokes the previous browser session before issuing a replacement.
- State-changing requests require `X-Requested-With: FinSight`; CORS is allow-listed. Responses include CSP, `nosniff`, frame, referrer, and no-store headers. HSTS is sent when `COOKIE_SECURE=true`; use that setting behind HTTPS.
- Authentication attempts are recorded with atomic database upserts. PostgreSQL instances sharing the database share the limits; stale windows are pruned during authentication.
- Owner-scoped query paths check both resource ID and user ID. Cross-user requests return 404.
- Amounts use Decimal/Numeric. Uploads are limited to 2 MB; PDF parsing runs in an isolated process capped at 200 pages and forcibly terminated after 15 seconds. File content is checked against its claimed type.
- PDF passwords are request-only. Raw PDF/CSV bytes are not persisted. Parsed rows remain in a user-scoped review record for up to 24 hours, are deleted on confirmation, and can be explicitly deleted. Scanned PDFs are detected but OCR is not performed.
- The optional LLM receives only verified answers, never statement text or generated SQL. Token counts and provider/model/purpose are recorded without storing prompts or responses.
- Database account deletion explicitly removes transactions, imports, plans, settings, sessions, and conversations/messages; model-run records are anonymized by nulling the user ID.

## Remaining operator duties and limitations

This is not a certified banking system. Configure HTTPS, `COOKIE_SECURE=true`, production CORS, managed secrets, least-privilege DB roles, backup/restore, audit monitoring, dependency updates, and documented deletion/backup-retention policies before public use. A database-backed rate limit does not replace edge-level abuse protection. Deleting live records cannot remove copies from operator-managed backups.

The LLM provider is optional and disabled by default (`LLM_PROVIDER=mock`). If enabling a remote provider, review its data-processing terms and send only data that is necessary and authorized. Do not upload statements you are not authorized to process. Live bank/UPI connectivity is unavailable.

CI installs the pinned Python dependencies, runs Ruff/mypy/tests/frontend checks, and audits Python and npm dependencies. These audits compare package metadata with public advisory databases; they do not upload project source code.
