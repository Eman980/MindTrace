
"""
test_step2_answer_lifecycle.py
------------------------------
Unit test verifying Step 2: Status logic in /answer and /flag endpoints,
plus MongoDB lifecycle helper state machine.
1. Incorrect answer -> status is 'open'.
2. Flagging concept -> status is 'open'.
3. Correct answer -> status is 'improving', improving_at = today, recheck_due = today + 2 days.
4. /answer NEVER marks status as 'resolved'.
5. Subsequent incorrect answer -> reverts status back to 'open'.
6. Direct MongoDB document helper functions transition correctly.
"""

import sys
import os
import unittest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, Misconception
from app.schemas.all_schemas import CheckpointAnswerIn
from app.routers.checkpoints import submit_checkpoint_answer
from app.routers.lectures import flag_concept_endpoint
from app.mongo import (
    mark_misconception_open,
    mark_misconception_improving,
    mark_misconception_relapse,
    mark_misconception_resolved,
    format_misconception_doc
)

class TestStep2AnswerLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SessionLocal()
        ts = int(datetime.datetime.now().timestamp() * 1000)
        self.user = User(
            email=f"step2_student_{ts}@mindtrace.edu",
            hashed_password="pw_hash_test",
            full_name="Step 2 Test Student",
            role="student"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.lecture = Lecture(
            user_id=self.user.id,
            title="Algorithms & Data Structures",
            course_code="CS201",
            status="ready"
        )
        self.db.add(self.lecture)
        self.db.commit()
        self.db.refresh(self.lecture)

        self.concept = Concept(
            lecture_id=self.lecture.id,
            title="Stack LIFO Principle",
            description="Last In First Out principle",
            start_time=0.0,
            end_time=90.0,
            order_index=0
        )
        self.db.add(self.concept)
        self.db.commit()
        self.db.refresh(self.concept)

        self.checkpoint = Checkpoint(
            concept_id=self.concept.id,
            question_type="mcq",
            question_text="Which element is removed first in a Stack?",
            options=[
                "A. First element added",
                "B. Most recently added element",
                "C. Middle element",
                "D. Random element"
            ],
            correct_answer="B. Most recently added element",
            explanation="Stack operates on Last-In First-Out (LIFO).",
            order_index=0
        )
        self.db.add(self.checkpoint)
        self.db.commit()
        self.db.refresh(self.checkpoint)

    def tearDown(self):
        self.db.close()

    async def test_endpoint_lifecycle_transitions(self):
        # 1. Incorrect answer -> Status becomes 'open'
        ans_wrong = CheckpointAnswerIn(
            checkpoint_id=self.checkpoint.id,
            student_answer="A. First element added"
        )
        res_wrong = await submit_checkpoint_answer(
            answer_in=ans_wrong,
            db=self.db,
            current_user=self.user
        )
        self.assertFalse(res_wrong["is_correct"])
        self.assertEqual(res_wrong.get("misconception_status"), "open")

        # Verify in SQLite DB
        misc = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).first()
        self.assertIsNotNone(misc)
        self.assertEqual(misc.status, "open")

        # 2. Correct answer -> Status becomes 'improving', recheck_due = today + 2 days
        today = datetime.date.today()
        expected_due = str(today + datetime.timedelta(days=2))

        ans_correct = CheckpointAnswerIn(
            checkpoint_id=self.checkpoint.id,
            student_answer="B. Most recently added element"
        )
        res_correct = await submit_checkpoint_answer(
            answer_in=ans_correct,
            db=self.db,
            current_user=self.user
        )
        self.assertTrue(res_correct["is_correct"])
        self.assertEqual(res_correct.get("misconception_status"), "improving")
        self.assertEqual(res_correct.get("recheck_due"), expected_due)

        self.db.expire_all()
        misc_improving = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).first()
        self.assertEqual(misc_improving.status, "improving")
        self.assertEqual(str(misc_improving.recheck_due), expected_due)
        self.assertIsNone(misc_improving.resolved_at, "/answer must never mark status as 'resolved'")

        # 3. Subsequent wrong answer -> Reverts status to 'open'
        ans_wrong2 = CheckpointAnswerIn(
            checkpoint_id=self.checkpoint.id,
            student_answer="C. Middle element"
        )
        res_wrong2 = await submit_checkpoint_answer(
            answer_in=ans_wrong2,
            db=self.db,
            current_user=self.user
        )
        self.assertFalse(res_wrong2["is_correct"])
        self.assertEqual(res_wrong2.get("misconception_status"), "open")

        self.db.expire_all()
        misc_reverted = self.db.query(Misconception).filter(
            Misconception.user_id == self.user.id,
            Misconception.concept_id == self.concept.id
        ).first()
        self.assertEqual(misc_reverted.status, "open")

        # 4. Flag concept -> Status remains/becomes 'open'
        res_flag = await flag_concept_endpoint(
            concept_id=self.concept.id,
            db=self.db,
            current_user=self.user
        )
        self.assertEqual(res_flag.get("status"), "open")

    async def test_mongo_document_state_machine(self):
        # In-memory document simulation for MongoDB helper functions
        fake_id = ObjectId("65f1a2b3c4d5e6f7a8b9c0d1")
        doc_store = {
            "_id": fake_id,
            "student_id": self.user.id,
            "lecture_id": self.lecture.id,
            "concept": self.concept.title,
            "original_question": self.checkpoint.question_text,
            "status": "open",
            "improving_at": None,
            "recheck_due": None,
            "relapse_count": 0,
            "disguise": None
        }

        mock_col = MagicMock()

        async def fake_update_one(filter_dict, update_dict):
            if "$set" in update_dict:
                for k, v in update_dict["$set"].items():
                    doc_store[k] = v
            if "$inc" in update_dict:
                for k, v in update_dict["$inc"].items():
                    doc_store[k] = doc_store.get(k, 0) + v
            return MagicMock(modified_count=1)

        async def fake_find_one(filter_dict):
            return dict(doc_store)

        mock_col.update_one = AsyncMock(side_effect=fake_update_one)
        mock_col.find_one = AsyncMock(side_effect=fake_find_one)
        mock_db = MagicMock(misconceptions=mock_col)

        with patch("app.mongo.get_mongo_db", return_value=mock_db):
            # Test mark_misconception_improving
            imp = await mark_misconception_improving(str(fake_id))
            self.assertEqual(imp["status"], "improving")
            self.assertIsNotNone(imp["improving_at"])
            self.assertIsNotNone(imp["recheck_due"])

            # Test mark_misconception_open
            op = await mark_misconception_open(str(fake_id))
            self.assertEqual(op["status"], "open")

            # Test mark_misconception_relapse
            rel = await mark_misconception_relapse(str(fake_id))
            self.assertEqual(rel["status"], "open")
            self.assertEqual(rel["relapse_count"], 1)

            # Test mark_misconception_resolved
            res = await mark_misconception_resolved(str(fake_id))
            self.assertEqual(res["status"], "resolved")

if __name__ == "__main__":
    unittest.main()
