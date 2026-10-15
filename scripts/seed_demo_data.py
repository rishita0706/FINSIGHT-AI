from __future__ import annotations

import csv
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from argon2 import PasswordHasher
from sqlalchemy import select
from app.db import Base, SessionLocal, engine
from app.logic import fingerprint
from app.models import Transaction, User

def main() -> None:
    email, password = os.getenv("DEMO_EMAIL"), os.getenv("DEMO_PASSWORD")
    if not email or not password or len(password) < 10:
        raise SystemExit("Set DEMO_EMAIL and DEMO_PASSWORD (at least 10 characters) before seeding.")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.casefold()))
        if user is None:
            user = User(email=email.casefold(), password_hash=PasswordHasher().hash(password))
            db.add(user)
            db.flush()
        with (ROOT / "data" / "synthetic" / "transactions.csv").open(encoding="utf-8", newline="") as handle:
            imported = 0
            for row in csv.DictReader(handle):
                tx_date = date.fromisoformat(row["date"])
                amount = Decimal(row["amount"])
                tx_fingerprint = fingerprint(tx_date, row["description"], amount, row["direction"])
                if db.scalar(select(Transaction.id).where(
                    Transaction.user_id == user.id, Transaction.fingerprint == tx_fingerprint
                )):
                    continue
                db.add(Transaction(user_id=user.id, date=tx_date, description=row["description"], amount=amount,
                                   direction=row["direction"], tx_type=row["type"], category=row["category"],
                                   category_source="rule", source="demo", fingerprint=tx_fingerprint))
                imported += 1
        db.commit()
        print(f"Seeded {imported} synthetic transactions for {user.email}.")

if __name__ == "__main__":
    main()
