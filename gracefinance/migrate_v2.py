"""
FCS v2 Database Migration
═════════════════════════
Run ONCE from your gracefinance/ directory:
    python migrate_v2.py

Renames columns in daily_index and user_metric_snapshots.
Updates dimension values in checkin_responses.
New feed tables auto-create via Base.metadata.create_all() on server start.
"""

from app.database import engine
from sqlalchemy import text

MIGRATIONS = [
    # 1. Rename DailyIndex columns
    "ALTER TABLE daily_index RENAME COLUMN fcs_emergency_readiness TO fcs_debt_pressure",
    "ALTER TABLE daily_index RENAME COLUMN fcs_income_adequacy TO fcs_financial_agency",

    # 2. Rename UserMetricSnapshot columns
    "ALTER TABLE user_metric_snapshots RENAME COLUMN emergency_readiness TO debt_pressure",
    "ALTER TABLE user_metric_snapshots RENAME COLUMN income_adequacy TO financial_agency",

    # 3. Update existing checkin_responses dimension values
    "UPDATE checkin_responses SET dimension = 'debt_pressure' WHERE dimension = 'emergency_readiness'",
    "UPDATE checkin_responses SET dimension = 'financial_agency' WHERE dimension = 'income_adequacy'",
]


def run():
    print("Running FCS v2 database migration...\n")

    with engine.connect() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                print(f"  OK  {sql[:70]}...")
            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg or "already exists" in error_msg:
                    print(f"  SKIP (already done): {sql[:60]}...")
                else:
                    print(f"  ERR: {error_msg}")
        conn.commit()

    print("\nMigration complete!")
    print("New feed tables will auto-create when you start the backend.")
    print("Run: uvicorn main:app --reload --port 8000")


if __name__ == "__main__":
    run()