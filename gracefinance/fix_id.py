from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE checkin_responses ALTER COLUMN id SET DEFAULT gen_random_uuid()"))
    conn.commit()
print("Done")
