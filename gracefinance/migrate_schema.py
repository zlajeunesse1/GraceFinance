"""
GraceFinance — Database Migration Script
Run this ONCE to update your existing database schema.

Usage:
    cd gracefinance-backend
    python migrate_schema.py

What this does:
  1. Adds new columns to users table (email_verified, onboarding_completed, etc.)
  2. Changes Float → Numeric(12,2) on all money columns
  3. Drops the old daily_indexes table (if the duplicate exists)
  4. Creates new tables (user_metric_snapshots, daily_index)
  5. Adds missing indexes

IMPORTANT: This script uses ALTER TABLE directly. Back up your database first:
    pg_dump gracefinance > backup_before_migration.sql
"""

import sys
from sqlalchemy import create_engine, text, inspect

# Import your settings to get the database URL
sys.path.insert(0, ".")
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)


def run_migration():
    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        print("=" * 60)
        print("GraceFinance Schema Migration")
        print("=" * 60)

        # ── 1. Users table: add new columns ──
        print("\n[1/6] Updating users table...")
        users_columns = [col["name"] for col in inspector.get_columns("users")]

        if "email_verified" not in users_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            print("  + Added email_verified")

        if "onboarding_completed" not in users_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            print("  + Added onboarding_completed")

        if "onboarding_goals" not in users_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN onboarding_goals JSONB"
            ))
            print("  + Added onboarding_goals")

        if "last_checkin_at" not in users_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN last_checkin_at TIMESTAMPTZ"
            ))
            print("  + Added last_checkin_at")

        # ── 2. Float → Numeric on money columns ──
        print("\n[2/6] Converting Float → Numeric(12,2) on money columns...")

        money_columns = [
            ("users", "monthly_income"),
            ("users", "monthly_expenses"),
            ("debts", "balance"),
            ("debts", "min_payment"),
            ("debts", "credit_limit"),
            ("transactions", "amount"),
            ("bills", "amount"),
        ]

        for table, column in money_columns:
            if table in existing_tables:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                        ALTER COLUMN {column}
                        TYPE NUMERIC(12,2)
                        USING {column}::NUMERIC(12,2)
                    """))
                    print(f"  ✓ {table}.{column} → Numeric(12,2)")
                except Exception as e:
                    print(f"  ⚠ {table}.{column}: {e}")

        # ── 3. Handle duplicate daily_indexes table ──
        print("\n[3/6] Checking for duplicate daily_indexes table...")
        if "daily_indexes" in existing_tables:
            conn.execute(text("DROP TABLE IF EXISTS daily_indexes CASCADE"))
            print("  ✓ Dropped old daily_indexes table (duplicate)")
        else:
            print("  - No duplicate found")

        # ── 4. Create missing tables ──
        print("\n[4/6] Creating missing tables...")

        if "checkin_responses" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE checkin_responses (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    question_id VARCHAR(10) NOT NULL,
                    dimension VARCHAR(30) NOT NULL,
                    question_text TEXT NOT NULL,
                    raw_value INTEGER NOT NULL,
                    scale_max INTEGER NOT NULL DEFAULT 5,
                    normalized_value FLOAT NOT NULL,
                    checkin_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_weekly BOOLEAN NOT NULL DEFAULT FALSE
                )
            """))
            print("  ✓ Created checkin_responses")

        if "user_metric_snapshots" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE user_metric_snapshots (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    current_stability NUMERIC(5,2) NOT NULL DEFAULT 0,
                    future_outlook NUMERIC(5,2) NOT NULL DEFAULT 0,
                    purchasing_power NUMERIC(5,2) NOT NULL DEFAULT 0,
                    emergency_readiness NUMERIC(5,2) NOT NULL DEFAULT 0,
                    income_adequacy NUMERIC(5,2) NOT NULL DEFAULT 0,
                    fcs_composite NUMERIC(5,2) NOT NULL DEFAULT 0,
                    bsi_score NUMERIC(6,2),
                    checkin_count INTEGER NOT NULL DEFAULT 0
                )
            """))
            print("  ✓ Created user_metric_snapshots")

        if "daily_index" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE daily_index (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    index_date DATE NOT NULL,
                    segment VARCHAR(50) NOT NULL DEFAULT 'national',
                    spi_value NUMERIC(5,2),
                    fcs_value NUMERIC(5,2) NOT NULL,
                    bsi_value NUMERIC(6,2),
                    fcs_current_stability NUMERIC(5,2) NOT NULL DEFAULT 0,
                    fcs_future_outlook NUMERIC(5,2) NOT NULL DEFAULT 0,
                    fcs_purchasing_power NUMERIC(5,2) NOT NULL DEFAULT 0,
                    fcs_emergency_readiness NUMERIC(5,2) NOT NULL DEFAULT 0,
                    fcs_income_adequacy NUMERIC(5,2) NOT NULL DEFAULT 0,
                    gf_rwi_composite NUMERIC(5,2) NOT NULL DEFAULT 0,
                    user_count INTEGER NOT NULL DEFAULT 0,
                    checkin_volume INTEGER NOT NULL DEFAULT 0,
                    avg_mood_score NUMERIC(4,2),
                    gci_slope_3d NUMERIC(7,4),
                    gci_slope_7d NUMERIC(7,4),
                    gci_volatility_7d NUMERIC(7,4),
                    trend_direction VARCHAR(10) DEFAULT 'FLAT',
                    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_daily_index_date_segment UNIQUE (index_date, segment)
                )
            """))
            print("  ✓ Created daily_index")

        # ── 5. Create indexes ──
        print("\n[5/6] Creating indexes...")

        indexes_to_create = [
            ("ix_checkin_resp_user_id", "checkin_responses", "user_id"),
            ("ix_checkin_resp_date", "checkin_responses", "checkin_date"),
            ("ix_checkin_resp_dimension", "checkin_responses", "dimension"),
            ("ix_user_metric_user_id", "user_metric_snapshots", "user_id"),
            ("ix_user_metric_computed", "user_metric_snapshots", "computed_at"),
            ("ix_daily_index_date", "daily_index", "index_date"),
            ("ix_daily_index_segment", "daily_index", "segment"),
            ("ix_debts_user_id", "debts", "user_id"),
            ("ix_bills_user_id", "bills", "user_id"),
        ]

        composite_indexes = [
            ("ix_checkin_resp_user_date", "checkin_responses", "user_id, checkin_date"),
            ("ix_user_metric_user_computed", "user_metric_snapshots", "user_id, computed_at"),
            ("ix_transactions_user_date", "transactions", "user_id, date"),
        ]

        for idx_name, table, column in indexes_to_create:
            if table in existing_tables or table in ["checkin_responses", "user_metric_snapshots", "daily_index"]:
                try:
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"
                    ))
                    print(f"  ✓ {idx_name}")
                except Exception as e:
                    print(f"  ⚠ {idx_name}: {e}")

        for idx_name, table, columns in composite_indexes:
            if table in existing_tables or table in ["checkin_responses", "user_metric_snapshots"]:
                try:
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})"
                    ))
                    print(f"  ✓ {idx_name}")
                except Exception as e:
                    print(f"  ⚠ {idx_name}: {e}")

        # ── 6. Add ondelete CASCADE to existing FKs that are missing it ──
        print("\n[6/6] Updating foreign key constraints...")
        # PostgreSQL requires dropping and recreating FKs to add ON DELETE CASCADE
        # We'll skip this for now — the model-level cascade handles it in SQLAlchemy
        print("  - Model-level cascade configured (SQLAlchemy handles deletes)")

        conn.commit()

        print("\n" + "=" * 60)
        print("Migration complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart uvicorn")
        print("  2. Hit /docs to verify all endpoints")
        print("  3. Test: POST /auth/signup → GET /checkin/questions → POST /checkin/submit")


if __name__ == "__main__":
    run_migration()