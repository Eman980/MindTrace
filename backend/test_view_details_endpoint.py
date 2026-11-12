"""
test_view_details_endpoint.py
-----------------------------
Integration test for Stage 1: GET /api/misconceptions/{id}/details endpoint.
Verifies all 12 required fields returned by the endpoint:
1. Concept Name
2. Why It Was Detected
3. Original Question
4. Student's Wrong Answer
5. Correct Answer
6. Detection Evidence
7. Lecture Evidence ('Evidence not available' if none)
8. Concept Start/End timestamps (for Wrong Answer Replay)
9. Marked Unresolved status and reason
10. Assessment History (attempts list with questions, answers, and results)
11. Current System Status
12. Next Reassessment Information
"""

import sys
import os
from datetime import datetime, timezone
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.main import app
from app.database import get_db, SessionLocal
from app.utils.security import get_current_user
from app.models.all_models import User, Misconception, Concept, Lecture, Checkpoint, CheckpointAttempt

def test_view_details_endpoint():
    print("==================================================")
    print("  RUNNING STAGE 1: VIEW DETAILS ENDPOINT TEST")
    print("==================================================")

    db = SessionLocal()
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)

    # 1. Create test user
    user = User(
        email=f"details_student_{ts}@mindtrace.ai",
        hashed_password="pw_hash_test",
        full_name="Details Student Ali",
        role="student"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Create test lecture & concept
    lecture = Lecture(
        user_id=user.id,
        title="Algorithms & Complexity",
        course_code="CS301",
        status="ready"
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)

    concept = Concept(
        lecture_id=lecture.id,
        title="Binary Search Invariant",
        description="Binary search requires the input array to be strictly sorted.",
        transcript_text="For binary search to divide the search space in half at each step, the precondition is that the collection is sorted. If unsorted, the invariant fails.",
        start_time=145.0,
        end_time=210.0,
        order_index=1,
        core_concepts=["Array must be sorted"],
        confusing_topics=["Applying binary search to unsorted list"]
    )
    db.add(concept)
    db.commit()
    db.refresh(concept)

    # 3. Create diagnostic checkpoint & failed attempt
    checkpoint = Checkpoint(
        concept_id=concept.id,
        question_text="What essential precondition must be met before executing Binary Search?",
        options=["A. The array must be sorted", "B. The array must contain unique elements", "C. The array size must be even", "D. Elements must be positive"],
        correct_answer="A. The array must be sorted",
        explanation="Binary search relies on order comparison to discard half the search space."
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)

    attempt = CheckpointAttempt(
        checkpoint_id=checkpoint.id,
        user_id=user.id,
        student_answer="B. The array must contain unique elements",
        is_correct=False,
        feedback_reason="Uniqueness is not required; duplicates are permitted. The true requirement is that elements must be sorted.",
        confidence_level=3,
        created_at=datetime.now(timezone.utc)
    )
    db.add(attempt)
    db.commit()

    # 4. Create misconception record
    misc = Misconception(
        user_id=user.id,
        lecture_id=lecture.id,
        concept_id=concept.id,
        concept_name=concept.title,
        title="Precondition Misunderstanding in Binary Search",
        summary="Student believes binary search requires unique elements rather than sorted elements.",
        status="open",
        severity_level="High",
        severity_score=7,
        relapse_count=0,
        first_detected=datetime.now(timezone.utc)
    )
    db.add(misc)
    db.commit()
    db.refresh(misc)

    # 5. Execute TestClient request
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)
    response = client.get(f"/api/misconceptions/{misc.id}/details")

    # Clean up overrides
    app.dependency_overrides.clear()

    # 6. Verify assertions
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    print("\n✅ API Response received successfully (HTTP 200):")
    print(f"  • Concept Name: {data['concept_name']}")
    print(f"  • Why Detected: {data['why_detected']}")
    print(f"  • Original Question: {data['original_question']}")
    print(f"  • Student Wrong Answer: {data['student_wrong_answer']}")
    print(f"  • Correct Answer: {data['correct_answer']}")
    print(f"  • Detection Evidence: {data['detection_evidence']}")
    print(f"  • Lecture Evidence: {data['lecture_evidence'][:80]}...")
    print(f"  • Replay Range: {data['concept_start_time']}s - {data['concept_end_time']}s")
    print(f"  • Marked Unresolved: {data['marked_unresolved']} ({data['marked_unresolved_reason']})")
    print(f"  • Current Status: {data['status']}")
    print(f"  • Next Reassessment: {data['next_reassessment_info']}")
    print(f"  • Assessment History Count: {len(data['assessment_history'])}")

    assert data["concept_name"] == "Binary Search Invariant"
    assert data["original_question"] == checkpoint.question_text
    assert data["student_wrong_answer"] == "B. The array must contain unique elements"
    assert data["correct_answer"] == "A. The array must be sorted"
    assert "Uniqueness is not required" in data["detection_evidence"]
    assert "For binary search to divide" in data["lecture_evidence"]
    assert data["concept_start_time"] == 145.0
    assert data["concept_end_time"] == 210.0
    assert data["marked_unresolved"] is True
    assert data["status"] == "open"
    assert len(data["assessment_history"]) >= 1
    assert data["assessment_history"][0]["student_answer"] == "B. The array must contain unique elements"
    assert data["assessment_history"][0]["is_correct"] is False

    print("\n==================================================")
    print("  STAGE 1 TEST PASSED (100% SUCCESS)!")
    print("==================================================")
    db.close()

if __name__ == "__main__":
    test_view_details_endpoint()
