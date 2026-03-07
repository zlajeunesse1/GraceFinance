"""
Alembic Migration — Daily Index Trend Columns
══════════════════════════════════════════════
  - Adds gci_slope_3d to daily_index
  - Adds gci_slope_7d to daily_index
  - Adds gci_volatility_7d to daily_index
  - Adds trend_direction to daily_index (if missing)

Revision: 002_daily_index_trend_columns
Revises: 001_fcs_pillar_update
"""

from alembic import op
import sqlalchemy as sa


revision = "002_daily_index_trend_columns"
down_revision = "001_fcs_pillar_update"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "daily_index",
        sa.Column("gci_slope_3d", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_index",
        sa.Column("gci_slope_7d", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_index",
        sa.Column("gci_volatility_7d", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("daily_index", "gci_volatility_7d")
    op.drop_column("daily_index", "gci_slope_7d")
    op.drop_column("daily_index", "gci_slope_3d")
    op.drop_column("daily_index", "trend_direction")