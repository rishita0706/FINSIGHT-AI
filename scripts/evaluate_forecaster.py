from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    monthly: dict[str, Decimal] = defaultdict(Decimal)
    with (ROOT / "data" / "synthetic" / "transactions.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["direction"] == "debit" and row["type"] != "transfer":
                monthly[row["date"][:7]] += Decimal(row["amount"])
    values = [monthly[month] for month in sorted(monthly)]
    actuals, mean_predictions, naive_predictions = [], [], []
    for index in range(6, len(values)):
        actuals.append(float(values[index]))
        mean_predictions.append(float(sum(values[index - 3:index], Decimal(0)) / Decimal(3)))
        naive_predictions.append(float(values[index - 1]))
    def metrics(predictions):
        errors = [prediction - actual for prediction, actual in zip(predictions, actuals)]
        return {"mae": sum(abs(error) for error in errors) / len(errors),
                "rmse": math.sqrt(sum(error * error for error in errors) / len(errors))}
    print(json.dumps({"temporal_holdout_months": len(actuals), "three_month_mean": metrics(mean_predictions),
                      "last_month_baseline": metrics(naive_predictions),
                      "limitation": "Synthetic monthly activity and a short rolling temporal holdout; not predictive of real users."}, indent=2))

if __name__ == "__main__":
    main()
