"""
Migration script to add question types and difficulty columns:
- checkpoints: difficulty VARCHAR(20) DEFAULT 'easy'
- checkpoints: scenario_text TEXT NULL
- checkpoint_attempts: grade VARCHAR(20) NULL
"""
import sqlite3
import os
import sys

# Find database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mindtrace.db")

def migrate():
    print(f"Applying migration to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}. Will be initialized by app.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check checkpoints table columns
    cursor.execute("PRAGMA table_info(checkpoints)")
    checkpoint_cols = [row[1] for row in cursor.fetchall()]

    if "difficulty" not in checkpoint_cols:
        print("Adding column 'difficulty' to 'checkpoints' table...")
        cursor.execute("ALTER TABLE checkpoints ADD COLUMN difficulty VARCHAR(20) DEFAULT 'easy'")
        cursor.execute("UPDATE checkpoints SET difficulty = 'easy' WHERE difficulty IS NULL")
        print("  -> 'difficulty' column added with default 'easy'.")
    else:
        print("Column 'difficulty' already exists in 'checkpoints'.")

    if "scenario_text" not in checkpoint_cols:
        print("Adding column 'scenario_text' to 'checkpoints' table...")
        cursor.execute("ALTER TABLE checkpoints ADD COLUMN scenario_text TEXT NULL")
        print("  -> 'scenario_text' column added.")
    else:
        print("Column 'scenario_text' already exists in 'checkpoints'.")

    # 2. Check checkpoint_attempts table columns
    cursor.execute("PRAGMA table_info(checkpoint_attempts)")
    attempt_cols = [row[1] for row in cursor.fetchall()]

    if "grade" not in attempt_cols:
        print("Adding column 'grade' to 'checkpoint_attempts' table...")
        cursor.execute("ALTER TABLE checkpoint_attempts ADD COLUMN grade VARCHAR(20) NULL")
        print("  -> 'grade' column added.")
    else:
        print("Column 'grade' already exists in 'checkpoint_attempts'.")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()

