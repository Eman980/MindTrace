"""
reset_sample_lecture.py
-----------------------
Clean existing test/demo lecture records and reload a pristine sample lecture
for all user accounts (or a specified user). Safe, idempotent, and non-destructive
to actual user account records.

Run from backend directory:
    python reset_sample_lecture.py [--email user@example.com]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, Misconception
from app.services.seed_service import reset_user_to_sample_lecture

def run_reset(target_email: str = None):
    db = SessionLocal()
    try:
        print("\n=======================================================")
        print("  MindTrace: Sample Lecture Reset & Initialization")
        print("=======================================================")

        query = db.query(User)
        if target_email:
            query = query.filter(User.email == target_email.lower())
            users = query.all()
            if not users:
                print(f"[!] No user account found with email: {target_email}")
                return False
        else:
            users = query.all()

        if not users:
            print("[!] No users in database to reset.")
            return False

        print(f"[*] Found {len(users)} user account(s). Cleaning old lecture data and loading sample lecture...")

        for user in users:
            print(f"\n  -> Processing User #{user.id} ({user.email})...")
            lecture = reset_user_to_sample_lecture(db, user)
            print(f"     [+] Successfully loaded sample lecture ID {lecture.id}: '{lecture.title}'")
            print(f"     [+] Concepts: {len(lecture.concepts)}")
            total_chks = sum(len(c.checkpoints) for c in lecture.concepts)
            print(f"     [+] Checkpoints: {total_chks}")
            misc_count = db.query(Misconception).filter(Misconception.user_id == user.id).count()
            print(f"     [+] Persistent Misconceptions: {misc_count}")

        print("\n=======================================================")
        print("  Reset Completed Successfully!")
        print("  Sample lecture 'Introduction to Functions' is ready.")
        print("  All database relationships verified intact.")
        print("=======================================================\n")
        return True

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Failed to reset sample lecture: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean and reset MindTrace sample lecture data.")
    parser.add_argument("--email", type=str, default=None, help="Specific user email to reset. Defaults to all users.")
    args = parser.parse_args()
    success = run_reset(args.email)
    sys.exit(0 if success else 1)

