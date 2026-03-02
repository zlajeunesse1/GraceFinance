"""Add GCI slope, volatility, and trend columns to daily_indexes

Revision ID: 002_index_engine_v1_1
Revises: 001_data_engine
Create Date: 2026-02-18

Adds:
    - gci_slope_3d: OLS slope of GCI over last 3 days (Numeric 7,4)
    - gci_slope_7d: OLS slope of GCI over last 7 days (Numeric 7,4)
    - gci_volatility_7d: Population std dev of GCI over last 7 days (Numeric 7,4)
    - trend_direction: UP / DOWN / FLAT classification (String 10)
"""

from alembic import op
import sqlalchemy as sa

revision = "002_index_engine_v1_1"
down_revision = "001_data_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "daily_indexes",
        sa.Column("gci_slope_3d", sa.Numeric(7, 4), nullable=True),
    )
    op.add_column(
        "daily_indexes",
        sa.Column("gci_slope_7d", sa.Numeric(7, 4), nullable=True),
    )
    op.add_column(
        "daily_indexes",
        sa.Column("gci_volatility_7d", sa.Numeric(7, 4), nullable=True),
    )
    op.add_column(
        "daily_indexes",
        sa.Column("trend_direction", sa.String(10), nullable=True, server_default="FLAT"),
    )


def downgrade() -> None:
    op.drop_column("daily_indexes", "trend_direction")
    op.drop_column("daily_indexes", "gci_volatility_7d")
    op.drop_column("daily_indexes", "gci_slope_7d")
    op.drop_column("daily_indexes", "gci_slope_3d")
