"""
migrate_misconception_lifecycle.py
----------------------------------
Migration script to add the lifecycle columns to the misconceptions table:
- status (TEXT DEFAULT 'open')
- improving_at (DATE DEFAULT NULL)
- recheck_due (DATE DEFAULT NULL)
- relapse_count (INTEGER DEFAULT 0)

Safe to run multiple times. Checks if each column already exists before adding.
Existing rows are updated to status 'open'.
"""

import sqlite3
import os
import shutil

DB_PATH = os.path.join(os.path.dirname(__file__), "mindtrace.db")
BACKUP_PATH = os.path.join(os.path.dirname(__file__), "mindtrace_backup_step1.db")

def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"[migrate] Database not found at {DB_PATH}.")
        return

    # Ensure backup exists
    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"[migrate] Created backup at {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Count records before migration to verify preservation
    cur.execute("SELECT COUNT(*) FROM misconceptions")
    count_before = cur.fetchone()[0]
    print(f"[migrate] Misconceptions count before migration: {count_before}")

    # 2. Check and add columns
    lifecycle_columns = [
        ("status", "ALTER TABLE misconceptions ADD COLUMN status TEXT DEFAULT 'open'"),
        ("improving_at", "ALTER TABLE misconceptions ADD COLUMN improving_at DATE DEFAULT NULL"),
        ("recheck_due", "ALTER TABLE misconceptions ADD COLUMN recheck_due DATE DEFAULT NULL"),
        ("relapse_count", "ALTER TABLE misconceptions ADD COLUMN relapse_count INTEGER DEFAULT 0"),
    ]

    for col_name, sql in lifecycle_columns:
        if column_exists(cur, "misconceptions", col_name):
            print(f"[migrate] Column misconceptions.{col_name} already exists. Skipping.")
        else:
            print(f"[migrate] Adding column misconceptions.{col_name}...")
            cur.execute(sql)
            conn.commit()

    # 3. Update existing rows so they have status = 'open' and relapse_count default
    print("[migrate] Updating existing rows to have status = 'open'...")
    cur.execute("UPDATE misconceptions SET status = 'open' WHERE status IS NULL OR status = 'Unresolved' OR status = ''")
    cur.execute("UPDATE misconceptions SET relapse_count = 0 WHERE relapse_count IS NULL")
    conn.commit()

    # 4. Verify existing records preserved
    cur.execute("SELECT COUNT(*) FROM misconceptions")
    count_after = cur.fetchone()[0]
    print(f"[migrate] Misconceptions count after migration: {count_after}")
    assert count_before == count_after, f"Record count mismatch! Before: {count_before}, After: {count_after}"

    # 5. Print schema
    cur.execute("PRAGMA table_info(misconceptions)")
    print("\n[migrate] Final misconceptions table structure:")
    for row in cur.fetchall():
        print(f"  - {row[1]} ({row[2]}), default={row[4]}")

    conn.close()
    print("\n[migrate] Migration completed successfully!")

if __name__ == "__main__":
    run_migration()

