"""
Run this script to add the new Book columns to the existing PostgreSQL `books` table.
It uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` so it is safe to re-run.

Usage (PowerShell):
    python migrate_add_book_fields.py

It uses the `engine` from `database.py` in this repo, so ensure your DATABASE_URL in `database.py` is correct.
Make a backup of your DB before running.
"""

from sqlalchemy import text
from database import engine

sql_statements = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS accession_number VARCHAR(100);",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS publisher VARCHAR(200);",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS edition VARCHAR(100);",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS genre VARCHAR(100);",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS language VARCHAR(50);",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS pages INTEGER;",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS price NUMERIC;",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS date_of_purchase DATE;",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS current_status VARCHAR(50) DEFAULT 'Available';",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS shelf_number VARCHAR(100);",
    # Keep schema aligned with SQLAlchemy model (models.Book.owner_id)
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS owner_id INTEGER;",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS image_url VARCHAR(1024);",
]

print("Running book-fields migration...")
with engine.connect() as conn:
    for sql in sql_statements:
        print("Executing:", sql)
        try:
            conn.execute(text(sql))
        except Exception as e:
            print("Warning: statement failed:", e)
            # continue through statements; user will be shown warnings
    # Commit if using transactional DDL (Postgres does autocommit for DDL but keep consistent)
    try:
        conn.commit()
    except Exception:
        pass
print("Migration finished. If you want unique indexes (accession_number/isbn), create them manually after ensuring there are no duplicates.")
print("To check duplicates, run in psql:")
print("  SELECT isbn, count(*) FROM books GROUP BY isbn HAVING count(*) > 1;")
print("  SELECT accession_number, count(*) FROM books GROUP BY accession_number HAVING count(*) > 1;")
print("If there are no duplicates, you can create unique indexes:")
print("  CREATE UNIQUE INDEX ux_books_accession_number ON books(accession_number);")
print("  CREATE UNIQUE INDEX ux_books_isbn ON books(isbn);")