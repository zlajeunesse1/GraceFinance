"""add_daily_index_trend_columns

Revision ID: d356e648897b
Revises: a45a74c54f5b
Create Date: 2026-02-23 20:21:07.322245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd356e648897b'
down_revision: Union[str, Sequence[str], None] = 'c65541317e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('daily_index', sa.Column('gci_slope_3d', sa.Numeric(7, 4), nullable=True))
    op.add_column('daily_index', sa.Column('gci_slope_7d', sa.Numeric(7, 4), nullable=True))
    op.add_column('daily_index', sa.Column('gci_volatility_7d', sa.Numeric(7, 4), nullable=True))
    op.add_column('daily_index', sa.Column('trend_direction', sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column('daily_index', 'trend_direction')
    op.drop_column('daily_index', 'gci_volatility_7d')
    op.drop_column('daily_index', 'gci_slope_7d')
    op.drop_column('daily_index', 'gci_slope_3d')