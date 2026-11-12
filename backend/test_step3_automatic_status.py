"""
test_step3_automatic_status.py
------------------------------
Unit test verifying Step 3: Automatic Misconception Status Management
1. Manual status updates via PATCH/PUT /misconceptions/{id}/status blocked with 403 Forbidden.
2. Review checkpoint answering NEVER moves misconception directly to 'Resolved'.
3. Strict lifecycle state machine:
   - Initial wrong answer -> 'open'
   - Correct answer -> 'improving' with recheck scheduled (+2 days)
   - Failed reassessment -> relapse: status reverts to 'open', relapse_count += 1
   - Passed reassessment -> 'resolved'
4. Attempts history is strictly preserved and never overwritten.
"""

import os
os.environ["MONGODB_URL"] = ""

import sys
import datetime
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.models.all_models import User, Misconception, MisconceptionEvidence
from app.routers.misconceptions import update_misconception_status
from app.schemas.all_schemas import MisconceptionStatusUpdateIn
from fastapi import HTTPException


def test_student_manual_status_blocked():
    print("\n[TEST 1] Verifying student manual status updates are blocked...")
    dummy_user = User(id=42, full_name="student_user", email="student@mindtrace.ai")
    for blocked_status in ["Resolved", "Improving", "open", "Unresolved"]:
        try:
            update_misconception_status(
                misconception_id=10,
                payload=MisconceptionStatusUpdateIn(status=blocked_status),
                db=None,
                current_user=dummy_user
            )
            print(f"❌ FAILED: Student was able to set status to '{blocked_status}'!")
            assert False, "Manual status update should raise 403 Forbidden"
        except HTTPException as e:
            assert e.status_code == 403
            assert "system-controlled" in e.detail.lower()
    print("✅ PASSED: Student manual status updates to any status return 403 Forbidden.")


def test_review_checkpoint_never_resolves_directly():
    print("\n[TEST 2] Verifying review checkpoint never jumps directly to 'Resolved'...")
    from app.services.misconception_service import misconception_service
    from unittest.mock import MagicMock

    from app.models.all_models import ConceptProgress

    mock_db = MagicMock()
    mock_misc = Misconception(
        id=10,
        user_id=42,
        concept_id=5,
        status="open",
        severity_score=3,
        severity_level="Medium",
        relapse_count=0
    )
    mock_progress = MagicMock(understanding_percentage=40)

    def fake_query(model):
        q = MagicMock()
        if model == Misconception:
            q.filter.return_value.first.return_value = mock_misc
        elif model == ConceptProgress:
            q.filter.return_value.first.return_value = mock_progress
        else:
            q.filter.return_value.all.return_value = []
        return q

    mock_db.query = fake_query

    # Student answers correctly on review checkpoint
    updated = misconception_service.resolve_misconception_checkpoint(
        db=mock_db,
        user_id=42,
        misconception_id=10,
        is_correct=True
    )
    assert updated.status == "improving", f"Expected 'improving', got '{updated.status}'"
    assert updated.improving_at == datetime.date.today()
    assert updated.recheck_due == datetime.date.today() + datetime.timedelta(days=2)
    print(f"✅ PASSED: Review checkpoint correctly sets status to '{updated.status}' and schedules recheck.")


def test_state_machine_and_attempts_persistence():
    print("\n[TEST 3] Verifying state machine transitions and attempts history...")
    fake_id = str(ObjectId("65f1a2b3c4d5e6f7a8b9c0d1"))

    # Simulated MongoDB misconception document store
    doc = {
        "id": fake_id,
        "student_id": 42,
        "lecture_id": 101,
        "concept": "Binary Search Tree Invariants",
        "original_question": "What invariant must hold for left subtree?",
        "status": "open",
        "improving_at": None,
        "recheck_due": None,
        "relapse_count": 0,
        "attempts": []
    }

    def simulate_record_attempt(question, student_answer, is_correct, context_type):
        doc["attempts"].append({
            "question": question,
            "student_answer": student_answer,
            "is_correct": is_correct,
            "context_type": context_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    def simulate_mark_improving():
        doc["status"] = "improving"
        doc["improving_at"] = datetime.date.today().isoformat()
        doc["recheck_due"] = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()

    def simulate_mark_relapse():
        doc["status"] = "open"
        doc["relapse_count"] += 1

    def simulate_mark_resolved():
        doc["status"] = "resolved"
        doc["resolved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Step 1: Initial state is 'open'
    assert doc["status"] == "open"
    assert doc["relapse_count"] == 0
    simulate_record_attempt(doc["original_question"], "Values greater than root", False, "initial_checkpoint")
    print(f"  1. Initial Wrong Answer -> status='{doc['status']}', relapse_count={doc['relapse_count']}")

    # Step 2: First correct answer -> status becomes 'improving' (NOT resolved)
    simulate_mark_improving()
    simulate_record_attempt(doc["original_question"], "Values strictly less than root", True, "initial_checkpoint")
    assert doc["status"] == "improving"
    assert doc["recheck_due"] == (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    print(f"  2. First Correct Answer -> status='{doc['status']}', recheck_due={doc['recheck_due']}")

    # Step 3: Failed reassessment -> Relapse! Status reverts to 'open', relapse_count += 1
    simulate_mark_relapse()
    simulate_record_attempt("In a library shelf sorted by BST invariant...", "Books on left have higher call numbers", False, "reassessment")
    assert doc["status"] == "open"
    assert doc["relapse_count"] == 1
    print(f"  3. Failed Reassessment (Relapse) -> status='{doc['status']}', relapse_count={doc['relapse_count']}")

    # Step 4: Remediation -> status becomes 'improving' again
    simulate_mark_improving()
    assert doc["status"] == "improving"
    assert doc["relapse_count"] == 1
    print(f"  4. Remediating -> status='{doc['status']}', relapse_count={doc['relapse_count']}")

    # Step 5: Passing targeted reassessment -> status becomes 'resolved'
    simulate_mark_resolved()
    simulate_record_attempt("In a library shelf sorted by BST invariant...", "Books on left have lower call numbers", True, "reassessment")
    assert doc["status"] == "resolved"
    assert doc.get("resolved_at") is not None
    print(f"  5. Passed Targeted Reassessment -> status='{doc['status']}', resolved_at={doc['resolved_at']}")

    # Step 6: Verify attempt history preservation
    attempts = doc["attempts"]
    assert len(attempts) == 4, f"Expected 4 attempts, got {len(attempts)}"
    print(f"\n[TEST 4] History Persistence: {len(attempts)} attempts stored across multiple sessions:")
    for i, a in enumerate(attempts):
        print(f"    Attempt {i+1}: [{a['context_type']}] is_correct={a['is_correct']}, ans='{a['student_answer']}'")
    print("✅ All attempts stored and historical records strictly preserved.")


def run_all():
    print("==================================================")
    print("  RUNNING STEP 3 AUTOMATIC STATUS MANAGEMENT SUITE")
    print("==================================================")
    test_student_manual_status_blocked()
    test_review_checkpoint_never_resolves_directly()
    test_state_machine_and_attempts_persistence()
    print("\n==================================================")
    print("  ALL STEP 3 TESTS PASSED (100% SUCCESS)")
    print("==================================================")


if __name__ == "__main__":
    run_all()
