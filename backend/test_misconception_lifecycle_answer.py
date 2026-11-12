"""
test_misconception_lifecycle_answer.py
--------------------------------------
Verifies Step 2: Lifecycle Status Transitions in /answer endpoint.
1. Incorrect answer sets misconception status to 'open'.
2. Correct answer sets misconception status to 'improving',
   improving_at = today, and recheck_due = today + 2 days.
3. /answer NEVER marks status as 'resolved'.
4. No duplicate misconception records are created for the same user + concept.
5. A subsequent incorrect answer reverts status from 'improving' back to 'open'.
"""

import sys
import os
import unittest
import datetime
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, Misconception
from app.main import app
from app.utils.security import create_access_token

class TestMisconceptionLifecycleAnswer(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Create test student
        ts = int(datetime.datetime.now().timestamp() * 1000)
        self.user = User(
            email=f"lifecycle_test_{ts}@mindtrace.edu",
            hashed_password="hashed_pw",
            full_name="Lifecycle Test Student",
            role="student"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # Create lecture
        self.lecture = Lecture(
            user_id=self.user.id,
            title="Data Structures Lecture",
            course_code="CS201",
            status="ready"
        )
        self.db.add(self.lecture)
        self.db.commit()
        self.db.refresh(self.lecture)

        # Create concept
        self.concept = Concept(
            lecture_id=self.lecture.id,
            title="Stack LIFO Principle",
            description="Last-In First-Out structure",
            start_time=0.0,
            end_time=120.0,
            order_index=0
        )
        self.db.add(self.concept)
        self.db.commit()
        self.db.refresh(self.concept)

        # Create checkpoint MCQ
        self.checkpoint = Checkpoint(
            concept_id=self.concept.id,
            question_type="mcq",
            question_text="Which element is removed first in a Stack?",
            options=[
                "A. The first element inserted",
                "B. The most recently inserted element",
                "C. The middle element",
                "D. A random element"
            ],
            correct_answer="B. The most recently inserted element",
            explanation="Stacks operate on the Last-In First-Out (LIFO) principle.",
            target_misconception="Treating stack like a queue (FIFO)",
            order_index=0
        )
        self.db.add(self.checkpoint)
        self.db.commit()
        self.db.refresh(self.checkpoint)

        # Create token & API client
        self.token = create_access_token({"sub": self.user.email, "role": self.user.role})
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.close()

    def test_answer_lifecycle_transitions(self):
        # 1. Submit WRONG answer
        resp1 = self.client.post(
            "/answer",
            headers=self.headers,
            json={
                "checkpoint_id": self.checkpoint.id,
                "student_answer": "A. The first element inserted"
            }
        )
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertFalse(data1["is_correct"])

        # Check misconception in database
        misc1 = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).all()
        self.assertEqual(len(misc1), 1, "Must create exactly one misconception")
        self.assertEqual(misc1[0].status, "open", "Incorrect answer must set status to 'open'")
        self.assertIsNone(misc1[0].improving_at)
        self.assertIsNone(misc1[0].recheck_due)

        # 2. Submit another WRONG answer (test no duplicates)
        resp2 = self.client.post(
            "/answer",
            headers=self.headers,
            json={
                "checkpoint_id": self.checkpoint.id,
                "student_answer": "C. The middle element"
            }
        )
        self.assertEqual(resp2.status_code, 200)
        misc2 = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).all()
        self.assertEqual(len(misc2), 1, "Must NOT create duplicate misconception records")
        self.assertEqual(misc2[0].status, "open")
        self.assertEqual(misc2[0].occurrence_count, 2)

        # 3. Submit CORRECT answer
        today = datetime.date.today()
        expected_recheck = today + datetime.timedelta(days=2)

        resp3 = self.client.post(
            "/answer",
            headers=self.headers,
            json={
                "checkpoint_id": self.checkpoint.id,
                "student_answer": "B. The most recently inserted element"
            }
        )
        self.assertEqual(resp3.status_code, 200)
        data3 = resp3.json()
        self.assertTrue(data3["is_correct"])

        # Refresh from db
        self.db.expire_all()
        misc3 = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).first()

        self.assertIsNotNone(misc3)
        self.assertEqual(misc3.status, "improving", "Correct answer must transition status to 'improving'")
        self.assertNotEqual(misc3.status, "resolved", "/answer must NEVER mark status as 'resolved'")
        self.assertIsNone(misc3.resolved_at, "resolved_at must remain None")
        self.assertEqual(misc3.improving_at, today, "improving_at must be set to today's date")
        self.assertEqual(misc3.recheck_due, expected_recheck, "recheck_due must be set to today + 2 days")

        # 4. Submit WRONG answer again (should revert to 'open')
        resp4 = self.client.post(
            "/answer",
            headers=self.headers,
            json={
                "checkpoint_id": self.checkpoint.id,
                "student_answer": "D. A random element"
            }
        )
        self.assertEqual(resp4.status_code, 200)
        self.db.expire_all()
        misc4 = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).first()
        self.assertEqual(misc4.status, "open", "Failing again must transition status back to 'open'")

if __name__ == "__main__":
    unittest.main()

