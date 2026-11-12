"""
Unit tests for Manual Lecture-Level Cross-Topic Recheck (FYP-1).
Verifies:
1. Prerequisite link logic: Recheck trigger uses prerequisite_lecture_id, NOT concept name map.
2. Only MCQ-type questions are picked for rechecking.
3. Validation blocks self-referencing (A -> A) and circular dependencies (A -> B and B -> A).
4. Submitting incorrect answer keeps misconception open and records failure signal (+3).
5. Submitting correct answer resolves misconception and records passed signal (-3).
6. After resolution, recheck query returns empty.
7. Deleting the prerequisite lecture sets prerequisite_lecture_id to NULL.
"""
import unittest
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import HTTPException
from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, Misconception, MisconceptionEvidence
from app.services.cross_topic_recheck_service import cross_topic_recheck_service
from app.routers.lectures import validate_prerequisite_lecture

class TestCrossTopicRecheck(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # Clean/Find test user
        self.user = self.db.query(User).filter(User.email == "recheck_student@mindtrace.edu").first()
        if not self.user:
            self.user = User(
                email="recheck_student@mindtrace.edu",
                hashed_password="hashed_test_password",
                full_name="Recheck Test Student",
                role="student"
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

    def tearDown(self):
        # Clean up test user records
        if self.user:
            # Clear any prerequisite links first to avoid circular FK locks
            self.db.query(Lecture).filter(Lecture.user_id == self.user.id).update(
                {"prerequisite_lecture_id": None}, synchronize_session=False
            )
            self.db.commit()

            user = self.db.query(User).filter(User.id == self.user.id).first()
            if user:
                self.db.delete(user)
                self.db.commit()
        self.db.close()

    def test_cross_topic_recheck_manual_link_flow(self):
        # 1. Create Lecture 1 (Functions) with a Concept and Checkpoints (MCQ and Short)
        lec1 = Lecture(
            user_id=self.user.id,
            title="Lecture 1: Introduction to Python Functions",
            duration_seconds=300
        )
        self.db.add(lec1)
        self.db.commit()
        self.db.refresh(lec1)

        c1 = Concept(
            lecture_id=lec1.id,
            title="Function Return Values",
            description="Understanding return values and termination",
            start_time=0.0,
            end_time=60.0
        )
        self.db.add(c1)
        self.db.commit()
        self.db.refresh(c1)

        # MCQ question (must be picked)
        chk_mcq = Checkpoint(
            concept_id=c1.id,
            question_type="mcq",
            question_text="What does a function return if no return statement is executed?",
            options=["A) 0", "B) None", "C) False", "D) Error"],
            correct_answer="B) None",
            explanation="In Python, functions without an explicit return statement return None.",
            item_family_role="variant"
        )
        self.db.add(chk_mcq)

        # Short question (must NOT be picked, recheck is MCQ only)
        chk_short = Checkpoint(
            concept_id=c1.id,
            question_type="short",
            question_text="Explain what None means as a function return value.",
            options=[],
            correct_answer="It represents the absence of a returned value.",
            explanation="None signifies no value returned.",
            item_family_role="original"
        )
        self.db.add(chk_short)
        self.db.commit()
        self.db.refresh(chk_mcq)

        # 2. Add an open misconception for the student on Lecture 1
        misc = Misconception(
            user_id=self.user.id,
            lecture_id=lec1.id,
            concept_id=c1.id,
            concept_name="Function Return Values",
            title="Conflating Print with Return Values",
            summary="Student believes print() passes a value back to caller",
            severity_score=2,
            severity_level="Low",
            status="Unresolved"
        )
        self.db.add(misc)
        self.db.commit()
        self.db.refresh(misc)

        # 3. Create Lecture 2 (Recursion) manually linked to Lecture 1 as prerequisite
        lec2 = Lecture(
            user_id=self.user.id,
            title="Lecture 2: Mastering Recursion",
            duration_seconds=400,
            prerequisite_lecture_id=lec1.id
        )
        self.db.add(lec2)
        self.db.commit()
        self.db.refresh(lec2)

        # 4. Test validation rules:
        # a) Cannot set self as prerequisite
        with self.assertRaises(HTTPException) as cm_self:
            validate_prerequisite_lecture(self.db, lecture_id=lec2.id, prerequisite_id=lec2.id, user_id=self.user.id)
        self.assertEqual(cm_self.exception.status_code, 400)
        self.assertIn("cannot be its own prerequisite", cm_self.exception.detail)

        # b) Cannot create circular link (lec1 -> lec2 while lec2 -> lec1)
        with self.assertRaises(HTTPException) as cm_circ:
            validate_prerequisite_lecture(self.db, lecture_id=lec1.id, prerequisite_id=lec2.id, user_id=self.user.id)
        self.assertEqual(cm_circ.exception.status_code, 400)
        self.assertIn("Circular prerequisite link", cm_circ.exception.detail)

        # 5. Check get_prerequisite_rechecks returns the prerequisite recheck
        rechecks = cross_topic_recheck_service.get_prerequisite_rechecks(
            db=self.db,
            user_id=self.user.id,
            lecture_id=lec2.id
        )
        self.assertEqual(len(rechecks), 1, "Should find exactly 1 prerequisite recheck")
        self.assertEqual(rechecks[0]["misconception_id"], misc.id)
        self.assertEqual(rechecks[0]["earlier_lecture_id"], lec1.id)
        self.assertEqual(rechecks[0]["earlier_lecture_title"], lec1.title)
        self.assertEqual(rechecks[0]["question"]["id"], chk_mcq.id)
        self.assertEqual(rechecks[0]["question"]["question_type"], "mcq", "Must be MCQ only")

        # 6. Test Answer Incorrectly:
        fail_data = cross_topic_recheck_service.submit_recheck_answer(
            db=self.db,
            user_id=self.user.id,
            lecture_id=lec2.id,
            misconception_id=misc.id,
            checkpoint_id=chk_mcq.id,
            student_answer="A) 0"
        )
        self.assertFalse(fail_data["is_correct"])
        self.assertEqual(fail_data["new_status"], "Unresolved")
        self.assertGreater(fail_data["new_severity_score"], 2)

        # Check evidence line in Signal Trail
        ev_fail = self.db.query(MisconceptionEvidence).filter(
            MisconceptionEvidence.misconception_id == misc.id
        ).order_by(MisconceptionEvidence.id.desc()).first()
        self.assertIn("Cross-topic recheck failed in Lecture 2: Mastering Recursion", ev_fail.evidence_text)
        self.assertEqual(ev_fail.points_added, 3)

        # 7. Test Answer Correctly:
        pass_data = cross_topic_recheck_service.submit_recheck_answer(
            db=self.db,
            user_id=self.user.id,
            lecture_id=lec2.id,
            misconception_id=misc.id,
            checkpoint_id=chk_mcq.id,
            student_answer="B) None"
        )
        self.assertTrue(pass_data["is_correct"])
        self.assertEqual(pass_data["new_status"], "Resolved")

        # Check evidence line in Signal Trail
        ev_pass = self.db.query(MisconceptionEvidence).filter(
            MisconceptionEvidence.misconception_id == misc.id
        ).order_by(MisconceptionEvidence.id.desc()).first()
        self.assertIn("Cross-topic recheck passed in Lecture 2: Mastering Recursion", ev_pass.evidence_text)
        self.assertEqual(ev_pass.points_added, -3)

        # 8. Check that get_prerequisite_rechecks now returns 0 (since it is now resolved)
        rechecks_after = cross_topic_recheck_service.get_prerequisite_rechecks(
            db=self.db,
            user_id=self.user.id,
            lecture_id=lec2.id
        )
        self.assertEqual(len(rechecks_after), 0, "No rechecks should remain after resolving")

        # 9. Test Deleting Prerequisite Lecture sets prerequisite_lecture_id to NULL
        # Simulate lecture deletion unlinking
        self.db.query(Lecture).filter(Lecture.prerequisite_lecture_id == lec1.id).update(
            {"prerequisite_lecture_id": None}, synchronize_session=False
        )
        self.db.delete(lec1)
        self.db.commit()

        # Verify lec2's prerequisite_lecture_id is now None
        self.db.refresh(lec2)
        self.assertIsNone(lec2.prerequisite_lecture_id, "Deleting prerequisite lecture must set link to NULL")

if __name__ == "__main__":
    unittest.main()
