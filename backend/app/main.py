import asyncio, copy, csv, hashlib, io, json, os, re, secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import case, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from . import logic
from .assistant import answer_financial_question
from .anomaly import find_anomaly_candidates
from .categorization import predict_category
from .db import Base, engine, get_db
from .integrations.llm import ProviderError, get_provider, phrase_verified
from .integrations.financial_data import get_provider as get_financial_data_provider
from .knowledge import DOCUMENTS, answer_knowledge_question
from .models import (
    AuthRateLimit, AuthSession, Budget, Conversation, ImportJob, KnowledgeChunk,
    KnowledgeDocument, Message, ModelRun, RecurringStatus, SavingsGoal,
    Transaction, User, UserSettings, now,
)
from .pdf_import import parse_pdf_with_timeout

if os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true":
    Base.metadata.create_all(engine)
app = FastAPI(title="FinSight AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Requested-With"],
)
ph = PasswordHasher()
COOKIE, SESSION_DAYS, MAX_UPLOAD = "fs_session", 7, 2_000_000
DateType = date


def enforce_auth_rate_limit(request: Request, email: str, db: Session) -> None:
    key = request.client.host if request.client else "unknown"
    cutoff = now() - timedelta(minutes=5)
    attempted_at = now()
    ip_key = hashlib.sha256(f"ip:{key}".encode()).hexdigest()
    account_key = hashlib.sha256(f"account:{email.casefold()}".encode()).hexdigest()
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    counts = []
    for limit_key, limit in ((ip_key, 100), (account_key, 10)):
        statement = insert(AuthRateLimit).values(
            key=limit_key, attempts=1, window_started_at=attempted_at,
        )
        expired = AuthRateLimit.window_started_at < cutoff
        statement = statement.on_conflict_do_update(
            index_elements=[AuthRateLimit.key],
            set_={
                "attempts": case((expired, 1), else_=AuthRateLimit.attempts + 1),
                "window_started_at": case((expired, attempted_at), else_=AuthRateLimit.window_started_at),
            },
        ).returning(AuthRateLimit.attempts)
        counts.append((db.scalar(statement), limit))
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.window_started_at < cutoff))
    db.commit()
    if any(attempts > limit for attempts, limit in counts):
        raise HTTPException(429, "Too many authentication attempts. Try again in a few minutes.")

@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    # Basic CSRF defence: state-changing requests need a custom header (+ SameSite=Lax cookie).
    if request.method in {"POST", "PATCH", "PUT", "DELETE"} and request.headers.get("x-requested-with") != "FinSight":
        resp = JSONResponse({"detail": "Missing CSRF header"}, status_code=403)
    else:
        resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Cache-Control"] = "no-store"
    if request.url.path in {"/docs", "/redoc", "/docs/oauth2-redirect"}:
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
    else:
        resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if os.getenv("COOKIE_SECURE", "").casefold() == "true":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp

def _hash(tok: str) -> str: return hashlib.sha256(tok.encode()).hexdigest()

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    tok = request.cookies.get(COOKIE)
    s = db.get(AuthSession, _hash(tok)) if tok else None
    if not s or s.expires_at.replace(tzinfo=s.expires_at.tzinfo or now().tzinfo) < now():
        raise HTTPException(401, "Not authenticated")
    user = db.get(User, s.user_id)
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return user

class Creds(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/api/v1/auth/register", status_code=201)
def register(c: Creds, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, c.email, db)
    u = User(email=c.email.lower(), password_hash=ph.hash(c.password))
    db.add(u)
    try: db.commit()
    except IntegrityError:
        raise HTTPException(409, "Could not register with these details")
    return {"id": u.id, "email": u.email}

@app.post("/api/v1/auth/login")
def login(c: Creds, response: Response, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, c.email, db)
    u = db.scalar(select(User).where(User.email == c.email.lower()))
    try:
        ok = bool(u) and ph.verify(u.password_hash, c.password)
    except VerifyMismatchError:
        ok = False
    if not ok: raise HTTPException(401, "Invalid email or password")
    old_token = request.cookies.get(COOKIE)
    if old_token:
        old_session = db.get(AuthSession, _hash(old_token))
        if old_session:
            db.delete(old_session)
    tok = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_hash(tok), user_id=u.id, expires_at=now() + timedelta(days=SESSION_DAYS)))
    db.commit()
    response.set_cookie(COOKIE, tok, httponly=True, samesite="lax",
                        secure=os.getenv("COOKIE_SECURE", "").casefold() == "true",
                        max_age=SESSION_DAYS * 86400)
    return {"id": u.id, "email": u.email}

@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    tok = request.cookies.get(COOKIE)
    if tok and (s := db.get(AuthSession, _hash(tok))):
        db.delete(s); db.commit()
    response.delete_cookie(COOKIE)

@app.get("/api/v1/auth/me")
def me(u: User = Depends(current_user)): return {"id": u.id, "email": u.email}

class TxIn(BaseModel):
    date: date
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    direction: Literal["debit", "credit"]
    category: str | None = Field(None, min_length=1, max_length=80)
    tx_type: Literal["expense", "income", "transfer", "refund"] | None = None

class TxPatch(BaseModel):
    date: DateType | None = None
    description: str | None = Field(None, min_length=1, max_length=300)
    amount: Decimal | None = Field(None, gt=0, max_digits=14, decimal_places=2)
    direction: Literal["debit", "credit"] | None = None
    category: str | None = Field(None, min_length=1, max_length=80)
    tx_type: Literal["expense", "income", "transfer", "refund"] | None = None

def tx_out(t: Transaction) -> dict:
    return {"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": str(t.amount),
            "currency": "INR", "direction": t.direction, "tx_type": t.tx_type, "category": t.category,
            "category_source": t.category_source, "category_confidence": str(t.category_confidence) if t.category_confidence is not None else None,
            "source": t.source}

def owned_tx(db, u, tid) -> Transaction:
    t = db.scalar(select(Transaction).where(Transaction.id == tid, Transaction.user_id == u.id))
    if not t: raise HTTPException(404, "Transaction not found")  # 404 (not 403) avoids ID enumeration
    return t

def user_today(db: Session, user: User) -> date:
    settings = db.get(UserSettings, user.id)
    timezone = settings.timezone if settings else "Asia/Kolkata"
    return datetime.now(ZoneInfo(timezone)).date()

def timestamp_before(value: datetime, cutoff: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < cutoff

@app.post("/api/v1/transactions", status_code=201)
def create_tx(b: TxIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    cat, typ, category_source, confidence = predict_category(b.description)
    if b.direction == "credit" and typ == "expense": typ = "income"
    t = Transaction(user_id=u.id, date=b.date, description=b.description, amount=b.amount, direction=b.direction,
                    category=b.category or cat, category_source="user" if b.category else category_source,
                    category_confidence=Decimal(confidence) if confidence else None,
                    tx_type=b.tx_type or typ, source="manual",
                    fingerprint=logic.fingerprint(b.date, b.description, b.amount, b.direction))
    db.add(t)
    try: db.commit()
    except IntegrityError:
        raise HTTPException(409, "Duplicate transaction")
    return tx_out(t)

@app.get("/api/v1/transactions")
def list_tx(u: User = Depends(current_user), db: Session = Depends(get_db), q: str | None = None,
            start: date | None = None, end: date | None = None, category: str | None = None,
            page: int = 1, page_size: int = 50):
    page_size = max(1, min(page_size, 200))
    stmt = select(Transaction).where(Transaction.user_id == u.id)
    if q: stmt = stmt.where(Transaction.description.ilike(f"%{q}%"))
    if start: stmt = stmt.where(Transaction.date >= start)
    if end: stmt = stmt.where(Transaction.date <= end)
    if category: stmt = stmt.where(Transaction.category == category)
    rows = db.scalars(stmt.order_by(Transaction.date.desc(), Transaction.id)).all()
    pg = max(1, page)
    return {"total": len(rows), "page": pg, "items": [tx_out(t) for t in rows[(pg - 1) * page_size: pg * page_size]]}

@app.get("/api/v1/transactions/export")
def export_transactions(u: User = Depends(current_user), db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "description", "amount", "direction", "type", "category", "currency"])
    for tx in db.scalars(select(Transaction).where(Transaction.user_id == u.id).order_by(Transaction.date)):
        writer.writerow([tx.date.isoformat(), tx.description, tx.amount, tx.direction, tx.tx_type, tx.category, "INR"])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="finsight-transactions.csv"'})

@app.get("/api/v1/transactions/{tid}")
def get_tx(tid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return tx_out(owned_tx(db, u, tid))

@app.patch("/api/v1/transactions/{tid}")
def patch_tx(tid: str, b: TxPatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = owned_tx(db, u, tid)
    for k, v in b.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(t, k, v)
        if k == "category":
            t.category_source = "user"
            t.category_confidence = None
    t.fingerprint = logic.fingerprint(t.date, t.description, t.amount, t.direction)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Updated transaction duplicates an existing record")
    return tx_out(t)

@app.delete("/api/v1/transactions/{tid}", status_code=204)
def del_tx(tid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_tx(db, u, tid)); db.commit()

@app.post("/api/v1/imports", status_code=201)
async def upload_import(file: UploadFile = File(...), password: str | None = Form(None),
                        u: User = Depends(current_user), db: Session = Depends(get_db)):
    expire_preview_jobs(db, u.id)
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD: raise HTTPException(413, "File too large (max 2 MB)")
    warnings = []
    if raw.startswith(b"%PDF-"):
        if file.content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(415, "The file content does not match a PDF statement")
        try:
            rows, warnings = await asyncio.to_thread(parse_pdf_with_timeout, raw, password, 15)
        except TimeoutError as e:
            raise HTTPException(422, "PDF parsing exceeded the 15-second limit") from e
        except ValueError as e:
            raise HTTPException(422, str(e))
        except RuntimeError as e:
            raise HTTPException(422, "The PDF parser could not process this document") from e
        source_type = "pdf"
    else:
        if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"}:
            raise HTTPException(415, "Upload a CSV file or a text-based PDF statement")
        try: text = raw.decode("utf-8-sig")
        except UnicodeDecodeError: raise HTTPException(422, "File is not valid UTF-8 CSV")
        try: rows = logic.parse_csv(text)
        except ValueError as e: raise HTTPException(422, str(e))
        source_type = "csv"
    for row in rows:
        if row["status"] == "ok":
            category, tx_type, category_source, confidence = predict_category(row["description"])
            if row["direction"] == "credit" and tx_type == "expense":
                tx_type = "refund" if category != "Other" else "income"
            row.update(category=category, tx_type=tx_type, category_source=category_source,
                       category_confidence=confidence)
    existing = set(db.scalars(select(Transaction.fingerprint).where(Transaction.user_id == u.id)))
    seen = set()
    for r in rows:
        if r["status"] == "ok":
            if r["fingerprint"] in existing or r["fingerprint"] in seen:
                r["status"] = "duplicate"
            seen.add(r["fingerprint"])
    if not any(r["status"] in ("ok", "duplicate") for r in rows):
        raise HTTPException(422, "No importable rows found")
    job = ImportJob(user_id=u.id, filename=(file.filename or f"upload.{source_type}")[:100],
                    rows=rows, warnings=warnings, source_type=source_type)
    db.add(job); db.commit()
    return {"id": job.id, "status": job.status, "source_type": source_type, "confidence": "review_required",
            "warnings": warnings, "rows": rows}

def owned_job(db, u, jid) -> ImportJob:
    j = db.scalar(select(ImportJob).where(ImportJob.id == jid, ImportJob.user_id == u.id))
    if not j: raise HTTPException(404, "Import not found")
    return j

def expire_preview_jobs(db: Session, user_id: str) -> None:
    cutoff = now() - timedelta(hours=24)
    previews = db.scalars(select(ImportJob).where(
        ImportJob.user_id == user_id, ImportJob.status == "preview"
    )).all()
    expired = [job for job in previews if timestamp_before(job.created_at, cutoff)]
    for job in expired:
        db.delete(job)
    if expired:
        db.commit()

@app.get("/api/v1/imports/{jid}/preview")
def preview(jid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    j = owned_job(db, u, jid)
    if j.status == "preview" and timestamp_before(j.created_at, now() - timedelta(hours=24)):
        db.delete(j); db.commit()
        raise HTTPException(410, "This import preview expired. Upload the statement again.")
    return {"id": j.id, "status": j.status, "source_type": j.source_type,
            "warnings": j.warnings, "rows": j.rows}

class ImportRowPatch(BaseModel):
    line: int = Field(ge=1)
    date: DateType | None = None
    description: str | None = Field(None, min_length=1, max_length=300)
    amount: Decimal | None = Field(None, gt=0, max_digits=14, decimal_places=2)
    direction: Literal["debit", "credit"] | None = None
    category: str | None = Field(None, min_length=1, max_length=80)
    tx_type: Literal["expense", "income", "transfer", "refund"] | None = None

class ImportReviewPatch(BaseModel):
    rows: list[ImportRowPatch] = Field(min_length=1, max_length=5000)

@app.patch("/api/v1/imports/{jid}/preview")
def correct_preview(jid: str, body: ImportReviewPatch, u: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    job = owned_job(db, u, jid)
    if job.status != "preview":
        raise HTTPException(409, "Only imports awaiting review can be edited")
    rows = copy.deepcopy(job.rows)
    for correction in body.rows:
        target = next((row for row in rows if row.get("line") == correction.line), None)
        if not target or target["status"] not in {"ok", "error"}:
            raise HTTPException(422, f"Line {correction.line} cannot be corrected")
        changes = correction.model_dump(exclude_unset=True, exclude={"line"})
        target.update({key: str(value) if isinstance(value, (date, Decimal)) else value for key, value in changes.items()})
        if "category" in changes:
            target["category_source"] = "user"
            target["category_confidence"] = None
        if all(target.get(key) for key in ("date", "description", "amount", "direction")):
            amount = Decimal(str(target["amount"]))
            target.update(status="ok", errors=[], amount=str(amount),
                          fingerprint=logic.fingerprint(target["date"], target["description"], amount, target["direction"]))
    job.rows = rows
    db.commit()
    return {"id": job.id, "status": job.status, "rows": job.rows, "warnings": job.warnings}

@app.get("/api/v1/imports")
def list_imports(u: User = Depends(current_user), db: Session = Depends(get_db)):
    expire_preview_jobs(db, u.id)
    jobs = db.scalars(select(ImportJob).where(ImportJob.user_id == u.id).order_by(ImportJob.created_at.desc())).all()
    return [{"id": job.id, "filename": job.filename, "status": job.status, "source_type": job.source_type,
             "created_at": job.created_at.isoformat()} for job in jobs]

@app.get("/api/v1/imports/{jid}")
def get_import(jid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    job = owned_job(db, u, jid)
    return {"id": job.id, "filename": job.filename, "status": job.status,
            "source_type": job.source_type, "created_at": job.created_at.isoformat()}

@app.delete("/api/v1/imports/{jid}", status_code=204)
def delete_import(jid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_job(db, u, jid)); db.commit()

@app.post("/api/v1/imports/{jid}/confirm")
def confirm(jid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    j = owned_job(db, u, jid)
    if j.status == "confirmed": raise HTTPException(409, "Already confirmed")
    imported = 0
    skipped = len([r for r in j.rows if r["status"] != "ok"])
    try:  # single DB transaction: all-or-nothing
        for r in j.rows:
            if r["status"] != "ok": continue
            db.add(Transaction(user_id=u.id, date=date.fromisoformat(r["date"]), description=r["description"],
                               amount=Decimal(r["amount"]), direction=r["direction"], tx_type=r["tx_type"],
                               category=r["category"], category_source=r.get("category_source", "rule"),
                               category_confidence=Decimal(r["category_confidence"]) if r.get("category_confidence") else None,
                               source=j.source_type, fingerprint=r["fingerprint"]))
            imported += 1
        j.status = "confirmed"; j.rows = []  # drop parsed content after import
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Import conflicts with existing data; nothing was saved")
    return {"imported": imported, "skipped": skipped, "status": "confirmed"}

@app.get("/api/v1/analytics/overview")
def analytics(u: User = Depends(current_user), db: Session = Depends(get_db), start: date | None = None, end: date | None = None):
    stmt = select(Transaction).where(Transaction.user_id == u.id)
    if start: stmt = stmt.where(Transaction.date >= start)
    if end: stmt = stmt.where(Transaction.date <= end)
    return {"start": start, "end": end, **logic.overview(db.scalars(stmt).all())}

@app.get("/api/v1/analytics/cash-flow")
def cash_flow(u: User = Depends(current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(Transaction).where(Transaction.user_id == u.id)).all()
    months: dict[str, dict[str, Decimal]] = {}
    for tx in txs:
        key = tx.date.strftime("%Y-%m")
        bucket = months.setdefault(key, {"income": Decimal(0), "expenses": Decimal(0)})
        if tx.tx_type == "transfer":
            continue
        bucket["income" if tx.direction == "credit" else "expenses"] += tx.amount
    return [{"month": month, "income": str(values["income"]), "expenses": str(values["expenses"]),
             "net": str(values["income"] - values["expenses"])} for month, values in sorted(months.items())]

@app.get("/api/v1/analytics/categories")
def category_analytics(start: date | None = None, end: date | None = None,
                       u: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Transaction).where(Transaction.user_id == u.id, Transaction.direction == "debit",
                                     Transaction.tx_type != "transfer")
    if start: query = query.where(Transaction.date >= start)
    if end: query = query.where(Transaction.date <= end)
    totals: dict[str, Decimal] = {}
    for tx in db.scalars(query):
        totals[tx.category] = totals.get(tx.category, Decimal(0)) + tx.amount
    return [{"category": key, "amount": str(value)} for key, value in sorted(totals.items(), key=lambda item: -item[1])]

@app.get("/api/v1/analytics/monthly-comparison")
def monthly_comparison(u: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = cash_flow(u, db)
    if len(rows) < 2:
        return {"available": False, "message": "At least two months of transactions are needed."}
    previous, current = rows[-2:]
    old, new = Decimal(previous["expenses"]), Decimal(current["expenses"])
    return {"available": True, "previous_month": previous["month"], "current_month": current["month"],
            "previous_expenses": str(old), "current_expenses": str(new), "change": str(new - old),
            "partial_current_month": current["month"] == user_today(db, u).strftime("%Y-%m")}



class AssistantQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


def _verified_assistant_answer(db: Session, user: User, question: str) -> dict:
    try:
        provider = get_provider()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    retrieval_failed = False
    warnings = []
    financial_intent = re.search(
        r"\b(spend|expense|income|transaction|category|cash flow|recurring|payment|save|savings|goal|largest|merchant|month)\b",
        question,
        re.IGNORECASE,
    )
    education_intent = re.search(
        r"\b(compound interest|budget|emergency fund|credit card|loan|inflation|fraud|digital banking|saving habit)\b",
        question,
        re.IGNORECASE,
    )
    def answer_education() -> dict:
        nonlocal retrieval_failed
        try:
            return answer_knowledge_question(question, db, provider)
        except ProviderError:
            retrieval_failed = True
            db.rollback()
            return answer_knowledge_question(question, provider=provider)

    if financial_intent and education_intent:
        personal = answer_financial_question(db, user.id, question, user_today(db, user))
        education = answer_education()
        result = {
            "mode": "combined",
            "answer": (
                "Your financial data\n\n" + personal["answer"]
                + "\n\nGeneral education\n\n" + education["answer"]
            ),
            "calculation": personal.get("calculation"),
            "citations": education.get("citations", []),
            "sections": [
                {
                    "kind": "personal_finance",
                    "title": "Your financial data",
                    "answer": personal["answer"],
                    "calculation": personal.get("calculation"),
                    "citations": [],
                },
                {
                    "kind": "education",
                    "title": "General education",
                    "answer": education["answer"],
                    "calculation": None,
                    "citations": education.get("citations", []),
                },
            ],
        }
        warnings.extend(education.get("warnings", []))
    elif education_intent:
        result = answer_education()
    elif financial_intent:
        result = answer_financial_question(db, user.id, question, user_today(db, user))
    else:
        result = answer_education()

    try:
        phrased = phrase_verified(provider, result["answer"])
        result["answer"] = phrased.text
        db.add(ModelRun(
            user_id=user.id,
            provider=provider.name,
            model=provider.model,
            purpose="assistant_phrase",
            input_tokens=phrased.input_tokens,
            output_tokens=phrased.output_tokens,
            succeeded=True,
        ))
    except ProviderError:
        db.add(ModelRun(
            user_id=user.id, provider=provider.name, model=provider.model,
            purpose="assistant_phrase", input_tokens=0, output_tokens=0, succeeded=False,
        ))
        warnings.append("Optional LLM phrasing was unavailable; the verified answer is shown unchanged.")
    if retrieval_failed:
        db.add(ModelRun(
            user_id=user.id, provider=provider.name, model=provider.model,
            purpose="assistant_retrieval", input_tokens=0, output_tokens=0, succeeded=False,
        ))
        warnings.append("The optional LLM service was unavailable; verified local results are shown.")
    if warnings:
        result["warnings"] = list(dict.fromkeys(warnings))
    db.commit()
    return result


@app.post("/api/v1/assistant/query")
def assistant_query(body: AssistantQuestion, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return _verified_assistant_answer(db, u, body.question)


def conversation_out(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


def owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    ))
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    return conversation


@app.get("/api/v1/conversations")
def list_conversations(u: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Conversation).where(Conversation.user_id == u.id)
        .order_by(Conversation.updated_at.desc())
    ).all()
    return [conversation_out(item) for item in items]


@app.post("/api/v1/conversations", status_code=201)
def create_conversation(u: User = Depends(current_user), db: Session = Depends(get_db)):
    conversation = Conversation(user_id=u.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation_out(conversation)


@app.get("/api/v1/conversations/{conversation_id}")
def get_conversation(conversation_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    conversation = owned_conversation(db, u, conversation_id)
    messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at, Message.id)
    ).all()
    return {
        **conversation_out(conversation),
        "messages": [{
            "id": item.id,
            "role": item.role,
            "content": item.content,
            "calculation": item.calculation,
            "citations": item.citations,
            "sections": item.sections,
            "created_at": item.created_at.isoformat(),
        } for item in messages],
    }


@app.post("/api/v1/conversations/{conversation_id}/messages", status_code=201)
def create_conversation_message(
    conversation_id: str,
    body: AssistantQuestion,
    u: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(db, u, conversation_id)
    question = Message(conversation_id=conversation.id, role="user", content=body.question)
    db.add(question)
    db.flush()
    answer = _verified_assistant_answer(db, u, body.question)
    response_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer["answer"],
        calculation=answer.get("calculation"),
        citations=answer.get("citations", []),
        sections=answer.get("sections", []),
    )
    conversation.title = body.question[:200]
    conversation.updated_at = now()
    db.add(response_message)
    db.commit()
    db.refresh(response_message)
    return {
        "user_message": {"id": question.id, "role": question.role, "content": question.content},
        "assistant_message": {
            "id": response_message.id,
            "role": response_message.role,
            "content": response_message.content,
            "calculation": response_message.calculation,
            "citations": response_message.citations,
            "sections": response_message.sections,
        },
        "warnings": answer.get("warnings", []),
    }


@app.delete("/api/v1/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    conversation = owned_conversation(db, u, conversation_id)
    db.execute(delete(Message).where(Message.conversation_id == conversation.id))
    db.delete(conversation)
    db.commit()

@app.get("/api/v1/knowledge/documents")
def list_knowledge_documents(u: User = Depends(current_user), db: Session = Depends(get_db)):
    documents = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.active.is_(True))).all()
    if not documents:
        return [{key: value for key, value in document.items() if key != "content"} for document in DOCUMENTS]
    return [{
        "id": document.external_id,
        "title": document.title,
        "topic": document.topic,
        "source_type": document.source_type,
        "source_url": document.source_url,
        "reference_url": document.reference_url,
        "version": document.version,
        "updated_at": document.updated_at.isoformat(),
    } for document in documents]


@app.get("/api/v1/knowledge/documents/{document_id}")
def get_knowledge_document(
    document_id: str,
    u: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    document = db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.external_id == document_id,
        KnowledgeDocument.active.is_(True),
    ))
    if document is not None:
        chunks = db.scalars(
            select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == document.id,
                KnowledgeChunk.version == document.version,
            ).order_by(KnowledgeChunk.chunk_index)
        ).all()
        return {
            "id": document.external_id,
            "title": document.title,
            "topic": document.topic,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "reference_url": document.reference_url,
            "version": document.version,
            "updated_at": document.updated_at.isoformat(),
            "content": "\n\n".join(chunk.content for chunk in chunks),
        }
    document = next((item for item in DOCUMENTS if item["id"] == document_id), None)
    if document is None: raise HTTPException(404, "Knowledge document not found")
    return document

class BudgetIn(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    period_start: date

    @field_validator("period_start")
    @classmethod
    def budget_starts_on_first(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Budget period_start must be the first day of a month")
        return value

@app.get("/api/v1/budgets")
def list_budgets(u: User = Depends(current_user), db: Session = Depends(get_db)):
    budgets = db.scalars(select(Budget).where(Budget.user_id == u.id)).all()
    results = []
    for item in budgets:
        next_period = date(item.period_start.year + (item.period_start.month == 12),
                           item.period_start.month % 12 + 1, 1)
        spent = sum((tx.amount for tx in db.scalars(select(Transaction).where(
            Transaction.user_id == u.id, Transaction.category == item.category, Transaction.direction == "debit",
            Transaction.tx_type != "transfer", Transaction.date >= item.period_start, Transaction.date < next_period
        ))), Decimal(0))
        results.append({"id": item.id, "category": item.category, "amount": str(item.amount),
                        "period_start": item.period_start.isoformat(), "spent": str(spent),
                        "usage": str((spent / item.amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))})
    return results

@app.post("/api/v1/budgets", status_code=201)
def create_budget(body: BudgetIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    item = Budget(user_id=u.id, **body.model_dump())
    db.add(item)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A budget for this category and period already exists")
    return {"id": item.id, "category": item.category, "amount": str(item.amount), "period_start": item.period_start.isoformat()}

@app.patch("/api/v1/budgets/{budget_id}")
def update_budget(budget_id: str, body: BudgetIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == u.id))
    if not item: raise HTTPException(404, "Budget not found")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    db.commit()
    return {"id": item.id, "category": item.category, "amount": str(item.amount), "period_start": item.period_start.isoformat()}

@app.delete("/api/v1/budgets/{budget_id}", status_code=204)
def delete_budget(budget_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == u.id))
    if not item: raise HTTPException(404, "Budget not found")
    db.delete(item); db.commit()

class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    saved_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    target_date: date | None = None

def goal_data(item: SavingsGoal) -> dict:
    return {"id": item.id, "name": item.name, "target_amount": str(item.target_amount),
            "saved_amount": str(item.saved_amount), "target_date": item.target_date.isoformat() if item.target_date else None,
            "progress": str(min(Decimal(1), item.saved_amount / item.target_amount))}

@app.get("/api/v1/goals")
def list_goals(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [goal_data(item) for item in db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == u.id))]

@app.post("/api/v1/goals", status_code=201)
def create_goal(body: GoalIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    item = SavingsGoal(user_id=u.id, **body.model_dump())
    db.add(item); db.commit()
    return goal_data(item)

@app.patch("/api/v1/goals/{goal_id}")
def update_goal(goal_id: str, body: GoalIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == u.id))
    if not item: raise HTTPException(404, "Savings goal not found")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    db.commit()
    return goal_data(item)

@app.delete("/api/v1/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == u.id))
    if not item: raise HTTPException(404, "Savings goal not found")
    db.delete(item); db.commit()

@app.get("/api/v1/recurring")
def recurring(u: User = Depends(current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(Transaction).where(Transaction.user_id == u.id, Transaction.direction == "debit",
                                               Transaction.tx_type != "transfer")).all()
    groups: dict[str, list[Transaction]] = {}
    for tx in txs:
        key = re.sub(r"[^a-z0-9 ]", "", tx.description.casefold()).strip()
        groups.setdefault(key, []).append(tx)
    statuses = {item.merchant: item.status for item in db.scalars(select(RecurringStatus).where(RecurringStatus.user_id == u.id))}
    output = []
    for merchant, items in groups.items():
        if len(items) < 2: continue
        dates = sorted(item.date for item in items)
        gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
        if not any(20 <= gap <= 40 or 80 <= gap <= 100 or 350 <= gap <= 380 for gap in gaps): continue
        status = statuses.get(merchant, "candidate")
        output.append({"merchant": merchant, "typical_amount": str(sum((i.amount for i in items), Decimal(0)) / len(items)),
                       "frequency": "monthly" if any(20 <= gap <= 40 for gap in gaps) else "periodic",
                       "last_observed": dates[-1].isoformat(), "confidence": "heuristic",
                       "status": status, "transaction_count": len(items)})
    return output

@app.post("/api/v1/recurring/{merchant}/confirm")
def confirm_recurring(merchant: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return set_recurring_status(merchant, "confirmed", u, db)

@app.post("/api/v1/recurring/{merchant}/dismiss")
def dismiss_recurring(merchant: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return set_recurring_status(merchant, "dismissed", u, db)

def set_recurring_status(merchant: str, status: str, u: User, db: Session):
    item = db.scalar(select(RecurringStatus).where(RecurringStatus.user_id == u.id, RecurringStatus.merchant == merchant))
    if item is None:
        item = RecurringStatus(user_id=u.id, merchant=merchant)
        db.add(item)
    item.status = status
    db.commit()
    return {"merchant": merchant, "status": status}

@app.get("/api/v1/insights")
def insights(u: User = Depends(current_user), db: Session = Depends(get_db)):
    comparison = monthly_comparison(u, db)
    items = []
    if comparison["available"]:
        change = Decimal(comparison["change"])
        if change:
            items.append({"title": "Month-to-month expense change",
                          "detail": f"Expenses changed by ₹{change:,.2f} compared with the previous recorded month.",
                          "method": "Difference between recorded debit totals; transfers excluded.",
                          "type": "comparison"})
    transactions = db.scalars(select(Transaction).where(Transaction.user_id == u.id)).all()
    return {"items": items, "anomaly_candidates": find_anomaly_candidates(transactions),
            "limitations": ["Insights describe recorded transactions only and do not establish causes. Unusual transactions are not proof of fraud."]}


@app.get("/api/v1/ml/categorizer/evaluation")
def categorizer_evaluation(u: User = Depends(current_user)):
    report = Path(__file__).resolve().parent / "ml" / "evaluation.json"
    if not report.is_file():
        return {
            "available": False,
            "message": "Categorizer evaluation is not available yet. Run scripts/evaluate_categorizer.py.",
        }
    return {"available": True, **json.loads(report.read_text(encoding="utf-8"))}


@app.get("/api/v1/forecasts")
def forecast(u: User = Depends(current_user), db: Session = Depends(get_db)):
    current_month = user_today(db, u).strftime("%Y-%m")
    rows = [row for row in cash_flow(u, db) if row["month"] < current_month]
    if len(rows) < 3:
        return {"available": False, "message": "At least three complete recorded months are needed for a simple baseline forecast."}
    previous = [Decimal(row["expenses"]) for row in rows[-3:]]
    average = sum(previous, Decimal(0)) / Decimal(len(previous))
    return {"available": True, "metric": "monthly_expenses", "currency": "INR", "estimate": str(average.quantize(Decimal("0.01"))),
            "method": "Mean of the last three recorded calendar months.", "history_months": [row["month"] for row in rows[-3:]],
            "warning": "Historical patterns do not guarantee future spending; this baseline is not a financial recommendation."}

@app.get("/api/v1/settings")
def get_settings(u: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = db.get(UserSettings, u.id)
    if settings is None:
        settings = UserSettings(user_id=u.id); db.add(settings); db.commit()
    return {
        "currency": settings.currency,
        "timezone": settings.timezone,
        "bank_connectivity": "not_available_in_mvp",
        "bank_connectivity_message": (
            "Live bank connections are unavailable in this MVP."
            if get_financial_data_provider() is None
            else "A financial-data provider is configured."
        ),
    }

class SettingsPatch(BaseModel):
    currency: Literal["INR"] | None = None
    timezone: str | None = Field(None, min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try: ZoneInfo(value)
            except ZoneInfoNotFoundError: raise ValueError("Enter a valid IANA timezone")
        return value

@app.patch("/api/v1/settings")
def patch_settings(body: SettingsPatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = db.get(UserSettings, u.id)
    if settings is None: settings = UserSettings(user_id=u.id); db.add(settings)
    for key, value in body.model_dump(exclude_unset=True).items(): setattr(settings, key, value)
    db.commit()
    return {
        "currency": settings.currency,
        "timezone": settings.timezone,
        "bank_connectivity": "not_available_in_mvp",
        "bank_connectivity_message": (
            "Live bank connections are unavailable in this MVP."
            if get_financial_data_provider() is None
            else "A financial-data provider is configured."
        ),
    }

@app.post("/api/v1/settings/export")
def export_data(u: User = Depends(current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(Transaction).where(Transaction.user_id == u.id)).all()
    imports = list_imports(u, db)
    return {"email": u.email, "transactions": [tx_out(item) for item in txs], "budgets": list_budgets(u, db),
            "goals": list_goals(u, db), "imports": imports, "generated_at": now().isoformat()}

@app.delete("/api/v1/settings/transactions", status_code=204)
def delete_transaction_history(u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(Transaction).where(Transaction.user_id == u.id))
    db.execute(delete(ImportJob).where(ImportJob.user_id == u.id))
    db.commit()

@app.delete("/api/v1/settings/account", status_code=204)
def delete_account(request: Request, response: Response, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(Transaction).where(Transaction.user_id == u.id))
    db.execute(delete(ImportJob).where(ImportJob.user_id == u.id))
    db.execute(delete(Budget).where(Budget.user_id == u.id))
    db.execute(delete(SavingsGoal).where(SavingsGoal.user_id == u.id))
    db.execute(delete(RecurringStatus).where(RecurringStatus.user_id == u.id))
    db.execute(delete(Message).where(Message.conversation_id.in_(
        select(Conversation.id).where(Conversation.user_id == u.id)
    )))
    db.execute(delete(Conversation).where(Conversation.user_id == u.id))
    db.execute(ModelRun.__table__.update().where(ModelRun.user_id == u.id).values(user_id=None))
    db.execute(delete(AuthSession).where(AuthSession.user_id == u.id))
    db.execute(delete(UserSettings).where(UserSettings.user_id == u.id))
    db.delete(u); db.commit()
    response.delete_cookie(COOKIE)

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(select(User.id).limit(1))
    except Exception:
        raise HTTPException(503, "Database is not ready")
    return {"status": "ready"}
