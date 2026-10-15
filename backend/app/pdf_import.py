"""Best-effort text extraction for common text-based bank statement PDFs."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

import pymupdf as fitz

from . import logic

DATE_RE = re.compile(r"^(?P<date>\d{1,2}[-/ ](?:\d{1,2}|[A-Za-z]{3})[-/ ]\d{2,4})\s+(?P<body>.+)$")
AMOUNT_RE = re.compile(r"(?<!\S)(?:₹\s*)?[-(]?\d[\d,]*(?:\.\d{1,2})?\)?")
DATE_FORMATS = (*logic.DATE_FORMATS, "%d-%b-%Y", "%d %b %Y", "%d-%b-%y")


def _parse_statement_line(line: str, line_number: int) -> dict | None:
    match = DATE_RE.match(line.strip())
    if not match:
        return None
    try:
        tx_date = next(
            date_value
            for fmt in DATE_FORMATS
            if (date_value := _try_date(match.group("date"), fmt)) is not None
        )
    except StopIteration:
        return {"line": line_number, "status": "error", "errors": ["Unrecognised transaction date"]}

    body = match.group("body")
    amounts = list(AMOUNT_RE.finditer(body))
    if not amounts:
        return {"line": line_number, "status": "error", "errors": ["No transaction amount found"]}
    description = body[:amounts[0].start()].strip(" -|")
    if not description:
        return {"line": line_number, "status": "error", "errors": ["Transaction description is missing"]}
    tokens = [item.group().strip() for item in amounts]
    suffix = body[amounts[-1].end():].strip().upper()
    direction_marker = re.search(r"\b(DR|DEBIT|CR|CREDIT)\b", suffix)
    try:
        values = [Decimal(token.replace("₹", "").replace(",", "").replace("(", "-").replace(")", "")) for token in tokens]
    except InvalidOperation:
        return {"line": line_number, "status": "error", "errors": ["Invalid transaction amount"]}

    if len(values) >= 2:
        debit, credit = values[0], values[1]
        if (debit > 0) == (credit > 0):
            return {"line": line_number, "status": "error", "errors": ["Debit/credit columns are ambiguous"]}
        amount = debit if debit > 0 else credit
        direction = "debit" if debit > 0 else "credit"
    else:
        amount = abs(values[0])
        marker = direction_marker.group(1) if direction_marker else ""
        direction = "credit" if marker in {"CR", "CREDIT"} or values[0] < 0 else "debit"
    if amount <= 0:
        return {"line": line_number, "status": "error", "errors": ["Transaction amount must be positive"]}

    category, tx_type = logic.categorize(description)
    if direction == "credit" and tx_type == "expense":
        tx_type = "refund" if category != "Other" else "income"
    fingerprint = logic.fingerprint(tx_date, description, amount, direction)
    return {
        "line": line_number,
        "status": "ok",
        "errors": [],
        "date": tx_date.isoformat(),
        "description": description,
        "amount": str(amount),
        "direction": direction,
        "category": category,
        "tx_type": tx_type,
        "fingerprint": fingerprint,
    }


def _try_date(value: str, fmt: str) -> date | None:
    from datetime import datetime

    try:
        return datetime.strptime(value.strip(), fmt).date()
    except ValueError:
        return None


def parse_pdf(raw: bytes, password: str | None = None) -> tuple[list[dict], list[str]]:
    try:
        document = fitz.open(stream=raw, filetype="pdf")
    except (fitz.FileDataError, ValueError) as exc:
        raise ValueError("The uploaded file is not a readable PDF statement") from exc
    try:
        if document.page_count > 200:
            raise ValueError("Statement has too many pages (max 200)")
        if document.needs_pass and not document.authenticate(password or ""):
            raise ValueError("This PDF is password-protected. Enter the password for this import.")
        text = "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()

    if len(text.strip()) < 20:
        raise ValueError("No selectable text found. Scanned statements are not supported; use a text-based PDF or CSV.")

    rows: list[dict] = []
    warnings = ["Generic PDF parser: verify every row; bank statement layouts vary."]
    for line_number, line in enumerate(text.splitlines(), start=1):
        candidate = _parse_statement_line(line, line_number)
        if candidate is not None:
            rows.append(candidate)
    if len(rows) > logic.MAX_ROWS:
        raise ValueError(f"Too many transactions (max {logic.MAX_ROWS})")
    if not rows:
        raise ValueError("No transaction rows could be identified in this PDF. Try CSV or add transactions manually.")
    return rows, warnings
