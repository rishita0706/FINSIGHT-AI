import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid() -> str: return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)

class AuthSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # always positive
    direction: Mapped[str] = mapped_column(String)  # debit | credit
    tx_type: Mapped[str] = mapped_column(String, default="expense")  # expense|income|transfer|refund
    category: Mapped[str] = mapped_column(String, default="Other")
    category_source: Mapped[str] = mapped_column(String, default="rule")  # rule | user
    category_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    source: Mapped[str] = mapped_column(String, default="manual")  # manual|csv|demo
    fingerprint: Mapped[str] = mapped_column(String)

class ImportJob(Base):
    __tablename__ = "import_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String, default="preview")  # preview|confirmed
    filename: Mapped[str] = mapped_column(String)
    rows: Mapped[list] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    source_type: Mapped[str] = mapped_column(String, default="csv")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category", "period_start"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    period_start: Mapped[date] = mapped_column(Date)

class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    saved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

class RecurringStatus(Base):
    __tablename__ = "recurring_status"
    __table_args__ = (UniqueConstraint("user_id", "merchant"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    merchant: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="candidate")

class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    currency: Mapped[str] = mapped_column(String, default="INR")
    timezone: Mapped[str] = mapped_column(String, default="Asia/Kolkata")
