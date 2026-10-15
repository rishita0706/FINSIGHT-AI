from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median

from .models import Transaction


def find_anomaly_candidates(transactions: list[Transaction]) -> list[dict]:
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for tx in transactions:
        if tx.direction == "debit" and tx.tx_type != "transfer":
            groups[tx.category].append(tx)
    candidates = []
    for category, items in groups.items():
        if len(items) < 5:
            continue
        amounts = [item.amount for item in items]
        typical = median(amounts)
        if typical <= Decimal(0):
            continue
        for tx in items:
            if tx.amount >= typical * Decimal(3):
                candidates.append({
                    "transaction_id": tx.id,
                    "date": tx.date.isoformat(),
                    "description": tx.description,
                    "amount": str(tx.amount),
                    "category": category,
                    "reason": f"At least 3× the median amount for {category} in this recorded history.",
                    "status": "unusual_candidate",
                    "warning": "Unusual spending is not proof of fraud.",
                })
    return sorted(candidates, key=lambda item: Decimal(item["amount"]), reverse=True)
