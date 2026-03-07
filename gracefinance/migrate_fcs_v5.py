"""
Migration: Add three-component FCS formula columns + drift detection
Run from gracefinance/ directory:
    python migrate_fcs_v5.py

Adds to user_metric_snapshots:
  - fcs_behavior (Float) — behavior component 0-100
  - fcs_consistency (Float) — consistency component 0-100
  - fcs_trend (Float) — trend component 0-100
  - fcs_slope_7d (Float) — 7-day slope of fcs_composite
  - fcs_slope_30d (Float) — 30-day slope of fcs_composite
"""

from app.database import engine
from sqlalchemy import text


def run_migration():
    columns = [
        ("fcs_behavior", "FLOAT"),
        ("fcs_consistency", "FLOAT"),
        ("fcs_trend", "FLOAT"),
        ("fcs_slope_7d", "FLOAT"),
        ("fcs_slope_30d", "FLOAT"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns:
            conn.execute(text(
                f"ALTER TABLE user_metric_snapshots "
                f"ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
            ))
            print(f"  + {col_name} ({col_type})")

        conn.commit()

    print("\nMigration complete. 5 columns added to user_metric_snapshots.")


if __name__ == "__main__":
    run_migration()