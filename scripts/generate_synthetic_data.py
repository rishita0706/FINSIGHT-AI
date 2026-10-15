from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
RNG = random.Random(706)
CATEGORIES = {
    "Food and dining": ["Swiggy order", "Zomato restaurant", "Cafe coffee", "Local restaurant"],
    "Groceries": ["DMart groceries", "BigBasket order", "Blinkit essentials", "Local grocery"],
    "Transport": ["Uber ride", "Ola cab", "Metro card recharge", "Fuel station"],
    "Shopping": ["Online apparel store", "Book store", "Electronics shop", "Home supplies"],
    "Housing and utilities": ["Monthly rent", "Electricity bill", "Broadband bill", "Mobile recharge"],
    "Education": ["Course fee", "Book purchase", "Learning subscription"],
    "Healthcare": ["Pharmacy purchase", "Clinic consultation", "Diagnostic lab"],
    "Entertainment": ["Cinema tickets", "Streaming rental", "Event tickets"],
    "Subscriptions": ["Netflix subscription", "Spotify subscription", "Cloud storage plan"],
    "Travel": ["Rail ticket", "Hotel booking", "Intercity bus"],
    "Income": ["Monthly salary", "Freelance payment", "Scholarship stipend"],
    "Transfers": ["Self transfer", "Credit card payment"],
    "Refunds": ["Shopping refund", "Travel refund"],
}

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def make_transactions() -> list[dict]:
    rows = []
    for month_offset in range(12):
        first = date(2025, 10, 1)
        month_index = (first.month - 1 + month_offset) % 12 + 1
        year = first.year + (first.month - 1 + month_offset) // 12
        month_start = date(year, month_index, 1)
        rows.append({"date": month_start.isoformat(), "description": "Monthly salary",
                     "amount": f"{RNG.randrange(48000, 76000, 1000)}.00", "direction": "credit",
                     "type": "income", "category": "Income", "currency": "INR"})
        for _ in range(13):
            category = RNG.choice(list(CATEGORIES.keys())[:-3])
            description = RNG.choice(CATEGORIES[category])
            amount = RNG.randrange(80, 6000, 10)
            day = min(RNG.randint(2, 27), 28)
            rows.append({"date": date(year, month_index, day).isoformat(), "description": description,
                         "amount": f"{amount}.00", "direction": "debit", "type": "expense",
                         "category": category, "currency": "INR"})
        if month_offset % 4 == 0:
            rows.append({"date": date(year, month_index, 19).isoformat(), "description": "Self transfer",
                         "amount": "3000.00", "direction": "debit", "type": "transfer",
                         "category": "Transfers", "currency": "INR"})
    return sorted(rows, key=lambda row: row["date"])

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    transactions = make_transactions()
    write_csv(OUT / "transactions.csv", transactions,
              ["date", "description", "amount", "direction", "type", "category", "currency"])
    labeled = []
    for category, descriptions in CATEGORIES.items():
        for _ in range(35):
            labeled.append({"description": RNG.choice(descriptions), "category": category})
    RNG.shuffle(labeled)
    split = int(len(labeled) * 0.8)
    write_csv(OUT / "categorization_train.csv", labeled[:split], ["description", "category"])
    write_csv(OUT / "categorization_test.csv", labeled[split:], ["description", "category"])

    anomaly_rows = []
    for row in transactions:
        amount = float(row["amount"])
        anomalous = row["category"] == "Food and dining" and amount > 4000
        anomaly_rows.append({"amount": f"{amount:.2f}", "category": row["category"],
                             "is_anomaly": int(anomalous)})
    anomaly_rows.extend([
        {"amount": "24000.00", "category": "Food and dining", "is_anomaly": 1},
        {"amount": "120000.00", "category": "Shopping", "is_anomaly": 1},
    ])
    write_csv(OUT / "anomaly_evaluation.csv", anomaly_rows, ["amount", "category", "is_anomaly"])
    (OUT / "rag_evaluation.json").write_text(json.dumps([
        {"question": "How does compound interest work?", "expected_document": "compound-interest"},
        {"question": "What can I do to plan a budget?", "expected_document": "budgeting-basics"},
        {"question": "What should I check when comparing loan offers?", "expected_document": "loan-comparison"},
        {"question": "How do I protect my UPI PIN?", "expected_document": "digital-safety"},
        {"question": "What is the capital of France?", "expected_document": None},
    ], indent=2), encoding="utf-8")

    statement = fitz.open()
    page = statement.new_page()
    page.insert_text((42, 38), "FICTIONAL TEST STATEMENT — NO REAL ACCOUNT")
    page.insert_text((42, 62), "Date          Description                         Amount   Dr/Cr")
    sample = [
        ("01/09/2026", "Monthly salary ACME", "58000.00 CR"),
        ("02/09/2026", "Swiggy order", "450.50 DR"),
        ("05/09/2026", "Metro card recharge", "300.00 DR"),
        ("07/09/2026", "Electricity bill", "1840.00 DR"),
    ]
    for index, (day, description, value) in enumerate(sample):
        page.insert_text((42, 88 + index * 20), f"{day} {description} {value}")
    statement.save(OUT / "bank_statement_sample.pdf")
    statement.close()
    (OUT / "README.md").write_text(
        "# Synthetic data\n\nAll records and statement rows are generated fictional examples. "
        "The PDFs are marked as fictional test statements and contain no real account identifiers.\n\n"
        "Regenerate the files from the repository root with:\n\n"
        "```powershell\npython scripts/generate_synthetic_data.py\n```\n\n"
        "The fixed seed is 706. Synthetic categorization and anomaly metrics are not evidence of real-world performance.\n",
        encoding="utf-8",
    )
    print(f"Generated {len(transactions)} synthetic transactions in {OUT}")

if __name__ == "__main__":
    main()
