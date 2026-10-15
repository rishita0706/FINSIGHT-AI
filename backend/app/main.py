import hashlib, secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import logic
from .db import Base, engine, get_db
from .models import AuthSession, ImportJob, Transaction, User, now

Base.metadata.create_all(engine)  # dev convenience; Alembic migrations are still TODO
app = FastAPI(title="FinSight AI API", version="0.1.0")
ph = PasswordHasher()
COOKIE, SESSION_DAYS, MAX_UPLOAD = "fs_session", 7, 2_000_000

@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    # Basic CSRF defence: state-changing requests need a custom header (+ SameSite=Lax cookie).
    if request.method in {"POST", "PATCH", "PUT", "DELETE"} and request.headers.get("x-requested-with") != "FinSight":
        return JSONResponse({"detail": "Missing CSRF header"}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "no-store"
    return resp

def _hash(tok: str) -> str: return hashlib.sha256(tok.encode()).hexdigest()

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    tok = request.cookies.get(COOKIE)
    s = db.get(AuthSession, _hash(tok)) if tok else None
    if not s or s.expires_at.replace(tzinfo=s.expires_at.tzinfo or now().tzinfo) < now():
        raise HTTPException(401, "Not authenticated")
    return db.get(User, s.user_id)

class Creds(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/api/v1/auth/register", status_code=201)
def register(c: Creds, db: Session = Depends(get_db)):
    u = User(email=c.email.lower(), password_hash=ph.hash(c.password))
    db.add(u)
    try: db.commit()
    except IntegrityError:
        raise HTTPException(409, "Could not register with these details")
    return {"id": u.id, "email": u.email}

@app.post("/api/v1/auth/login")
def login(c: Creds, response: Response, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == c.email.lower()))
    try:
        ok = bool(u) and ph.verify(u.password_hash, c.password)
    except VerifyMismatchError:
        ok = False
    if not ok: raise HTTPException(401, "Invalid email or password")
    tok = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_hash(tok), user_id=u.id, expires_at=now() + timedelta(days=SESSION_DAYS)))
    db.commit()
    response.set_cookie(COOKIE, tok, httponly=True, samesite="lax", secure=False, max_age=SESSION_DAYS * 86400)  # secure=True in prod
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
    category: str | None = None
    tx_type: Literal["expense", "income", "transfer", "refund"] | None = None

class TxPatch(BaseModel):
    description: str | None = Field(None, min_length=1, max_length=300)
    category: str | None = None
    tx_type: Literal["expense", "income", "transfer", "refund"] | None = None

def tx_out(t: Transaction) -> dict:
    return {"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": str(t.amount),
            "currency": "INR", "direction": t.direction, "tx_type": t.tx_type, "category": t.category,
            "category_source": t.category_source, "source": t.source}

def owned_tx(db, u, tid) -> Transaction:
    t = db.scalar(select(Transaction).where(Transaction.id == tid, Transaction.user_id == u.id))
    if not t: raise HTTPException(404, "Transaction not found")  # 404 (not 403) avoids ID enumeration
    return t

@app.post("/api/v1/transactions", status_code=201)
def create_tx(b: TxIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    cat, typ = logic.categorize(b.description)
    if b.direction == "credit" and typ == "expense": typ = "income"
    t = Transaction(user_id=u.id, date=b.date, description=b.description, amount=b.amount, direction=b.direction,
                    category=b.category or cat, category_source="user" if b.category else "rule",
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

@app.get("/api/v1/transactions/{tid}")
def get_tx(tid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return tx_out(owned_tx(db, u, tid))

@app.patch("/api/v1/transactions/{tid}")
def patch_tx(tid: str, b: TxPatch, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = owned_tx(db, u, tid)
    for k, v in b.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(t, k, v)
        if k == "category": t.category_source = "user"
    db.commit()
    return tx_out(t)

@app.delete("/api/v1/transactions/{tid}", status_code=204)
def del_tx(tid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_tx(db, u, tid)); db.commit()

@app.post("/api/v1/imports", status_code=201)
async def upload_import(file: UploadFile = File(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD: raise HTTPException(413, "File too large (max 2 MB)")
    if raw[:5] == b"%PDF-":
        raise HTTPException(501, "PDF import is not implemented yet in this build; use CSV.")
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: raise HTTPException(422, "File is not valid UTF-8 CSV")
    try: rows = logic.parse_csv(text)
    except ValueError as e: raise HTTPException(422, str(e))
    existing = set(db.scalars(select(Transaction.fingerprint).where(Transaction.user_id == u.id)))
    seen = set()
    for r in rows:
        if r["status"] == "ok":
            if r["fingerprint"] in existing or r["fingerprint"] in seen:
                r["status"] = "duplicate"
            seen.add(r["fingerprint"])
    if not any(r["status"] in ("ok", "duplicate") for r in rows):
        raise HTTPException(422, "No importable rows found")
    job = ImportJob(user_id=u.id, filename=(file.filename or "upload.csv")[:100], rows=rows)
    db.add(job); db.commit()
    return {"id": job.id, "status": job.status, "rows": rows}

def owned_job(db, u, jid) -> ImportJob:
    j = db.scalar(select(ImportJob).where(ImportJob.id == jid, ImportJob.user_id == u.id))
    if not j: raise HTTPException(404, "Import not found")
    return j

@app.get("/api/v1/imports/{jid}/preview")
def preview(jid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    j = owned_job(db, u, jid); return {"id": j.id, "status": j.status, "rows": j.rows}

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
                               category=r["category"], source="csv", fingerprint=r["fingerprint"]))
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
