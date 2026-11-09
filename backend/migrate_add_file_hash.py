"""
migrate_add_file_hash.py
-------------------------
Migration script to:
1. Add `file_hash` column to `lectures` and `media_files`.
2. Compute and backfill SHA-256 hashes for existing lecture media files in `backend/mindtrace.db`.
3. Create unique index on `lectures(file_hash)` safely.
4. Create index on `media_files(file_hash)`.

Safe to run multiple times.
"""

import os
import sqlite3
import hashlib

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BACKEND_DIR, "mindtrace.db")

def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols

def index_exists(cursor, index_name: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None

def compute_file_hash(filepath: str) -> str | None:
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"  [!] Error reading {filepath}: {e}")
        return None

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"[migrate_file_hash] Database not found at {DB_PATH}.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Add file_hash to lectures
    if not column_exists(cur, "lectures", "file_hash"):
        print("  [+] Adding column lectures.file_hash ...")
        cur.execute("ALTER TABLE lectures ADD COLUMN file_hash VARCHAR(64)")
    else:
        print("  [=] Column lectures.file_hash already exists.")

    # 2. Add file_hash to media_files
    if not column_exists(cur, "media_files", "file_hash"):
        print("  [+] Adding column media_files.file_hash ...")
        cur.execute("ALTER TABLE media_files ADD COLUMN file_hash VARCHAR(64)")
    else:
        print("  [=] Column media_files.file_hash already exists.")

    conn.commit()

    # 3. Backfill existing media files and lectures
    # Prioritize lectures with ready status and transcripts
    cur.execute("""
        SELECT m.lecture_id, m.id, m.file_path, m.original_filename, l.status, LENGTH(COALESCE(t.full_text, '')) as t_len
        FROM media_files m
        JOIN lectures l ON m.lecture_id = l.id
        LEFT JOIN transcripts t ON l.id = t.lecture_id
        ORDER BY (CASE WHEN l.status = 'ready' THEN 1 ELSE 0 END) DESC, t_len DESC, m.lecture_id ASC
    """)
    rows = cur.fetchall()
    print(f"\n[migrate_file_hash] Evaluating {len(rows)} existing media files for hash backfill...")

    seen_hashes = set()
    for lec_id, media_id, file_path, orig_name, status_val, _ in rows:
        # Resolve real path
        real_path = file_path
        if not os.path.isabs(real_path):
            real_path = os.path.join(BACKEND_DIR, real_path)
        if not os.path.exists(real_path):
            # Check relative to backend/uploads
            alt_path = os.path.join(BACKEND_DIR, "uploads", os.path.basename(file_path))
            if os.path.exists(alt_path):
                real_path = alt_path

        h = compute_file_hash(real_path)
        if h:
            # Update media_file hash
            cur.execute("UPDATE media_files SET file_hash = ? WHERE id = ?", (h, media_id))
            
            # For lectures, only set file_hash on the first/primary lecture for each unique hash
            # so the UNIQUE index constraint is satisfied while preserving historical records
            if h not in seen_hashes and status_val != 'failed':
                cur.execute("UPDATE lectures SET file_hash = ? WHERE id = ?", (h, lec_id))
                seen_hashes.add(h)
                print(f"  [*] Canonical Lecture ID {lec_id} ('{orig_name}') assigned hash {h[:16]}...")
            else:
                # Existing duplicate lecture keeps file_hash = NULL to allow unique index
                cur.execute("UPDATE lectures SET file_hash = NULL WHERE id = ?", (lec_id,))
                print(f"  [.] Duplicate/Failed Lecture ID {lec_id} kept with NULL hash (preserves unique index)")

    conn.commit()

    # 4. Create unique composite index on lectures(user_id, file_hash)
    print("\n[migrate_file_hash] Ensuring composite unique index uq_lectures_user_file_hash on lectures(user_id, file_hash)...")
    cur.execute("DROP INDEX IF EXISTS idx_lectures_file_hash")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_lectures_user_file_hash ON lectures(user_id, file_hash)")

    # 5. Create index on media_files(file_hash)
    print("[migrate_file_hash] Ensuring index idx_media_files_file_hash on media_files(file_hash)...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_media_files_file_hash ON media_files(file_hash)")

    conn.commit()
    conn.close()
    print("[migrate_file_hash] Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
