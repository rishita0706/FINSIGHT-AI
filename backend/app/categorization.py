"""Optional model-backed categorization with an explicit deterministic fallback."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .logic import categorize

DEFAULT_MODEL = Path(__file__).parent / "ml" / "artifacts" / "categorizer-v1.joblib"
NEEDS_REVIEW_CONFIDENCE = 0.60


@lru_cache(maxsize=2)
def _load_model(path: str):
    import joblib

    return joblib.load(path)


def predict_category(description: str) -> tuple[str, str, str, str | None]:
    model_path = Path(os.getenv("CATEGORIZER_MODEL_PATH", str(DEFAULT_MODEL)))
    if not model_path.is_file():
        category, tx_type = categorize(description)
        return category, tx_type, "rule", None
    model = _load_model(str(model_path))
    probabilities = model.predict_proba([description])[0]
    index = int(probabilities.argmax())
    confidence = float(probabilities[index])
    if confidence < NEEDS_REVIEW_CONFIDENCE:
        category, tx_type = categorize(description)
        return category, tx_type, "rule", f"{confidence:.4f}"
    category = str(model.classes_[index])
    tx_type = "income" if category == "Income" else "transfer" if category == "Transfers" else "expense"
    return category, tx_type, "model", f"{confidence:.4f}"
