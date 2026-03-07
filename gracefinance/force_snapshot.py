import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)
db = Session()

user_id = uuid.UUID("da326919-278e-417d-928b-3c0d551151db")

# Import and run snapshot computation
from app.services.checkin_service import compute_user_snapshot
snapshot = compute_user_snapshot(db, user_id)

print(f"FCS Raw:       {snapshot.fcs_raw}")
print(f"FCS Composite: {snapshot.fcs_composite}")
print(f"FCS Confidence:{snapshot.fcs_confidence}")
print(f"Stability:     {snapshot.current_stability}")
print(f"Outlook:       {snapshot.future_outlook}")
print(f"Purch Power:   {snapshot.purchasing_power}")
print(f"Emerg Ready:   {snapshot.emergency_readiness}")
print(f"Agency:        {snapshot.financial_agency}")
print(f"BSI:           {snapshot.bsi_score}")
print(f"Checkin Count: {snapshot.checkin_count}")

db.close()