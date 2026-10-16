# Interview preparation

- **Problem:** finance tools often require manual spreadsheets while generic chatbots cannot reliably access private transaction facts.
- **Architecture:** a modular monolith keeps financial records and calculations in one API; the frontend never computes authoritative totals.
- **SQL vs. RAG:** personal questions route to typed, deterministic operations scoped to the logged-in user. General education retrieves local notes and cites their source records; no generated SQL or external model is used.
- **ML:** TF-IDF + Logistic Regression is a reproducible baseline. Synthetic evaluation is deliberately described as synthetic, and a rule fallback keeps the app usable without an artifact.
- **Privacy:** statement bytes are processed in memory, preview rows have bounded retention, sessions store only token hashes, and live bank access is intentionally absent.
- **Trade-offs:** SQLite simplifies development; PostgreSQL + pgvector is used for deployed retrieval. The mock embedding adapter keeps tests deterministic, while the optional external embedding provider adds cost/privacy trade-offs. Generic PDF parsing is review-first, not universal bank support.
- **Next steps:** improve PDF fixtures/reconciliation, add pgvector with licensed sources, implement optional model providers, expand tests, and harden production rate-limits/monitoring.
