# Production checklist

- [ ] Replace local database credentials and keep secrets in a secret manager.
- [ ] Use managed PostgreSQL with encrypted backups; test restore and deletion procedures.
- [ ] Apply Alembic migrations as a release step and set `AUTO_CREATE_SCHEMA=false`.
- [ ] Serve only over HTTPS; set `COOKIE_SECURE=true`.
- [ ] Configure exact `CORS_ORIGINS` and the production `VITE_API_URL`.
- [ ] Replace in-process auth throttling with a distributed rate limiter / edge WAF.
- [ ] Review data retention, statement-preview cleanup, log redaction and backup retention.
- [ ] Add structured monitoring, alerting, dependency scanning and an incident response process.
- [ ] Security review and authorization tests against the production database and storage.
- [ ] Do not claim bank integrations or financial regulatory certification.
