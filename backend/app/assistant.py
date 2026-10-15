"""Constrained local assistant: financial calculations are always deterministic."""
from __future__ import annotations

import calendar
import re
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Transaction

MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
CATEGORY_TERMS = {
    "food": ("food and dining", "food"),
    "dining": ("food and dining", "food"),
    "groceries": ("groceries", "grocer"),
    "transport": ("transport", "transport"),
    "shopping": ("shopping", "shop"),
    "rent": ("housing and utilities", "rent"),
    "utilities": ("housing and utilities", "utilit"),
    "subscriptions": ("subscriptions", "subscription"),
}


def _month_range(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def answer_financial_question(db: Session, user_id: str, question: str, today: date | None = None) -> dict:
    today = today or date.today()
    normalized = question.casefold()
    txs = db.scalars(select(Transaction).where(Transaction.user_id == user_id)).all()
    if not txs:
        return {
            "mode": "deterministic",
            "answer": "I don’t have any transactions for your account yet. Add a transaction or import a statement, then I can calculate this from your records.",
            "calculation": None,
            "citations": [],
        }

    start, end = _month_range(today.year, today.month)
    if "last month" in normalized:
        year = today.year - 1 if today.month == 1 else today.year
        month = 12 if today.month == 1 else today.month - 1
        start, end = _month_range(year, month)
    else:
        month_match = re.search(r"\b(" + "|".join(MONTHS) + r")(?:\s+(\d{4}))?\b", normalized)
        if month_match:
            month = MONTHS[month_match.group(1)]
            year = int(month_match.group(2)) if month_match.group(2) else today.year
            start, end = _month_range(year, month)
        elif "this month" in normalized or "month" in normalized:
            end = today

    selected = [tx for tx in txs if start <= tx.date <= end]
    category = next(
        (terms for label, terms in CATEGORY_TERMS.items() if label in normalized),
        None,
    )
    expenses = [
        tx for tx in selected
        if tx.direction == "debit" and tx.tx_type != "transfer"
        and (category is None or category[0].casefold() in tx.category.casefold() or category[1] in tx.category.casefold())
    ]
    if "largest" in normalized or "biggest" in normalized:
        largest = sorted(expenses, key=lambda item: item.amount, reverse=True)[:5]
        amount = sum((tx.amount for tx in largest), Decimal(0))
        return {
            "mode": "deterministic",
            "answer": f"Here are your {len(largest)} largest qualifying transactions from {start.isoformat()} to {end.isoformat()}.",
            "calculation": {
                "metric": "largest_transactions",
                "value": str(amount),
                "currency": "INR",
                "date_range": {"start": start.isoformat(), "end": end.isoformat()},
                "definition": "Debit transactions excluding items classified as transfers.",
                "transactions": [
                    {"date": tx.date.isoformat(), "description": tx.description, "amount": str(tx.amount), "category": tx.category}
                    for tx in largest
                ],
            },
            "citations": [],
        }

    total = sum((tx.amount for tx in expenses), Decimal(0))
    label = f" on {category[0]}" if category else ""
    return {
        "mode": "deterministic",
        "answer": f"You spent ₹{total:,.2f}{label} from {start.isoformat()} to {end.isoformat()} based on {len(expenses)} debit transactions. Transfers are excluded.",
        "calculation": {
            "metric": "spending",
            "value": str(total),
            "currency": "INR",
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "definition": "Sum of debit transactions excluding items classified as transfers.",
            "transaction_count": len(expenses),
            "warnings": ["Refunds and transfers may require review if the statement description did not identify them."],
        },
        "citations": [],
    }
