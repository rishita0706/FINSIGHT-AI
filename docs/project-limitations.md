# Project limitations

- PDF parsing uses a generic text adapter. It supports several common date/amount layouts, attempts reconciliation only if opening and closing balances are extractable, and does not identify bank-specific dialects, wrapped rows reliably, or perform OCR. Review every candidate.
- No open banking, bank, UPI, PhonePe, Paytm, Google Pay, NPCI, or Account Aggregator integration is active. The financial-data provider interface is deliberately disabled.
- SQLite is for local development/testing. PostgreSQL + pgvector is the deployment target; operators still need TLS, managed secrets, backup/restore, monitoring, and retention controls.
- The optional LLM provider only phrases already computed/retrieved answers; it does not produce SQL or change structured calculation/citation fields. A remote provider can receive verified answer text and is disabled by default. Streaming is not implemented.
- The bundled educational corpus is small and FinSight-authored. PostgreSQL uses embeddings and thresholded pgvector retrieval; SQLite uses a lexical fallback. Current evaluation is a five-question synthetic regression set, not an independent relevance or faithfulness assessment.
- Categorization is optional and based on synthetic descriptions. The model report is versioned and surfaced in the UI/API, but its confidence threshold is a heuristic and scores do not predict real-world performance. Rules remain the fallback.
- Median-based anomaly suggestions need five or more category examples and can produce false positives. Recurring candidates are based on normalized descriptions/date gaps and can miss merchant aliases.
- Forecast baseline excludes the current partial month and averages the last three complete recorded months; it has no uncertainty interval and is not a guarantee.
- Budgets and goals are INR-only; savings progress is manually entered. No automatic FX conversion or linked accounts.
- Preview expiration is enforced lazily on import/list/preview activity; a periodic cleanup worker is not included. Not every parser warning can be corrected, and anomaly feedback is not available.
- The database-backed auth limiter shares state among API workers using the same database, but does not replace edge-level abuse protection.
