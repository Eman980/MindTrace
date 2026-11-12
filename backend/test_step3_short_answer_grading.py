import asyncio
import os
import sys
import datetime
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, Misconception
from app.schemas.all_schemas import CheckpointAnswerIn
from app.routers.checkpoints import submit_checkpoint_answer
from app.services.evaluation_service import evaluation_service

async def test_short_answer_grading_and_lifecycle():
    question = "In your own words, why is a function described as a 'black box'?"
    reference = "It takes inputs and returns an output based on internal logic without requiring the caller to know the internal implementation."
    explanation = "Callers rely on the inputs and output contract without depending on internal execution details."

    print("--- 1. Testing Guard: < 4 words ---")
    # Test 1: Single letter "u" (The user's reported bug)
    res_u = await evaluation_service.evaluate_answer(
        question_type="short",
        question_text=question,
        correct_answer=reference,
        student_answer="u",
        explanation=explanation
    )
    print(f"Result for 'u': verdict={res_u.get('verdict')}, correct={res_u.get('correct')}, feedback={res_u.get('feedback')}")
    assert res_u["correct"] is False, f"Expected False for 'u', got {res_u['correct']}"
    assert res_u["verdict"] == "incorrect", f"Expected 'incorrect' for 'u', got {res_u['verdict']}"

    # Test 2: Two words "black box"
    res_two = await evaluation_service.evaluate_answer(
        question_type="short",
        question_text=question,
        correct_answer=reference,
        student_answer="black box",
        explanation=explanation
    )
    assert res_two["correct"] is False
    assert res_two["verdict"] == "incorrect"

    # Test 3: Three words "hides its code"
    res_three = await evaluation_service.evaluate_answer(
        question_type="short",
        question_text=question,
        correct_answer=reference,
        student_answer="hides its code",
        explanation=explanation
    )
    assert res_three["correct"] is False
    assert res_three["verdict"] == "incorrect"
    print("[PASS] < 4 words guard verified: all return 'incorrect' and correct=False immediately.")

    print("\n--- 2. Testing Incorrect Answer (>= 4 words) ---")
    res_wrong = await evaluation_service.evaluate_answer(
        question_type="short",
        question_text=question,
        correct_answer=reference,
        student_answer="A function permanently writes changes to external hard drive storage disks.",
        explanation=explanation
    )
    print(f"Result for wrong answer: verdict={res_wrong.get('verdict')}, correct={res_wrong.get('correct')}, feedback={res_wrong.get('feedback')}")
    assert res_wrong["correct"] is False
    assert res_wrong["verdict"] in ["incorrect", "partial"]
    print("[PASS] Incorrect answer evaluated as not correct.")

    print("\n--- 3. Testing Correct Answer (>= 4 words) ---")
    res_correct = await evaluation_service.evaluate_answer(
        question_type="short",
        question_text=question,
        correct_answer=reference,
        student_answer="Because you only need to know what goes in and comes out, without needing to know internal implementation details.",
        explanation=explanation
    )
    print(f"Result for correct answer: verdict={res_correct.get('verdict')}, correct={res_correct.get('correct')}, feedback={res_correct.get('feedback')}")
    assert res_correct["correct"] is True, f"Expected True for correct explanation, got {res_correct}"
    assert res_correct["verdict"] == "correct", f"Expected verdict='correct', got {res_correct.get('verdict')}"
    print("[PASS] Proper explanation in own words is evaluated as correct.")

    print("\n--- 4. Testing MCQ intact ---")
    res_mcq_correct = await evaluation_service.evaluate_answer(
        question_type="mcq",
        question_text="What does f(x) signify?",
        correct_answer="B. The input argument passed into the function",
        student_answer="B",
        explanation="x is the argument."
    )
    assert res_mcq_correct["correct"] is True
    assert res_mcq_correct["verdict"] == "correct"

    res_mcq_wrong = await evaluation_service.evaluate_answer(
        question_type="mcq",
        question_text="What does f(x) signify?",
        correct_answer="B. The input argument passed into the function",
        student_answer="A",
        explanation="x is the argument."
    )
    assert res_mcq_wrong["correct"] is False
    assert res_mcq_wrong["verdict"] == "incorrect"
    print("[PASS] MCQ behavior completely intact.")

    print("\n--- 5. Testing Endpoint Lifecycle Integration (/answer) ---")
    db = SessionLocal()
    try:
        ts = int(datetime.datetime.now().timestamp() * 1000)
        user = User(
            email=f"step3_test_{ts}@mindtrace.edu",
            hashed_password="pw_test",
            full_name="Step 3 Student",
            role="student"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        lec = Lecture(user_id=user.id, title="Test Lecture", course_code="CS101", status="ready")
        db.add(lec)
        db.commit()
        db.refresh(lec)

        c = Concept(
            lecture_id=lec.id,
            title="Black Box Concept",
            description="A concept explaining black box functions",
            start_time=0.0,
            end_time=60.0
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        chk = Checkpoint(
            concept_id=c.id,
            question_type="short",
            difficulty="easy",
            question_text=question,
            options=[],
            correct_answer=reference,
            explanation=explanation,
            order_index=0
        )
        db.add(chk)
        db.commit()
        db.refresh(chk)

        # 5a. Submit "u" -> must be incorrect, 0 points, status "open", LLM verdict "incorrect"
        ans_u = CheckpointAnswerIn(checkpoint_id=chk.id, student_answer="u")
        res_endpoint_u = await submit_checkpoint_answer(answer_in=ans_u, db=db, current_user=user)
        print(f"Endpoint result for 'u': is_correct={res_endpoint_u['is_correct']}, points={res_endpoint_u['points_awarded']}, verdict={res_endpoint_u['verdict']}, LLM_verdict={res_endpoint_u.get('explanation_verdict')}, status={res_endpoint_u['misconception_status']}")
        assert res_endpoint_u["is_correct"] is False
        assert res_endpoint_u["verdict"] == "incorrect"
        assert res_endpoint_u["points_awarded"] == 0
        assert res_endpoint_u["misconception_status"] == "open"
        assert res_endpoint_u["explanation_verdict"] == "incorrect", f"Expected explanation_verdict='incorrect', got {res_endpoint_u.get('explanation_verdict')}"

        # 5b. Submit valid conceptual answer -> must be correct, 10 points, status "improving", LLM verdict "correct"
        ans_good = CheckpointAnswerIn(
            checkpoint_id=chk.id,
            student_answer="It maps inputs to outputs based on internal logic without exposing implementation details to callers."
        )
        res_endpoint_good = await submit_checkpoint_answer(answer_in=ans_good, db=db, current_user=user)
        print(f"Endpoint result for good answer: is_correct={res_endpoint_good['is_correct']}, points={res_endpoint_good['points_awarded']}, verdict={res_endpoint_good['verdict']}, LLM_verdict={res_endpoint_good.get('explanation_verdict')}, status={res_endpoint_good['misconception_status']}")
        assert res_endpoint_good["is_correct"] is True
        assert res_endpoint_good["verdict"] == "correct"
        assert res_endpoint_good["points_awarded"] == 10
        assert res_endpoint_good["misconception_status"] == "improving"
        assert res_endpoint_good["recheck_due"] is not None
        assert res_endpoint_good["explanation_verdict"] == "correct", f"Expected explanation_verdict='correct', got {res_endpoint_good.get('explanation_verdict')}"

        # Verify attempts stored in database have real LLM verdict (NOT 'not_checked')
        from app.models.all_models import CheckpointAttempt
        attempts = db.query(CheckpointAttempt).filter(CheckpointAttempt.checkpoint_id == chk.id, CheckpointAttempt.user_id == user.id).order_by(CheckpointAttempt.id.asc()).all()
        assert len(attempts) == 2
        assert attempts[0].explanation_verdict == "incorrect", f"Attempt 0 DB explanation_verdict was {attempts[0].explanation_verdict}"
        assert attempts[1].explanation_verdict == "correct", f"Attempt 1 DB explanation_verdict was {attempts[1].explanation_verdict}"

        print("[PASS] /answer lifecycle & LLM Verdict verified: 'u' has LLM Verdict='incorrect', proper answer has LLM Verdict='correct', and DB rows no longer stay 'not_checked'.")
    finally:
        db.close()

    print("\n[ALL STEP 3 TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    asyncio.run(test_short_answer_grading_and_lifecycle())
