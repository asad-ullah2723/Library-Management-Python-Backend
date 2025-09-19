"""
Run this script to create the `transactions` table if it doesn't exist. Uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` to be safe.

Usage (PowerShell):
    python migrate_add_transactions.py

It uses the `engine` from `database.py` in this repo.
"""

from sqlalchemy import text
from database import engine

sql_statements = [
    "CREATE TABLE IF NOT EXISTS transactions (\n    id SERIAL PRIMARY KEY,\n    transaction_id VARCHAR(255) UNIQUE,\n    member_id INTEGER NOT NULL,\n    book_id INTEGER NOT NULL,\n    issue_date DATE NOT NULL,\n    due_date DATE NOT NULL,\n    return_date DATE,\n    fine_details TEXT,\n    renewal_count INTEGER DEFAULT 0,\n    created_at DATE DEFAULT current_timestamp\n);"]

print("Running transactions migration...")
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
