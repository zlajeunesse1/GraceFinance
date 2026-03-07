from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check current columns
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'user_metric_snapshots'
        ORDER BY column_name
    """))
    cols = [row[0] for row in result]
    print("Current columns:", cols)

    # Rename if needed
    if "debt_pressure" in cols and "emergency_readiness" not in cols:
        conn.execute(text("ALTER TABLE user_metric_snapshots RENAME COLUMN debt_pressure TO emergency_readiness"))
        print("Renamed debt_pressure -> emergency_readiness")

    if "fcs_raw" not in cols:
        conn.execute(text("ALTER TABLE user_metric_snapshots ADD COLUMN fcs_raw FLOAT"))
        print("Added fcs_raw")

    if "fcs_confidence" not in cols:
        conn.execute(text("ALTER TABLE user_metric_snapshots ADD COLUMN fcs_confidence FLOAT NOT NULL DEFAULT 0.0"))
        print("Added fcs_confidence")

    if "bsi_shock" not in cols:
        conn.execute(text("ALTER TABLE user_metric_snapshots ADD COLUMN bsi_shock BOOLEAN NOT NULL DEFAULT FALSE"))
        print("Added bsi_shock")

    conn.commit()
    print("All done.")