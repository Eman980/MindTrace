"""
Unit test for Reopening Misconceptions and Status Transitions in MindTrace.
Verifies:
1. Reopen a Resolved misconception -> status becomes Unresolved, resolved_at is cleared.
2. Signal Trail logs "Reopened by student" with 0 points (severity score unchanged).
3. Dropdown transitions: Resolved -> Needs Review, and back to Resolved.
4. Dashboard and My Lectures unresolved counts include Unresolved and Needs Review.
5. Cross-topic re-check picks up reopened misconceptions (status Unresolved or Needs Review).
"""

import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, "backend")

from app.database import SessionLocal, Base, engine
from app.models.all_models import (
    User, Lecture, Concept, Checkpoint, Misconception, MisconceptionEvidence
)
from app.routers.misconceptions import update_misconception_status
from app.schemas.all_schemas import MisconceptionStatusUpdateIn
from app.routers.dashboard import get_dashboard_stats
from app.routers.lectures import list_lectures, get_lecture
from app.services.cross_topic_recheck_service import cross_topic_recheck_service


class TestReopenMisconception(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Create a unique test user
        self.user = User(
            email=f"test_reopen_{int(datetime.now().timestamp()*1000)}@mindtrace.edu",
            hashed_password="test_hash",
            full_name="Test Reopen Student",
            role="student"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # Create Lecture 1 (Prerequisite)
        self.lec1 = Lecture(
            user_id=self.user.id,
            title="Prerequisite Lecture on Functions",
            status="ready",
            course_code="CS101"
        )
        self.db.add(self.lec1)
        self.db.commit()
        self.db.refresh(self.lec1)

        # Create Concept & MCQ Checkpoint for Lecture 1
        self.concept = Concept(
            lecture_id=self.lec1.id,
            title="Pure Functions",
            description="Pure function invariants",
            start_time=0.0,
            end_time=60.0,
            order_index=0
        )
        self.db.add(self.concept)
        self.db.commit()
        self.db.refresh(self.concept)

        self.checkpoint = Checkpoint(
            concept_id=self.concept.id,
            question_type="mcq",
            question_text="What is a pure function?",
            options='["A. Deterministic mapping", "B. Random state", "C. Loop", "D. Global variable"]',
            correct_answer="A. Deterministic mapping",
            explanation="A pure function produces predictable outputs with no side effects.",
            order_index=0
        )
        self.db.add(self.checkpoint)
        self.db.commit()
        self.db.refresh(self.checkpoint)

        # Create a Resolved Misconception
        self.misc = Misconception(
            user_id=self.user.id,
            lecture_id=self.lec1.id,
            concept_id=self.concept.id,
            concept_name=self.concept.title,
            title="Confusing Pure Functions",
            summary="Thinks pure functions mutate external state",
            severity_score=6,
            severity_level="Medium",
            occurrence_count=2,
            status="Resolved",
            evidence_status="Resolved",
            resolved_at=datetime.now(timezone.utc)
        )
        self.db.add(self.misc)
        self.db.commit()
        self.db.refresh(self.misc)

        # Create Lecture 2 (Dependent) linked to Lecture 1 as prerequisite
        self.lec2 = Lecture(
            user_id=self.user.id,
            title="Advanced Recursion Lecture",
            status="ready",
            course_code="CS102",
            prerequisite_lecture_id=self.lec1.id
        )
        self.db.add(self.lec2)
        self.db.commit()
        self.db.refresh(self.lec2)

    def tearDown(self):
        # Clean up test artifacts
        try:
            self.db.query(MisconceptionEvidence).filter(
                MisconceptionEvidence.misconception_id == self.misc.id
            ).delete()
            self.db.query(Misconception).filter(Misconception.user_id == self.user.id).delete()
            self.db.query(Checkpoint).filter(Checkpoint.concept_id == self.concept.id).delete()
            self.db.query(Concept).filter(Concept.lecture_id == self.lec1.id).delete()
            self.db.query(Lecture).filter(Lecture.user_id == self.user.id).delete()
            self.db.query(User).filter(User.id == self.user.id).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_reopen_resolved_misconception_to_unresolved(self):
        """1. Reopening a Resolved misconception sets status to Unresolved, clears resolved_at, logs 0 points."""
        initial_score = self.misc.severity_score

        res = update_misconception_status(
            misconception_id=self.misc.id,
            payload=MisconceptionStatusUpdateIn(status="Unresolved"),
            db=self.db,
            current_user=self.user
        )

        self.db.refresh(self.misc)
        self.assertEqual(self.misc.status, "Unresolved")
        self.assertIsNone(self.misc.resolved_at, "resolved_at must be cleared to None")
        self.assertEqual(self.misc.severity_score, initial_score, "Severity score must not change on reopen")

        # Verify evidence entry
        ev = (
            self.db.query(MisconceptionEvidence)
            .filter(MisconceptionEvidence.misconception_id == self.misc.id)
            .order_by(MisconceptionEvidence.id.desc())
            .first()
        )
        self.assertIsNotNone(ev)
        self.assertEqual(ev.evidence_text, "Reopened by student")
        self.assertEqual(ev.points_added, 0, "Points added must be 0 for reopen")

    def test_status_dropdown_transitions(self):
        """2. Dropdown transitions: Resolved -> Needs Review, then back to Resolved."""
        # Transition 1: Resolved -> Needs Review
        res1 = update_misconception_status(
            misconception_id=self.misc.id,
            payload=MisconceptionStatusUpdateIn(status="Needs Review"),
            db=self.db,
            current_user=self.user
        )
        self.db.refresh(self.misc)
        self.assertEqual(self.misc.status, "Needs Review")
        self.assertIsNone(self.misc.resolved_at)

        # Transition 2: Needs Review -> Resolved
        res2 = update_misconception_status(
            misconception_id=self.misc.id,
            payload=MisconceptionStatusUpdateIn(status="Resolved"),
            db=self.db,
            current_user=self.user
        )
        self.db.refresh(self.misc)
        self.assertEqual(self.misc.status, "Resolved")
        self.assertIsNotNone(self.misc.resolved_at)

    def test_unresolved_counts_on_dashboard_and_lectures(self):
        """3. Unresolved counts on Dashboard and Lectures include both Unresolved and Needs Review."""
        # When Resolved: count should be 0
        dash_stats = get_dashboard_stats(db=self.db, current_user=self.user)
        self.assertEqual(dash_stats["unresolved_concepts"], 0)

        # Reopen to Unresolved: count should be 1
        update_misconception_status(
            misconception_id=self.misc.id,
            payload=MisconceptionStatusUpdateIn(status="Unresolved"),
            db=self.db,
            current_user=self.user
        )
        dash_stats = get_dashboard_stats(db=self.db, current_user=self.user)
        self.assertEqual(dash_stats["unresolved_concepts"], 1)

        lec_detail = get_lecture(lecture_id=self.lec1.id, db=self.db, current_user=self.user)
        self.assertEqual(lec_detail["unresolved_count"], 1)

        # Change to Needs Review: count should STILL be 1
        update_misconception_status(
            misconception_id=self.misc.id,
            payload=MisconceptionStatusUpdateIn(status="Needs Review"),
            db=self.db,
            current_user=self.user
        )
        dash_stats2 = get_dashboard_stats(db=self.db, current_user=self.user)
        self.assertEqual(dash_stats2["unresolved_concepts"], 1)

        lec_detail2 = get_lecture(lecture_id=self.lec1.id, db=self.db, current_user=self.user)
        self.assertEqual(lec_detail2["unresolved_count"], 1)

    def test_cross_topic_recheck_picks_up_reopened(self):
        """4. Open dependent lecture picks up the reopened misconception from prerequisite."""
        # While Resolved: 0 rechecks
        rechecks_before = cross_topic_recheck_service.get_prerequisite_rechecks(
            db=self.db,
            user_id=self.user.id,
            lecture_id=self.lec2.id
        )
        self.assertEqual(len(rechecks_before), 0)

        # Reopen to Unresolved: 1 recheck found
        update_misconception_status(
            misconception_id=self.misc.id,
            payload=MisconceptionStatusUpdateIn(status="Unresolved"),
            db=self.db,
            current_user=self.user
        )
        rechecks_after = cross_topic_recheck_service.get_prerequisite_rechecks(
            db=self.db,
            user_id=self.user.id,
            lecture_id=self.lec2.id
        )
        self.assertEqual(len(rechecks_after), 1)
        self.assertEqual(rechecks_after[0]["misconception_id"], self.misc.id)
        self.assertEqual(rechecks_after[0]["question"]["question_type"], "mcq")


if __name__ == "__main__":
    unittest.main()
