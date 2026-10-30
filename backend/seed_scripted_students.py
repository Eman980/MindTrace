"""
seed_scripted_students.py
-------------------------
Populates MindTrace with 4 scripted student personas illustrating the
evidence-based resolution state machine for FYP-1 / FYP-2 experimental
validation (E1, E3, E4, E5) and Viva demonstrations.

Personas:
1. Aisha Patel (Genuine Learner)   -> Resolved (Passed with validated explanation)
2. Bilal Khan (Rote Memorizer)     -> Memorized (Surface pass, failed transfer probe)
3. Catherine Lee (Persistent Flaw)  -> Confirmed (Repeated distractor + behavioural replays)
4. Danial Ahmed (Recurrent Slip)   -> Recurred (Previously resolved, slipped on spaced re-probe)

Run from backend/:
    python seed_scripted_students.py
"""

import sys
import os
import datetime

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.all_models import (
    User, Lecture, Concept, Checkpoint, CheckpointAttempt,
    Misconception, MisconceptionEvidence, ConceptProgress
)
from app.services.seed_service import seed_demo_data
from app.utils.security import get_password_hash

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def seed_all_scripted_students():
    db = SessionLocal()
    try:
        print("\n=======================================================")
        print("  MindTrace: Seeding Scripted Evaluation Students")
        print("=======================================================\n")

        # -------------------------------------------------------------
        # Persona 1: Aisha Patel (Genuine Learner -> Resolved)
        # -------------------------------------------------------------
        user_1 = db.query(User).filter(User.email == "learner@mindtrace.edu").first()
        if not user_1:
            user_1 = User(
                email="learner@mindtrace.edu",
                full_name="Aisha Patel (Genuine Learner)",
                hashed_password=get_password_hash("mindtrace123"),
                role="student"
            )
            db.add(user_1)
            db.commit()
            db.refresh(user_1)

        lec_1 = seed_demo_data(db, user_1)
        domain_c1 = next((c for c in lec_1.concepts if "Domain and Range" in c.title), lec_1.concepts[2])
        chk_1 = domain_c1.checkpoints[0]

        # Ensure misconception is marked Resolved
        misc_1 = db.query(Misconception).filter(
            Misconception.user_id == user_1.id,
            Misconception.concept_id == domain_c1.id
        ).first()

        if misc_1:
            misc_1.evidence_status = "Resolved"
            misc_1.status = "Resolved"
            misc_1.severity_score = 1
            misc_1.severity_level = "Low"
            misc_1.resolved_at = utcnow() - datetime.timedelta(hours=2)

            # Add successful explanation attempt
            db.add(CheckpointAttempt(
                checkpoint_id=chk_1.id,
                user_id=user_1.id,
                student_answer="A. Domain is the set of valid inputs; Range is the set of resulting outputs",
                is_correct=True,
                confidence_level=3,
                explanation_text="Domain defines the allowed input values while range is the actual computed output space.",
                explanation_verdict="valid",
                hours_since_prev=74.5,
                created_at=utcnow() - datetime.timedelta(hours=2)
            ))

            db.add(MisconceptionEvidence(
                misconception_id=misc_1.id,
                signal_type="explanation_check_pass",
                evidence_text="Student passed transfer checkpoint with validated explanation and high confidence (3/3).",
                points_added=0,
                created_at=utcnow() - datetime.timedelta(hours=2)
            ))
            print("  [OK] Persona 1: Aisha Patel -> Resolved state seeded.")

        # -------------------------------------------------------------
        # Persona 2: Bilal Khan (Rote Memorizer -> Memorized)
        # -------------------------------------------------------------
        user_2 = db.query(User).filter(User.email == "memorizer@mindtrace.edu").first()
        if not user_2:
            user_2 = User(
                email="memorizer@mindtrace.edu",
                full_name="Bilal Khan (Rote Memorizer)",
                hashed_password=get_password_hash("mindtrace123"),
                role="student"
            )
            db.add(user_2)
            db.commit()
            db.refresh(user_2)

        lec_2 = seed_demo_data(db, user_2)
        notation_c2 = next((c for c in lec_2.concepts if "Function Notation" in c.title), lec_2.concepts[3])
        chk_2 = notation_c2.checkpoints[0]

        misc_2 = db.query(Misconception).filter(
            Misconception.user_id == user_2.id,
            Misconception.concept_id == notation_c2.id
        ).first()

        if misc_2:
            misc_2.evidence_status = "Memorized"
            misc_2.memorized_flag = True
            misc_2.severity_score = 4
            misc_2.severity_level = "Medium"

            # Attempt with low confidence and guess explanation
            db.add(CheckpointAttempt(
                checkpoint_id=chk_2.id,
                user_id=user_2.id,
                student_answer="B. The input argument passed into the function",
                is_correct=True,
                confidence_level=1,
                explanation_text="I just guessed the letter inside the bracket because I memorized the option.",
                explanation_verdict="too_brief",
                created_at=utcnow() - datetime.timedelta(hours=10)
            ))

            db.add(MisconceptionEvidence(
                misconception_id=misc_2.id,
                signal_type="conversational_pattern",
                evidence_text="Passed surface item but failed isomorphic variant. Flagged: Memorized / Transfer Gap.",
                points_added=2,
                created_at=utcnow() - datetime.timedelta(hours=5)
            ))
            print("  [OK] Persona 2: Bilal Khan -> Memorized (Rote) state seeded.")

        # -------------------------------------------------------------
        # Persona 3: Catherine Lee (Persistent Flawed Student -> Confirmed)
        # -------------------------------------------------------------
        user_3 = db.query(User).filter(User.email == "persistent@mindtrace.edu").first()
        if not user_3:
            user_3 = User(
                email="persistent@mindtrace.edu",
                full_name="Catherine Lee (Persistent Misconception)",
                hashed_password=get_password_hash("mindtrace123"),
                role="student"
            )
            db.add(user_3)
            db.commit()
            db.refresh(user_3)

        lec_3 = seed_demo_data(db, user_3)
        quad_c3 = next((c for c in lec_3.concepts if "Concrete Examples" in c.title), lec_3.concepts[4])
        chk_3 = quad_c3.checkpoints[0]

        misc_3 = db.query(Misconception).filter(
            Misconception.user_id == user_3.id,
            Misconception.concept_id == quad_c3.id
        ).first()

        if not misc_3:
            misc_3 = Misconception(
                user_id=user_3.id,
                lecture_id=lec_3.id,
                concept_id=quad_c3.id,
                concept_name=quad_c3.title,
                title="Quadratic Range Non-Negativity Confusion",
                summary="Student firmly believes squaring a negative real number produces negative output.",
                severity_score=8,
                severity_level="High",
                occurrence_count=4,
                status="Unresolved",
                evidence_status="Confirmed",
                remediation_segment_id=quad_c3.id,
                first_detected=utcnow() - datetime.timedelta(days=3),
                last_detected=utcnow() - datetime.timedelta(hours=1)
            )
            db.add(misc_3)
            db.flush()

        db.add(CheckpointAttempt(
            checkpoint_id=chk_3.id,
            user_id=user_3.id,
            student_answer="A. All real numbers including negative numbers",
            is_correct=False,
            confidence_level=3,
            explanation_text="If you square negative numbers like -3, the negative sign carries over to give negative 9.",
            explanation_verdict="flawed_matches_label",
            created_at=utcnow() - datetime.timedelta(hours=1)
        ))

        db.add(MisconceptionEvidence(
            misconception_id=misc_3.id,
            signal_type="explicit_checkpoint",
            evidence_text="High confidence flawed answer: Student asserted (-x)^2 yields negative numbers.",
            points_added=3,
            created_at=utcnow() - datetime.timedelta(hours=1)
        ))
        print("  [OK] Persona 3: Catherine Lee -> Confirmed High Severity state seeded.")

        # -------------------------------------------------------------
        # Persona 4: Danial Ahmed (Recurrent Slip -> Recurred)
        # -------------------------------------------------------------
        user_4 = db.query(User).filter(User.email == "recurrent@mindtrace.edu").first()
        if not user_4:
            user_4 = User(
                email="recurrent@mindtrace.edu",
                full_name="Danial Ahmed (Recurrent Slip)",
                hashed_password=get_password_hash("mindtrace123"),
                role="student"
            )
            db.add(user_4)
            db.commit()
            db.refresh(user_4)

        lec_4 = seed_demo_data(db, user_4)
        domain_c4 = next((c for c in lec_4.concepts if "Domain and Range" in c.title), lec_4.concepts[2])
        chk_4 = domain_c4.checkpoints[0]

        misc_4 = db.query(Misconception).filter(
            Misconception.user_id == user_4.id,
            Misconception.concept_id == domain_c4.id
        ).first()

        if misc_4:
            misc_4.evidence_status = "Recurred"
            misc_4.status = "Unresolved"
            misc_4.recurrence_count = 1
            misc_4.severity_score = 6
            misc_4.severity_level = "High"
            misc_4.resolved_at = utcnow() - datetime.timedelta(days=4)

            db.add(CheckpointAttempt(
                checkpoint_id=chk_4.id,
                user_id=user_4.id,
                student_answer="B. Domain is the function's return value; Range is the parameter count",
                is_correct=False,
                confidence_level=2,
                explanation_text="I mixed up the return value and input space again during testing.",
                explanation_verdict="flawed_matches_label",
                created_at=utcnow() - datetime.timedelta(hours=4)
            ))

            db.add(MisconceptionEvidence(
                misconception_id=misc_4.id,
                signal_type="checkpoint_resolved",
                evidence_text="Initially marked Resolved following remediation lecture replay.",
                points_added=0,
                created_at=utcnow() - datetime.timedelta(days=4)
            ))

            db.add(MisconceptionEvidence(
                misconception_id=misc_4.id,
                signal_type="explicit_checkpoint",
                evidence_text="Relapse detected: Slipped back into Domain/Range inversion during follow-up transfer test.",
                points_added=3,
                created_at=utcnow() - datetime.timedelta(hours=4)
            ))
            print("  [OK] Persona 4: Danial Ahmed -> Recurred state seeded.")

        # -------------------------------------------------------------
        # Enrich Default Demo Student (demo@mindtrace.edu)
        # -------------------------------------------------------------
        demo_user = db.query(User).filter(User.email == "demo@mindtrace.edu").first()
        if demo_user:
            demo_lec = seed_demo_data(db, demo_user)
            # Ensure domain misconception has full attempts and is due for reprobe
            domain_demo = next((c for c in demo_lec.concepts if "Domain and Range" in c.title), demo_lec.concepts[2])
            demo_misc = db.query(Misconception).filter(
                Misconception.user_id == demo_user.id,
                Misconception.concept_id == domain_demo.id
            ).first()

            if demo_misc:
                demo_misc.evidence_status = "Confirmed"
                demo_misc.last_detected = utcnow() - datetime.timedelta(hours=75) # > 72h, so it's due!
                chk_demo = domain_demo.checkpoints[0]

                # Add attempt history
                existing_att = db.query(CheckpointAttempt).filter(
                    CheckpointAttempt.user_id == demo_user.id,
                    CheckpointAttempt.checkpoint_id == chk_demo.id
                ).first()

                if not existing_att:
                    db.add(CheckpointAttempt(
                        checkpoint_id=chk_demo.id,
                        user_id=demo_user.id,
                        student_answer="C. Range is the input set; Domain is the error boundary",
                        is_correct=False,
                        confidence_level=3,
                        explanation_text="I thought range is what you pass into the function from the outside.",
                        explanation_verdict="flawed_matches_label",
                        created_at=utcnow() - datetime.timedelta(hours=75)
                    ))
                print("  [OK] Demo Student: Alex Chen enriched with due re-probe and attempt logs.")

        db.commit()

        print("\n=======================================================")
        print("  All 4 Student Personas Seeded Successfully!")
        print("=======================================================")
        print("  1. Aisha Patel    (learner@mindtrace.edu / mindtrace123)   -> Resolved")
        print("  2. Bilal Khan     (memorizer@mindtrace.edu / mindtrace123) -> Memorized")
        print("  3. Catherine Lee  (persistent@mindtrace.edu / mindtrace123)-> Confirmed")
        print("  4. Danial Ahmed   (recurrent@mindtrace.edu / mindtrace123) -> Recurred")
        print("  * Default Demo    (demo@mindtrace.edu / mindtrace123)      -> Active with Due Reprobes")
        print("=======================================================\n")

    except Exception as e:
        db.rollback()
        print(f"\n[Error seeding students]: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_all_scripted_students()
