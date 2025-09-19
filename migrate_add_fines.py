"""
Run this script to create the `fines` table if it doesn't exist.

Usage (PowerShell):
    python migrate_add_fines.py

It uses the `engine` from `database.py` in this repo.
"""

from sqlalchemy import text
from database import engine

sql_statements = [
    "CREATE TABLE IF NOT EXISTS fines (\n    id SERIAL PRIMARY KEY,\n    fine_id VARCHAR(255) UNIQUE,\n    member_id INTEGER NOT NULL,\n    amount NUMERIC NOT NULL,\n    reason VARCHAR(100) NOT NULL,\n    payment_status VARCHAR(20) DEFAULT 'Unpaid',\n    payment_date DATE,\n    created_at DATE DEFAULT current_timestamp\n);"]

print("Running fines migration...")
with engine.connect() as conn:
    for sql in sql_statements:
        print("Executing:", sql)
        try:
            conn.execute(text(sql))
        except Exception as e:
            print("Warning: statement failed:", e)
    try:
        conn.commit()
    except Exception:
        pass
print("Migration finished.")
