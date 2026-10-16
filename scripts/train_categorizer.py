from __future__ import annotations

import csv
import json
import argparse
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
MODEL_VERSION = "categorizer-v1"
NEEDS_REVIEW_CONFIDENCE = 0.60

def load(path: Path) -> tuple[list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row["description"] for row in rows], [row["category"] for row in rows]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-artifact", action="store_true", help="Save the fitted pipeline for local inference.")
    args = parser.parse_args()
    x_train, y_train = load(DATA / "categorization_train.csv")
    x_test, y_test = load(DATA / "categorization_test.csv")
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, strip_accents="unicode")),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=706)),
    ])
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    result = {
        "version": MODEL_VERSION,
        "model": "TF-IDF + Logistic Regression",
        "dataset": "synthetic fictional transaction descriptions",
        "split": "fixed 80/20 shuffled split generated with seed 706",
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "macro_f1": f1_score(y_test, predictions, average="macro"),
        "weighted_f1": f1_score(y_test, predictions, average="weighted"),
        "per_class": report,
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=model.classes_).tolist(),
        "labels": model.classes_.tolist(),
        "needs_review_confidence_threshold": NEEDS_REVIEW_CONFIDENCE,
        "needs_review_policy": "Predictions below this confidence fall back to deterministic rules and should be reviewed.",
        "limitations": "Synthetic examples share templates and do not establish real-world accuracy.",
    }
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    serialized = json.dumps(result, indent=2)
    (out / "categorizer-evaluation.json").write_text(serialized, encoding="utf-8")
    report_path = ROOT / "backend" / "app" / "ml" / "evaluation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(serialized, encoding="utf-8")
    if args.save_artifact:
        import joblib

        artifact_dir = ROOT / "backend" / "app" / "ml" / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, artifact_dir / f"{MODEL_VERSION}.joblib")
    print(json.dumps({key: result[key] for key in ("model", "train_rows", "test_rows", "macro_f1", "weighted_f1")}, indent=2))

if __name__ == "__main__":
    main()
