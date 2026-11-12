
"""
migrate_add_evidence_columns.py
-------------------------------
One-time migration script to add the new evidence-based resolution columns
and item-family columns to the existing SQLite database.

SQLite does NOT support ALTER TABLE ... ADD COLUMN with complex constraints,
but it DOES support adding nullable columns with defaults. That's all we need.

Run from the backend/ folder:
    python migrate_add_evidence_columns.py

Safe to run multiple times — it checks if each column already exists first.
"""

import sqlite3
import os

# Path to the database (same logic as config.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "mindtrace.db")

def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"[migrate] Database not found at {DB_PATH}. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    migrations = [
        # ── checkpoint_attempts ──────────────────────────────────────────────
        (
            "checkpoint_attempts",
            "confidence_level",
            "ALTER TABLE checkpoint_attempts ADD COLUMN confidence_level INTEGER"
        ),
        (
            "checkpoint_attempts",
            "explanation_text",
            "ALTER TABLE checkpoint_attempts ADD COLUMN explanation_text TEXT"
        ),
        (
            "checkpoint_attempts",
            "explanation_verdict",
            "ALTER TABLE checkpoint_attempts ADD COLUMN explanation_verdict TEXT DEFAULT 'not_checked'"
        ),
        (
            "checkpoint_attempts",
            "raw_llm_eval",
            "ALTER TABLE checkpoint_attempts ADD COLUMN raw_llm_eval TEXT"
        ),
        (
            "checkpoint_attempts",
            "hours_since_prev",
            "ALTER TABLE checkpoint_attempts ADD COLUMN hours_since_prev REAL"
        ),

        # ── misconceptions ───────────────────────────────────────────────────
        (
            "misconceptions",
            "evidence_status",
            "ALTER TABLE misconceptions ADD COLUMN evidence_status TEXT"
        ),
        (
            "misconceptions",
            "memorized_flag",
            "ALTER TABLE misconceptions ADD COLUMN memorized_flag INTEGER DEFAULT 0"
        ),
        (
            "misconceptions",
            "remediation_segment_id",
            "ALTER TABLE misconceptions ADD COLUMN remediation_segment_id INTEGER"
        ),
        (
            "misconceptions",
            "intervention_shown_at",
            "ALTER TABLE misconceptions ADD COLUMN intervention_shown_at TEXT"
        ),
        (
            "misconceptions",
            "resolved_at",
            "ALTER TABLE misconceptions ADD COLUMN resolved_at TEXT"
        ),
        (
            "misconceptions",
            "recurrence_count",
            "ALTER TABLE misconceptions ADD COLUMN recurrence_count INTEGER DEFAULT 0"
        ),

        # ── checkpoints (Item Families) ──────────────────────────────────────
        (
            "checkpoints",
            "item_family_role",
            "ALTER TABLE checkpoints ADD COLUMN item_family_role TEXT DEFAULT 'original'"
        ),
        (
            "checkpoints",
            "target_misconception",
            "ALTER TABLE checkpoints ADD COLUMN target_misconception TEXT"
        ),
    ]

    added = []
    skipped = []

    for table, col, sql in migrations:
        if column_exists(cur, table, col):
            skipped.append(f"{table}.{col}")
        else:
            cur.execute(sql)
            added.append(f"{table}.{col}")
            print(f"  [+] Added column: {table}.{col}")

    conn.commit()
    conn.close()

    print(f"\n[migrate] Done. Added {len(added)} column(s), skipped {len(skipped)} existing.")
    if skipped:
        print(f"  [=] Already present: {', '.join(skipped)}")

if __name__ == "__main__":
    print(f"[migrate] Targeting DB: {DB_PATH}")
    run_migration()
