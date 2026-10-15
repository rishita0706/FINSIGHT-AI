# Dataset guide

`data/synthetic/` is generated with seed 706 by `scripts/generate_synthetic_data.py`.

- `transactions.csv`: fictional INR activity across twelve months.
- `bank_statement_sample.pdf`: fictional text PDF with a clear fictional-statement label.
- `categorization_train.csv` / `categorization_test.csv`: generated description/category examples.
- `anomaly_evaluation.csv`: artificial numeric examples and labels.
- `rag_evaluation.json`: five local retrieval cases including an unanswerable question.

No public transaction dataset is redistributed. There are no account numbers or real transaction histories. Synthetic data is intentionally small and is not suitable for making real-world quality, fairness, or fraud-detection claims.
