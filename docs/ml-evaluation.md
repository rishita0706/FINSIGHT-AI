# ML and baseline evaluation

## Categorization

`python scripts/evaluate_categorizer.py` fits and evaluates the versioned `categorizer-v1` TF-IDF (unigrams/bigrams) + Logistic Regression pipeline on fixed-seed fictional transaction descriptions. The generated split has 364 train rows and 91 held-out shuffled test rows. The report contains per-class precision/recall, a confusion matrix, and a 0.60 needs-review confidence threshold in ignored `artifacts/categorizer-evaluation.json`; authenticated clients can read it at `/api/v1/ml/categorizer/evaluation`.

This score reflects repetitive generated templates, not real transactions. It must not be represented as expected user accuracy. The optional local model uses a 0.60 confidence threshold and falls back to keyword rules below that threshold or when the artifact is absent. Category edits are marked user-specified.

## Unusual transactions

The API flags a debit as an unusual candidate when its amount is at least three times the category median and there are at least five category examples. The synthetic evaluation script reported precision 0.80 and recall 1.00 on the generated 173-row dataset. These labels are synthetic; a flagged item is not proof of fraud.

## Forecast baseline

`scripts/evaluate_forecaster.py` uses chronological rolling evaluation on six held-out synthetic months. The observed run: 3-month mean MAE ₹7,097.78 / RMSE ₹8,020.17; last-month baseline MAE ₹6,306.67 / RMSE ₹8,109.15. These values vary only if the fixed generator changes. They do not demonstrate predictive quality on real user behavior. The API requires three complete recorded months and returns the mean of those months.

## Retrieval evaluation

`scripts/evaluate_rag.py` measures Recall@3, MRR, citation source-membership, and insufficient-evidence abstention for a five-question hand-authored set. By default it evaluates the deterministic lexical fallback; set `RAG_USE_DATABASE=true` with a migrated pgvector database to evaluate cosine-distance retrieval. This small dataset is not an independent faithfulness evaluation, nor does it use an LLM judge.
