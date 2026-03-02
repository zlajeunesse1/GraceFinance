"""Add reward loop infrastructure: contribution queue + streak

Revision ID: 003_reward_loop
Revises: 002_index_engine_v1_1
Create Date: 2026-02-23

Adds:
    - index_contribution_queue table (append-only event log)
    - current_streak column on users table
    - last_checkin_date column on users table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003_reward_loop"
down_revision = "002_index_engine_v1_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Contribution queue: append-only event log --
    op.create_table(
        "index_contribution_queue",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("checkin_date", sa.Date, nullable=False),
        sa.Column("fcs_composite", sa.Numeric(5, 4), nullable=False),
        sa.Column("current_stability", sa.Numeric(5, 4), nullable=True),
        sa.Column("future_outlook", sa.Numeric(5, 4), nullable=True),
        sa.Column("purchasing_power", sa.Numeric(5, 4), nullable=True),
        sa.Column("emergency_readiness", sa.Numeric(5, 4), nullable=True),
        sa.Column("income_adequacy", sa.Numeric(5, 4), nullable=True),
        sa.Column("bsi_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_contrib_queue_status",
        "index_contribution_queue",
        ["status"],
    )
    op.create_index(
        "ix_contrib_queue_user_date",
        "index_contribution_queue",
        ["user_id", "checkin_date"],
        unique=True,
    )

    # -- Streak tracking on users --
    op.add_column(
        "users",
        sa.Column("current_streak", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("last_checkin_date", sa.Date, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_checkin_date")
    op.drop_column("users", "current_streak")
    op.drop_index("ix_contrib_queue_user_date", "index_contribution_queue")
    op.drop_index("ix_contrib_queue_status", "index_contribution_queue")
    op.drop_table("index_contribution_queue")
