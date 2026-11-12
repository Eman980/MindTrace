"""
test_step5_rechecks_and_report.py
---------------------------------
Unit test verifying Step 5:
1. GET /rechecks/due:
   - Returns misconceptions where status == 'improving' and recheck_due <= today.
   - Ignores future rechecks and open/resolved status.
2. GET /report and GET /report/{recording_id}:
   - Returns status counts: open, improving, resolved.
   - Returns relapse list where relapse_count > 0, labeled 'memorized, not understood'.
   - Preserves existing recording report fields.
"""

import sys
import os
import unittest
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Misconception, Checkpoint, CheckpointAttempt
from app.routers.disguise import get_due_rechecks_endpoint
from app.routers.lectures import get_recording_report_endpoint
from app.routers.workflow import workflow_general_report

class TestStep5RechecksAndReport(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SessionLocal()
        ts = int(datetime.datetime.now().timestamp() * 1000)
        self.user = User(
            email=f"step5_student_{ts}@mindtrace.edu",
            hashed_password="pw_hash_test",
            full_name="Step 5 Test Student",
            role="student"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.lecture = Lecture(
            user_id=self.user.id,
            title="Advanced Algorithms",
            course_code="CS301",
            status="ready",
            duration_seconds=3600.0
        )
        self.db.add(self.lecture)
        self.db.commit()
        self.db.refresh(self.lecture)

        self.concept = Concept(
            lecture_id=self.lecture.id,
            title="Graph Depth First Search",
            description="DFS traversal using recursion/stack",
            start_time=0.0,
            end_time=300.0,
            order_index=0
        )
        self.db.add(self.concept)
        self.db.commit()
        self.db.refresh(self.concept)

        today = datetime.date.today()
        past_date = today - datetime.timedelta(days=1)
        future_date = today + datetime.timedelta(days=2)

        # 1. Improving & Due Misconception (should be in /rechecks/due)
        self.m_due = Misconception(
            user_id=self.user.id,
            lecture_id=self.lecture.id,
            concept_id=self.concept.id,
            concept_name="Graph DFS Traversal",
            title="Confusing DFS backtracking with BFS queue",
            status="improving",
            improving_at=past_date,
            recheck_due=past_date,
            relapse_count=0
        )
        self.db.add(self.m_due)

        # 2. Improving but NOT due yet (recheck_due in future)
        self.m_not_due = Misconception(
            user_id=self.user.id,
            lecture_id=self.lecture.id,
            concept_id=self.concept.id,
            concept_name="Graph BFS Traversal",
            title="BFS queue invariant confusion",
            status="improving",
            improving_at=today,
            recheck_due=future_date,
            relapse_count=0
        )
        self.db.add(self.m_not_due)

        # 3. Open Misconception with Relapse (relapse_count = 2)
        self.m_relapse = Misconception(
            user_id=self.user.id,
            lecture_id=self.lecture.id,
            concept_id=self.concept.id,
            concept_name="Recursion Stack Overflow",
            title="Base case omission in recursion",
            status="open",
            improving_at=None,
            recheck_due=None,
            relapse_count=2,
            summary="Student failed disguise test twice."
        )
        self.db.add(self.m_relapse)

        # 4. Resolved Misconception
        self.m_resolved = Misconception(
            user_id=self.user.id,
            lecture_id=self.lecture.id,
            concept_id=self.concept.id,
            concept_name="Binary Tree Inorder",
            title="Inorder vs Preorder traversal",
            status="Resolved",
            improving_at=past_date,
            recheck_due=past_date,
            relapse_count=0
        )
        self.db.add(self.m_resolved)

        self.db.commit()

    def tearDown(self):
        self.db.close()

    async def test_due_rechecks_endpoint(self):
        # Call /rechecks/due
        due_items = await get_due_rechecks_endpoint(
            db=self.db,
            current_user=self.user
        )

        # Only m_due should be returned (not m_not_due, not m_relapse, not m_resolved)
        due_ids = [str(item["misconception_id"]) for item in due_items]
        self.assertIn(str(self.m_due.id), due_ids)
        self.assertNotIn(str(self.m_not_due.id), due_ids)
        self.assertNotIn(str(self.m_relapse.id), due_ids)
        self.assertNotIn(str(self.m_resolved.id), due_ids)

        # Verify fields
        item = next(it for it in due_items if str(it["misconception_id"]) == str(self.m_due.id))
        self.assertEqual(item["concept_name"], "Graph DFS Traversal")
        self.assertEqual(item["status"], "improving")
        self.assertIsNotNone(item["recheck_due"])

    async def test_recording_report_endpoint(self):
        # Call /report/{recording_id}
        rep = await get_recording_report_endpoint(
            recording_id=self.lecture.id,
            db=self.db,
            current_user=self.user
        )

        # 1. Verify status counts
        status_counts = rep["status_counts"]
        self.assertEqual(status_counts["open"], 1)       # m_relapse
        self.assertEqual(status_counts["improving"], 2)  # m_due, m_not_due
        self.assertEqual(status_counts["resolved"], 1)   # m_resolved

        # 2. Verify relapse list
        relapses = rep["relapse_list"]
        self.assertEqual(len(relapses), 1)
        relapse_entry = relapses[0]
        self.assertEqual(str(relapse_entry["misconception_id"]), str(self.m_relapse.id))
        self.assertEqual(relapse_entry["concept"], "Recursion Stack Overflow")
        self.assertEqual(relapse_entry["relapse_count"], 2)
        self.assertEqual(relapse_entry["label"], "memorized, not understood")

        # 3. Verify existing report fields are preserved
        self.assertEqual(rep["recording_id"], self.lecture.id)
        self.assertEqual(rep["title"], "Advanced Algorithms")
        self.assertEqual(rep["duration_seconds"], 3600.0)

    async def test_general_report_endpoint(self):
        # Call general /report
        gen_rep = await workflow_general_report(
            db=self.db,
            current_user=self.user
        )
        self.assertEqual(gen_rep["status_counts"]["open"], 1)
        self.assertEqual(gen_rep["status_counts"]["improving"], 2)
        self.assertEqual(gen_rep["status_counts"]["resolved"], 1)
        self.assertEqual(len(gen_rep["relapse_list"]), 1)
        self.assertEqual(gen_rep["relapse_list"][0]["label"], "memorized, not understood")

if __name__ == "__main__":
    unittest.main()

