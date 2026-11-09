"""
Migration script to add 'prerequisite_lecture_id' column to 'lectures' table.
Sets ON DELETE SET NULL so deleting a prerequisite lecture sets the link to NULL.
"""
import sqlite3
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mindtrace.db")

def migrate():
    print(f"Target database file: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Database file does not exist yet at {DB_PATH}.")
        return

    # Create safety backup copy before modifying
    backup_path = DB_PATH + ".bak"
    shutil.copy2(DB_PATH, backup_path)
    print(f"Safety backup created at: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(lectures)")
    cols = [row[1] for row in cursor.fetchall()]

    if "prerequisite_lecture_id" not in cols:
        print("Adding 'prerequisite_lecture_id' column to 'lectures' table...")
        cursor.execute("ALTER TABLE lectures ADD COLUMN prerequisite_lecture_id INTEGER REFERENCES lectures(id) ON DELETE SET NULL")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_prerequisite ON lectures(prerequisite_lecture_id)")
        conn.commit()
        print("  -> Column 'prerequisite_lecture_id' added successfully with ON DELETE SET NULL.")
    else:
        print("Column 'prerequisite_lecture_id' already exists in 'lectures'.")

    conn.close()
    print("Migration finished successfully!")

if __name__ == "__main__":
    migrate()

