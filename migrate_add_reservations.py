"""
Run this script to create the `reservations` table if it doesn't exist.

Usage (PowerShell):
    python migrate_add_reservations.py

It uses the `engine` from `database.py` in this repo.
"""

from sqlalchemy import text
from database import engine

sql_statements = [
    "CREATE TABLE IF NOT EXISTS reservations (\n    id SERIAL PRIMARY KEY,\n    reservation_id VARCHAR(255) UNIQUE,\n    book_id INTEGER NOT NULL,\n    member_id INTEGER NOT NULL,\n    reservation_date DATE NOT NULL,\n    status VARCHAR(50) DEFAULT 'Active',\n    created_at DATE DEFAULT current_timestamp\n);"]

print("Running reservations migration...")
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
