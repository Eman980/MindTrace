import asyncio
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, CheckpointAttempt, Misconception
from app.schemas.all_schemas import CheckpointAnswerIn
from app.routers.checkpoints import submit_checkpoint_answer
from app.services.checkpoint_service import checkpoint_service

async def test_full_system_verification():
    print("==================================================")
    print("STEP 4: FULL SYSTEM VERIFICATION")
    print("==================================================")

    db = SessionLocal()
    try:
        ts = int(datetime.datetime.now().timestamp() * 1000)
        user = User(
            email=f"verify_student_{ts}@mindtrace.edu",
            hashed_password="pw_test",
            full_name="Verification Student",
            role="student"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 1. Test Checkpoints Generation & Ordering
        mock_concepts = [
            {
                "id": 1,
                "title": "Recursion Fundamentals",
                "description": "Base cases and activation records.",
                "start_time": 0.0,
                "end_time": 120.0,
                "transcript_text": "In recursion, we always have a base case that terminates the recursive execution.",
                "core_concepts": ["Base cases", "Termination"]
            },
            {
                "id": 2,
                "title": "Call Stack Operations",
                "description": "Pushing and popping activation frames.",
                "start_time": 120.0,
                "end_time": 240.0,
                "transcript_text": "Each recursive call allocates a new frame on top of the call stack.",
                "core_concepts": ["Call stack", "Stack frames"]
            }
        ]
        questions = await checkpoint_service.generate_lecture_checkpoints(
            concepts=mock_concepts,
            full_transcript="In recursion, we always have a base case that terminates recursive execution. Each recursive call allocates a new frame on the call stack.",
            lecture_title="Recursion & Call Stacks"
        )

        print(f"\n[1] Checkpoint Ordering Check: Generated {len(questions)} questions")
        seen_non_mcq = False
        for idx, q in enumerate(questions):
            q_type = q.get("question_type")
            assert q_type in ["mcq", "short", "scenario"]
            if q_type == "mcq":
                assert not seen_non_mcq, f"MCQ found after short question at index {idx}"
            else:
                seen_non_mcq = True

        mcqs = [q for q in questions if q["question_type"] == "mcq"]
        shorts = [q for q in questions if q["question_type"] != "mcq"]
        print(f"    MCQs count: {len(mcqs)} (indices 0 to {len(mcqs)-1})")
        print(f"    Short/Scenario count: {len(shorts)} (indices {len(mcqs)} to {len(questions)-1})")
        assert len(mcqs) > 0 and len(shorts) > 0
        print("    [PASS] All MCQs strictly precede short-answer questions!")

        # 2. Test Answering "u" on a short-answer question
        lec = Lecture(user_id=user.id, title="Recursion", course_code="CS101", status="ready")
        db.add(lec)
        db.commit()
        db.refresh(lec)

        c = Concept(lecture_id=lec.id, title="Base Case Concept", description="Understanding base cases", start_time=0.0, end_time=60.0)
        db.add(c)
        db.commit()
        db.refresh(c)

        chk_short = Checkpoint(
            concept_id=c.id,
            question_type="short",
            difficulty="easy",
            question_text="In your own words, briefly state why a base case is necessary in recursion.",
            options=[],
            correct_answer="A base case is necessary to stop recursive calls and prevent infinite recursion or stack overflow.",
            explanation="Without a base case, recursive calls continue indefinitely until stack memory is exhausted.",
            order_index=4
        )
        db.add(chk_short)
        db.commit()
        db.refresh(chk_short)

        print("\n[2] Testing Bug Report 1: Typing 'u' into short-answer question")
        ans_u = CheckpointAnswerIn(checkpoint_id=chk_short.id, student_answer="u")
        res_u = await submit_checkpoint_answer(answer_in=ans_u, db=db, current_user=user)
        print(f"    is_correct: {res_u['is_correct']}")
        print(f"    verdict: {res_u['verdict']}")
        print(f"    points_awarded: {res_u['points_awarded']}")
        print(f"    explanation_verdict (LLM Verdict): {res_u['explanation_verdict']}")
        print(f"    feedback: {res_u['feedback']}")
        assert res_u["is_correct"] is False, "Typing 'u' must NOT be marked correct!"
        assert res_u["verdict"] == "incorrect"
        assert res_u["points_awarded"] == 0, "Typing 'u' must award 0 points!"
        assert res_u["explanation_verdict"] == "incorrect", "LLM Verdict must be 'incorrect'!"
        print("    [PASS] 'u' correctly marked incorrect with 0 points!")

        # 3. Test Proper Conceptual Answer
        print("\n[3] Testing Proper Answer into short-answer question")
        ans_good = CheckpointAnswerIn(
            checkpoint_id=chk_short.id,
            student_answer="A base case provides the termination condition so recursion stops before stack overflow."
        )
        res_good = await submit_checkpoint_answer(answer_in=ans_good, db=db, current_user=user)
        print(f"    is_correct: {res_good['is_correct']}")
        print(f"    verdict: {res_good['verdict']}")
        print(f"    points_awarded: {res_good['points_awarded']}")
        print(f"    explanation_verdict (LLM Verdict): {res_good['explanation_verdict']}")
        print(f"    feedback: {res_good['feedback']}")
        assert res_good["is_correct"] is True, "Proper answer must be marked correct!"
        assert res_good["verdict"] == "correct"
        assert res_good["points_awarded"] == 10, "Correct answer must award 10 points!"
        assert res_good["explanation_verdict"] == "correct", "LLM Verdict must be 'correct'!"
        print("    [PASS] Proper answer verified: 10 points awarded and LLM Verdict='correct'!")

        # 4. Check Database Attempt Rows for Ledger Page
        print("\n[4] Testing Bug Report 3: Checking DB rows for Ledger 'LLM Verdict'")
        db_attempts = db.query(CheckpointAttempt).filter(
            CheckpointAttempt.checkpoint_id == chk_short.id,
            CheckpointAttempt.user_id == user.id
        ).order_by(CheckpointAttempt.id.asc()).all()
        assert len(db_attempts) == 2
        print(f"    Attempt 1 (answering 'u') explanation_verdict: '{db_attempts[0].explanation_verdict}'")
        print(f"    Attempt 2 (proper answer) explanation_verdict: '{db_attempts[1].explanation_verdict}'")
        assert db_attempts[0].explanation_verdict == "incorrect"
        assert db_attempts[1].explanation_verdict == "correct"
        assert db_attempts[0].explanation_verdict != "not_checked"
        assert db_attempts[1].explanation_verdict != "not_checked"
        print("    [PASS] Ledger 'LLM Verdict' field now saves real verdicts instead of staying 'not_checked'!")

        print("\n==================================================")
        print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
        print("==================================================")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_full_system_verification())

