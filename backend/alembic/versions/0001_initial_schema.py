"""Create the FinSight MVP schema, including upgrades from the original prototype."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.db import Base
from app import models

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("import_jobs")}
    if "warnings" not in columns:
        op.add_column("import_jobs", sa.Column("warnings", sa.JSON(), nullable=True))
    if "source_type" not in columns:
        op.add_column("import_jobs", sa.Column("source_type", sa.String(), nullable=False, server_default="csv"))
    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "category_confidence" not in transaction_columns:
        op.add_column("transactions", sa.Column("category_confidence", sa.Numeric(5, 4), nullable=True))

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
