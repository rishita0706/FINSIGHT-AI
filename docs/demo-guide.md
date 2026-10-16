# Demo guide

## Start and sample data

Follow the Windows PowerShell quick start in the root README. For local SQLite, Alembic applies the schema; for Compose, the API container runs the migrations before starting. Create a local account or seed a disposable synthetic account with the documented `DEMO_EMAIL` and `DEMO_PASSWORD` environment variables.

Sample inputs live in `data/synthetic/`: `bank_statement_sample.pdf`, `transactions.csv`, and fixed-seed transaction/category/anomaly/RAG fixtures. They contain fictional data.

## Walkthrough

1. Register and sign in. Show that the session is HttpOnly, and a second login rotates the session.
2. Start with an empty dashboard; add a manual transaction or import the synthetic PDF/CSV.
3. Review warnings and rows. Correct an extraction result and confirm. Before confirmation, analytics do not include the preview. Re-importing the same rows flags duplicates.
4. Explore dashboard analytics, transactions, budgets, goals, recurring candidates, and insights. Date filters and totals are server-calculated.
5. Ask a personal question such as "How much did I spend in September 2026?" and compare the answer with analytics. Then ask an education question such as "Explain compound interest" and inspect citations. Unknown topics abstain.
6. Create a conversation, reload it, and use the delete control/API. Export data or delete transaction history/account to demonstrate the privacy controls.

## Optional model and knowledge ingestion

Without credentials, `LLM_PROVIDER=mock` keeps all assistant phrasing local. A remote provider is optional and may receive the verified answer text; review provider privacy terms before enabling. For the PostgreSQL semantic retrieval path, use the Compose pgvector database, apply migrations, and run `python scripts/ingest_knowledge_base.py`. `python scripts/evaluate_rag.py` reports Recall@3 and MRR; set `RAG_USE_DATABASE=true` to evaluate pgvector retrieval.

These steps demonstrate an MVP, not bank connectivity, investment advice, universal bank-PDF parsing, or production readiness. Check and correct every imported transaction.
