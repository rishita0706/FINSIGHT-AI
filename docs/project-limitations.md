# Project limitations

- PDF layouts are inconsistent. Current parsing is generic and does not reconcile balances, detect all wrapped rows, identify bank-specific dialects, or perform OCR. Users must review candidates before confirmation.
- No open banking, bank, UPI, PhonePe, Paytm, Google Pay, NPCI or Account Aggregator integration is active.
- SQLite is suitable for local demo/testing; production requires PostgreSQL and operational controls.
- No LLM API adapter, pgvector schema, semantic embedding, hybrid search, streaming, or conversation persistence is currently wired. Assistant personal calculations are constrained; education retrieval uses local lexical matching.
- The optional sklearn artifact is trained on short synthetic descriptions; confidence thresholds are heuristic. Rule-based classification remains the default if the artifact is absent.
- Median-based anomaly suggestions need five or more category examples and can produce false positives. Recurring candidates are based on normalized descriptions/date gaps and can miss merchant aliases.
- Forecast baseline excludes the current partial month and averages the last three complete recorded months; it has no uncertainty interval and is not a guarantee.
- Budgets and goals are INR-only; savings progress is manually entered. No automatic FX conversion or linked accounts.
- Chat history, full correction of every parser warning, export import history details, automatic preview cleanup scheduling, and user feedback on anomalies are future work.
- Rate limiting is in-process only; use an edge limiter in multi-worker production.
