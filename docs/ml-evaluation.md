# ML and baseline evaluation

## Categorization

`python scripts/train_categorizer.py` fits a TF-IDF (unigrams/bigrams) + Logistic Regression pipeline on fixed-seed fictional transaction descriptions. The generated split has 364 train rows and 91 held-out shuffled test rows. The observed run reported macro-F1 **1.00** and weighted-F1 **1.00**, with per-class precision/recall and confusion matrix written to ignored `artifacts/categorizer-evaluation.json`.

This score reflects repetitive generated templates, not real transactions. It must not be represented as expected user accuracy. The optional local model uses a 0.60 confidence threshold and falls back to keyword rules below that threshold or when the artifact is absent. Category edits are marked user-specified.

## Unusual transactions

The API flags a debit as an unusual candidate when its amount is at least three times the category median and there are at least five category examples. The synthetic evaluation script reported precision 0.80 and recall 1.00 on the generated 173-row dataset. These labels are synthetic; a flagged item is not proof of fraud.

## Forecast baseline

`scripts/evaluate_forecaster.py` uses chronological rolling evaluation on six held-out synthetic months. The observed run: 3-month mean MAE ₹7,097.78 / RMSE ₹8,020.17; last-month baseline MAE ₹6,306.67 / RMSE ₹8,109.15. These values vary only if the fixed generator changes. They do not demonstrate predictive quality on real user behavior. The API requires three complete recorded months and returns the mean of those months.

## Retrieval evaluation

`scripts/evaluate_rag.py` measured Recall@3 1.00, MRR 0.80, citation source-membership 1.00, and successful insufficient-evidence abstention for a five-question hand-authored set. It is deterministic lexical term overlap. This small dataset is not an independent faithfulness evaluation, nor does it use an LLM judge.
