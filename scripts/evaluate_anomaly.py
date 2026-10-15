from __future__ import annotations

import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    with (ROOT / "data" / "synthetic" / "anomaly_evaluation.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for row in rows:
        if not int(row["is_anomaly"]):
            groups[row["category"]].append(Decimal(row["amount"]))
    predictions = []
    for row in rows:
        baseline = groups[row["category"]]
        predicted = len(baseline) >= 5 and Decimal(row["amount"]) >= median(baseline) * Decimal(3)
        predictions.append(predicted)
    actual = [bool(int(row["is_anomaly"])) for row in rows]
    tp = sum(predicted and expected for predicted, expected in zip(predictions, actual))
    fp = sum(predicted and not expected for predicted, expected in zip(predictions, actual))
    fn = sum(not predicted and expected for predicted, expected in zip(predictions, actual))
    print(json.dumps({"synthetic_rows": len(rows), "precision": tp / (tp + fp) if tp + fp else 0,
                      "recall": tp / (tp + fn) if tp + fn else 0,
                      "rule": "Flag category transaction at least 3x median when five or more baseline examples exist.",
                      "limitation": "Synthetic labels and rule evaluation do not identify actual fraud."}, indent=2))

if __name__ == "__main__":
    main()
