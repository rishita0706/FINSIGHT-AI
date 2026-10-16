"""Create the initial FinSight relational schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("tx_type", sa.String(), nullable=False, server_default="expense"),
        sa.Column("category", sa.String(), nullable=False, server_default="Other"),
        sa.Column("category_source", sa.String(), nullable=False, server_default="rule"),
        sa.Column("category_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "fingerprint", name="uq_transactions_user_fingerprint"),
        sa.CheckConstraint("amount > 0", name="ck_transactions_positive_amount"),
        sa.CheckConstraint("direction IN ('debit', 'credit')", name="ck_transactions_direction"),
        sa.CheckConstraint("tx_type IN ('expense', 'income', 'transfer', 'refund')", name="ck_transactions_type"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="preview"),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False, server_default="csv"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('uploaded', 'parsed', 'preview', 'confirmed', 'expired', 'failed')",
            name="ck_import_jobs_status",
        ),
    )
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"])
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.UniqueConstraint("user_id", "category", "period_start", name="uq_budgets_user_category_period"),
        sa.CheckConstraint("amount > 0", name="ck_budgets_positive_amount"),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("target_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("saved_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.CheckConstraint("target_amount > 0", name="ck_savings_goals_positive_target"),
        sa.CheckConstraint("saved_amount >= 0", name="ck_savings_goals_nonnegative_saved"),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])
    op.create_table(
        "recurring_status",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="candidate"),
        sa.UniqueConstraint("user_id", "merchant", name="uq_recurring_status_user_merchant"),
    )
    op.create_index("ix_recurring_status_user_id", "recurring_status", ["user_id"])
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("currency", sa.String(), nullable=False, server_default="INR"),
        sa.Column("timezone", sa.String(), nullable=False, server_default="Asia/Kolkata"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index("ix_recurring_status_user_id", table_name="recurring_status")
    op.drop_table("recurring_status")
    op.drop_index("ix_savings_goals_user_id", table_name="savings_goals")
    op.drop_table("savings_goals")
    op.drop_index("ix_budgets_user_id", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index("ix_import_jobs_user_id", table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
