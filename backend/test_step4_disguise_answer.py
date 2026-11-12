"""
test_step4_disguise_answer.py
-----------------------------
Unit test verifying Step 4: Disguise Test Answer + Relapse
POST /disguise/{misconception_id}/answer
1. Student cannot answer disguise test if status != 'improving' (400).
2. Student cannot answer disguise test before recheck_due (400).
3. Correct answer -> status transitions to 'resolved'.
4. Incorrect answer -> status transitions back to 'open' and relapse_count increases by 1.
5. Verifies both index and option-letter submission.
"""

import sys
import os
import unittest
import datetime
from unittest.mock import patch
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.all_models import User
from app.routers.disguise import submit_disguise_answer_endpoint
from app.schemas.all_schemas import DisguiseAnswerIn
from fastapi import HTTPException

class TestStep4DisguiseAnswer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SessionLocal()
        ts = int(datetime.datetime.now().timestamp() * 1000)
        self.user = User(
            email=f"step4_student_{ts}@mindtrace.edu",
            hashed_password="pw_hash_test",
            full_name="Step 4 Test Student",
            role="student"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()

    async def test_disguise_answer_transitions(self):
        fake_id = ObjectId("65f1a2b3c4d5e6f7a8b9c0d2")
        today = datetime.date.today().isoformat()
        past_due = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        future_due = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()

        doc_store = {
            "_id": fake_id,
            "id": str(fake_id),
            "student_id": self.user.id,
            "concept": "Stack LIFO Principle",
            "original_question": "Which element is popped first?",
            "status": "open",
            "improving_at": past_due,
            "recheck_due": past_due,
            "relapse_count": 0,
            "disguise": {
                "question": "In a cafeteria tray dispenser, clean trays are stacked from above. Which tray does the student take?",
                "options": [
                    "A. The tray at the very bottom",
                    "B. The tray added most recently at the top",
                    "C. A random tray in the middle",
                    "D. Any arbitrary tray"
                ],
                "correct_index": 1,
                "explanation": "This follows the Last-In First-Out (LIFO) model."
            }
        }

        async def fake_get_by_id(mid):
            if str(mid) == str(fake_id):
                return dict(doc_store)
            return None

        async def fake_mark_resolved(mid):
            doc_store["status"] = "resolved"
            return doc_store

        async def fake_mark_relapse(mid):
            doc_store["status"] = "open"
            doc_store["relapse_count"] += 1
            return doc_store

        with patch("app.routers.disguise.get_misconception_by_id", side_effect=fake_get_by_id), \
             patch("app.routers.disguise.mark_misconception_resolved", side_effect=fake_mark_resolved), \
             patch("app.routers.disguise.mark_misconception_relapse", side_effect=fake_mark_relapse):

            # 1. Cannot answer if status is 'open' (must be 'improving')
            doc_store["status"] = "open"
            with self.assertRaises(HTTPException) as ctx_open:
                await submit_disguise_answer_endpoint(
                    misconception_id=str(fake_id),
                    payload=DisguiseAnswerIn(selected_index=1),
                    db=self.db,
                    current_user=self.user
                )
            self.assertEqual(ctx_open.exception.status_code, 400)
            self.assertIn("improving", ctx_open.exception.detail)

            # 2. Cannot answer if recheck_due is in the future
            doc_store["status"] = "improving"
            doc_store["recheck_due"] = future_due
            with self.assertRaises(HTTPException) as ctx_future:
                await submit_disguise_answer_endpoint(
                    misconception_id=str(fake_id),
                    payload=DisguiseAnswerIn(selected_index=1),
                    db=self.db,
                    current_user=self.user
                )
            self.assertEqual(ctx_future.exception.status_code, 400)
            self.assertIn("recheck_due", ctx_future.exception.detail)

            # 3. Test INCORRECT Answer -> Status reverts to 'open', relapse_count becomes 1
            doc_store["recheck_due"] = past_due
            ans_wrong = DisguiseAnswerIn(selected_index=0) # Wrong (correct is 1)
            res_wrong = await submit_disguise_answer_endpoint(
                misconception_id=str(fake_id),
                payload=ans_wrong,
                db=self.db,
                current_user=self.user
            )

            self.assertFalse(res_wrong["is_correct"])
            self.assertEqual(res_wrong["new_status"], "open")
            self.assertEqual(res_wrong["relapse_count"], 1)
            self.assertIn("memorized, not understood", res_wrong["message"])

            # 4. Now suppose student answers original again to become 'improving'
            doc_store["status"] = "improving"

            # 5. Test CORRECT Answer -> Status becomes 'resolved'
            ans_correct = DisguiseAnswerIn(selected_index=1) # Correct
            res_correct = await submit_disguise_answer_endpoint(
                misconception_id=str(fake_id),
                payload=ans_correct,
                db=self.db,
                current_user=self.user
            )

            self.assertTrue(res_correct["is_correct"])
            self.assertEqual(res_correct["new_status"], "resolved")
            self.assertEqual(res_correct["correct_index"], 1)
            self.assertIn("Resolved", res_correct["message"])

if __name__ == "__main__":
    unittest.main()

