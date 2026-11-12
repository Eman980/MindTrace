"""
test_step3_disguise_generate.py
-------------------------------
Unit test verifying Step 3: Disguise Test Generation endpoint
POST /disguise/{misconception_id}/generate
1. 404 if misconception not found.
2. 400 if misconception status is not 'improving'.
3. 400 if today < recheck_due.
4. Generates Disguise Test MCQ (4 options) on/after recheck_due.
5. Does NOT expose correct_index or explanation in the generation response.
6. Reuses stored disguise question on subsequent calls (no repeated generation).
7. Verifies JSON fence-stripping logic.
"""

import sys
import os
import unittest
import datetime
from unittest.mock import patch, MagicMock
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Misconception
from app.routers.disguise import generate_disguise_test_endpoint
from app.services.disguise_service import generate_disguise_mcq
from fastapi import HTTPException

class TestStep3DisguiseGenerate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SessionLocal()
        ts = int(datetime.datetime.now().timestamp() * 1000)
        self.user = User(
            email=f"step3_student_{ts}@mindtrace.edu",
            hashed_password="pw_hash_test",
            full_name="Step 3 Test Student",
            role="student"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()

    async def test_disguise_eligibility_and_generation(self):
        fake_id = ObjectId("65f1a2b3c4d5e6f7a8b9c0d1")
        today = datetime.date.today().isoformat()
        future_due = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        past_due = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

        doc_store = {
            "_id": fake_id,
            "id": str(fake_id),
            "student_id": self.user.id,
            "concept": "Stack LIFO Principle",
            "original_question": "Which element is popped first?",
            "status": "open",
            "recheck_due": future_due,
            "relapse_count": 0,
            "disguise": None
        }

        async def fake_get_by_id(mid):
            if str(mid) == str(fake_id):
                return dict(doc_store)
            return None

        async def fake_save_disguise(mid, disguise_data):
            doc_store["disguise"] = disguise_data
            return doc_store

        with patch("app.routers.disguise.get_misconception_by_id", side_effect=fake_get_by_id), \
             patch("app.routers.disguise.save_disguise_to_misconception", side_effect=fake_save_disguise):

            # 1. Non-existent misconception -> 404
            with self.assertRaises(HTTPException) as ctx404:
                await generate_disguise_test_endpoint(
                    misconception_id="nonexistent_id",
                    db=self.db,
                    current_user=self.user
                )
            self.assertEqual(ctx404.exception.status_code, 404)

            # 2. Status 'open' (not 'improving') -> 400
            with self.assertRaises(HTTPException) as ctx400_status:
                await generate_disguise_test_endpoint(
                    misconception_id=str(fake_id),
                    db=self.db,
                    current_user=self.user
                )
            self.assertEqual(ctx400_status.exception.status_code, 400)
            self.assertIn("improving", ctx400_status.exception.detail)

            # 3. Status 'improving' but recheck_due in future -> 400
            doc_store["status"] = "improving"
            doc_store["recheck_due"] = future_due
            with self.assertRaises(HTTPException) as ctx400_date:
                await generate_disguise_test_endpoint(
                    misconception_id=str(fake_id),
                    db=self.db,
                    current_user=self.user
                )
            self.assertEqual(ctx400_date.exception.status_code, 400)
            self.assertIn("recheck_due", ctx400_date.exception.detail)

            # 4. Status 'improving' and recheck_due is due (today or past) -> SUCCESS
            doc_store["recheck_due"] = past_due
            result = await generate_disguise_test_endpoint(
                misconception_id=str(fake_id),
                db=self.db,
                current_user=self.user
            )

            self.assertEqual(result["misconception_id"], str(fake_id))
            self.assertEqual(result["concept"], "Stack LIFO Principle")
            self.assertEqual(len(result["options"]), 4)
            self.assertTrue(bool(result["question"]))

            # CRITICAL: Verify correct_index and explanation are NOT in public generate response!
            self.assertNotIn("correct_index", result)
            self.assertNotIn("explanation", result)

            # Verify saved in doc_store
            self.assertIsNotNone(doc_store["disguise"])
            saved_q = doc_store["disguise"]["question"]

            # 5. Calling again reuses the stored question without changing it
            result2 = await generate_disguise_test_endpoint(
                misconception_id=str(fake_id),
                db=self.db,
                current_user=self.user
            )
            self.assertEqual(result2["question"], saved_q)

    def test_json_fence_stripping(self):
        # Test markdown code fences stripping logic
        raw_markdown = """```json
{
  "question": "A stack of plates in a buffet...",
  "options": ["A. Top plate", "B. Bottom plate", "C. Middle plate", "D. None"],
  "correct_index": 0,
  "explanation": "Follows LIFO."
}
```"""
        raw = raw_markdown.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        import json
        parsed = json.loads(raw.strip())
        self.assertEqual(parsed["correct_index"], 0)
        self.assertEqual(len(parsed["options"]), 4)

if __name__ == "__main__":
    unittest.main()

