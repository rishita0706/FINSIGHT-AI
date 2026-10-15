"""Deterministic finance logic: CSV parsing, categorisation fallback, analytics."""
import csv, hashlib, io
from datetime import datetime
from decimal import Decimal, InvalidOperation

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d/%m/%y"]
RULES = {
    "Food and dining": ["swiggy", "zomato", "restaurant", "cafe"],
    "Groceries": ["bigbasket", "blinkit", "dmart", "grocery"],
    "Transport": ["uber", "ola", "metro", "irctc", "fuel"],
    "Subscriptions": ["netflix", "spotify", "prime"],
    "Housing and utilities": ["rent", "electricity", "broadband", "airtel", "jio"],
    "Income": ["salary", "stipend"],
    "Transfers": ["transfer", "self", "cc payment", "credit card payment"],
}
MAX_ROWS = 5000

def categorize(desc: str) -> tuple[str, str]:
    d = desc.lower()
    for cat, kws in RULES.items():
        if any(k in d for k in kws):
            typ = "income" if cat == "Income" else "transfer" if cat == "Transfers" else "expense"
            return cat, typ
    return "Other", "expense"

def parse_date(s: str):
    for f in DATE_FORMATS:
        try: return datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    raise ValueError(f"Unrecognised date '{s}'")

def parse_amount(s: str) -> Decimal:
    s = (s or "").replace(",", "").replace("₹", "").strip()
    if not s: return Decimal(0)
    try: return Decimal(s)
    except InvalidOperation: raise ValueError(f"Invalid amount '{s}'")

def fingerprint(d, desc, amount, direction) -> str:
    return hashlib.sha256(f"{d}|{desc.strip().lower()}|{amount}|{direction}".encode()).hexdigest()[:32]

def _col(headers, *names):
    for h in headers:
        if h.strip().lower() in names: return h
    return None

def parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames: raise ValueError("CSV has no header row")
    h = reader.fieldnames
    dc, desc = _col(h, "date", "txn date", "transaction date"), _col(h, "description", "narration", "details")
    deb, cred, amt = _col(h, "debit", "withdrawal"), _col(h, "credit", "deposit"), _col(h, "amount")
    if not (dc and desc and (amt or deb or cred)):
        raise ValueError("Could not detect date, description and amount/debit/credit columns")
    out = []
    for i, r in enumerate(reader, start=2):
        if i > MAX_ROWS + 1: raise ValueError(f"Too many rows (max {MAX_ROWS})")
        row = {"line": i, "status": "ok", "errors": []}
        try:
            d = parse_date(r[dc]); description = (r[desc] or "").strip()
            if not description: raise ValueError("Empty description")
            if deb or cred:
                dv, cv = parse_amount(r.get(deb, "")), parse_amount(r.get(cred, ""))
                if (dv > 0) == (cv > 0): raise ValueError("Exactly one of debit/credit must be set")
                direction, amount = ("debit", dv) if dv > 0 else ("credit", cv)
            else:
                a = parse_amount(r[amt])
                if a == 0: raise ValueError("Zero amount")
                direction, amount = ("debit", -a) if a < 0 else ("credit", a)
            if amount <= 0: raise ValueError("Amount must be positive")
            cat, typ = categorize(description)
            if direction == "credit" and typ == "expense": typ = "refund" if cat != "Other" else "income"
            row.update(date=d.isoformat(), description=description, amount=str(amount), direction=direction,
                       category=cat, tx_type=typ, fingerprint=fingerprint(d, description, amount, direction))
        except (ValueError, KeyError) as e:
            row.update(status="error", errors=[str(e)])
        out.append(row)
    return out

def overview(txs) -> dict:
    """income = credits excluding transfers; expenses = debits excluding transfers; refunds reduce nothing
    (counted as income-side credits, documented). savings_rate = (income-expenses)/income, null if income==0."""
    inc = sum((t.amount for t in txs if t.direction == "credit" and t.tx_type != "transfer"), Decimal(0))
    exp = sum((t.amount for t in txs if t.direction == "debit" and t.tx_type != "transfer"), Decimal(0))
    cats: dict[str, Decimal] = {}
    for t in txs:
        if t.direction == "debit" and t.tx_type != "transfer":
            cats[t.category] = cats.get(t.category, Decimal(0)) + t.amount
    return {"currency": "INR", "income": str(inc), "expenses": str(exp), "net_cash_flow": str(inc - exp),
            "savings_rate": str(((inc - exp) / inc).quantize(Decimal("0.0001"))) if inc > 0 else None,
            "by_category": {k: str(v) for k, v in sorted(cats.items(), key=lambda x: -x[1])},
            "transaction_count": len(txs)}
