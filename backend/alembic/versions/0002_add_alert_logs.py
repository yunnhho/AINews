"""add alert_logs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-27 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent_via", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_alert_logs_created", "alert_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_alert_logs_created", table_name="alert_logs")
    op.drop_table("alert_logs")
