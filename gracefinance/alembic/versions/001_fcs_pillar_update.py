"""
Alembic Migration — FCS Pillar Update
══════════════════════════════════════
  - Renames debt_pressure → emergency_readiness in user_metric_snapshots
  - Adds fcs_raw column (pre-EMA score, for transparency)
  - Adds fcs_confidence column (data coverage %, 0–100)
  - Adds bsi_shock column (boolean flag for large single-session swings)

Revision: 001_fcs_pillar_update
Revises: <your previous head revision>
"""

from alembic import op
import sqlalchemy as sa


# ── Replace this with your actual previous revision ID ──────────────────────
revision = "001_fcs_pillar_update"
down_revision = "d356e648897b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Rename debt_pressure → emergency_readiness ────────────────────────
    op.alter_column(
        "user_metric_snapshots",
        "debt_pressure",
        new_column_name="emergency_readiness",
        existing_type=sa.Float(),
        nullable=True,
    )

    # ── 2. Add fcs_raw (pre-EMA composite, stored for audit/transparency) ────
    op.add_column(
        "user_metric_snapshots",
        sa.Column("fcs_raw", sa.Float(), nullable=True),
    )

    # ── 3. Add fcs_confidence (data coverage %, 0–100) ───────────────────────
    op.add_column(
        "user_metric_snapshots",
        sa.Column(
            "fcs_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )

    # ── 4. Add bsi_shock (True if single-session swing exceeded threshold) ───
    op.add_column(
        "user_metric_snapshots",
        sa.Column(
            "bsi_shock",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ── 5. Add index on fcs_composite for index aggregation performance ──────
    op.create_index(
        "ix_user_metric_snapshots_fcs_composite",
        "user_metric_snapshots",
        ["fcs_composite"],
    )

    # ── 6. Add index on computed_at for time-series queries ──────────────────
    op.create_index(
        "ix_user_metric_snapshots_computed_at",
        "user_metric_snapshots",
        ["computed_at"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        "ix_user_metric_snapshots_computed_at",
        table_name="user_metric_snapshots",
    )
    op.drop_index(
        "ix_user_metric_snapshots_fcs_composite",
        table_name="user_metric_snapshots",
    )

    # Drop new columns
    op.drop_column("user_metric_snapshots", "bsi_shock")
    op.drop_column("user_metric_snapshots", "fcs_confidence")
    op.drop_column("user_metric_snapshots", "fcs_raw")

    # Rename back
    op.alter_column(
        "user_metric_snapshots",
        "emergency_readiness",
        new_column_name="debt_pressure",
        existing_type=sa.Float(),
        nullable=True,
    )