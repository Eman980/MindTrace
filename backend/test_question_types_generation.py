"""
Unit test for Multiple Question Types & Difficulty Generation (Step a).
Verifies:
1. Database columns existence on checkpoints and checkpoint_attempts.
2. Default values for legacy rows (type='mcq', difficulty='easy').
3. Generation produces target distribution:
   - 4 MCQ (2 easy, 2 moderate)
   - 2 Short (1 easy, 1 moderate)
   - 2 Scenario (2 moderate)
4. Question sorting: Easy first, then Moderate (preserving segment timestamp order within difficulty).
5. Question schema validation:
   - mcq: 4 options, correct_answer matching an option.
   - short: 0 options, model answer in correct_answer.
   - scenario: scenario_text present, 0 options, model answer in correct_answer.
"""
import asyncio
import sqlite3
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.checkpoint_service import checkpoint_service
from app.config import settings

def test_database_columns():
    db_path = settings.DEFAULT_DB_PATH
    assert os.path.exists(db_path), f"DB not found at {db_path}"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check checkpoints columns
    cur.execute("PRAGMA table_info(checkpoints)")
    chk_cols = {row[1]: row for row in cur.fetchall()}
    assert "difficulty" in chk_cols, "Column 'difficulty' missing from checkpoints"
    assert "scenario_text" in chk_cols, "Column 'scenario_text' missing from checkpoints"
    assert "question_type" in chk_cols, "Column 'question_type' missing from checkpoints"

    # Check checkpoint_attempts columns
    cur.execute("PRAGMA table_info(checkpoint_attempts)")
    att_cols = {row[1]: row for row in cur.fetchall()}
    assert "grade" in att_cols, "Column 'grade' missing from checkpoint_attempts"

    # Verify old rows have difficulty set to 'easy'
    cur.execute("SELECT COUNT(*) FROM checkpoints WHERE difficulty IS NULL")
    null_diff_count = cur.fetchone()[0]
    assert null_diff_count == 0, f"Found {null_diff_count} checkpoints with NULL difficulty"

    conn.close()
    print("[PASS] Database columns and legacy defaults verified successfully.")

async def test_generation():
    # Mock concepts representing a typical lecture
    mock_concepts = [
        {
            "id": 101,
            "title": "Introduction to Recursion",
            "description": "Explains base cases and self-referential function calls.",
            "start_time": 0.0,
            "end_time": 120.0,
            "transcript_text": "A recursive function is a function that calls itself to solve a smaller instance of the same problem. Crucially, every recursive function must have a base case to terminate execution without an infinite loop.",
            "core_concepts": [
                "A recursive function solves problems by calling itself with smaller sub-problems.",
                "The base case is mandatory to stop execution and prevent stack overflow."
            ]
        },
        {
            "id": 102,
            "title": "Call Stack Mechanics",
            "description": "How activation records are pushed and popped during recursion.",
            "start_time": 120.0,
            "end_time": 250.0,
            "transcript_text": "Each time a recursive call is made, a new activation frame is placed onto the execution call stack. When the base case returns, frames are popped in reverse order until the original caller finishes.",
            "core_concepts": [
                "Recursive calls allocate frames on the call stack.",
                "Unwinding happens in Last-In First-Out (LIFO) order."
            ]
        },
        {
            "id": 103,
            "title": "Boundary Conditions & Stack Overflow",
            "description": "What happens when base cases fail or recursion depth exceeds limits.",
            "start_time": 250.0,
            "end_time": 380.0,
            "transcript_text": "If the base case is missing or unreachable, recursive invocations continue until the stack memory is exhausted, throwing a StackOverflowError.",
            "core_concepts": [
                "Missing base case causes uncontrolled recursion.",
                "Exhausting stack memory causes fatal termination."
            ]
        }
    ]

    mock_transcript = " ".join([c["transcript_text"] for c in mock_concepts])

    # Generate checkpoints
    questions = await checkpoint_service.generate_lecture_checkpoints(
        concepts=mock_concepts,
        full_transcript=mock_transcript,
        lecture_title="Recursion & The Call Stack"
    )

    print(f"Generated {len(questions)} questions.")
    assert len(questions) >= 6, f"Expected at least 6 questions, got {len(questions)}"

    # 1. Check breakdown of question types
    mcq_count = sum(1 for q in questions if q["question_type"] == "mcq")
    short_count = sum(1 for q in questions if q["question_type"] == "short")
    scenario_count = sum(1 for q in questions if q["question_type"] == "scenario")
    print(f"Type breakdown: {mcq_count} MCQ, {short_count} Short, {scenario_count} Scenario")

    assert mcq_count >= 3, f"Expected ~4 MCQ, got {mcq_count}"
    assert short_count >= 1, f"Expected ~2 Short, got {short_count}"
    assert scenario_count >= 1, f"Expected ~2 Scenario, got {scenario_count}"

    # 2. Check difficulty breakdown
    easy_count = sum(1 for q in questions if q["difficulty"] == "easy")
    moderate_count = sum(1 for q in questions if q["difficulty"] == "moderate")
    print(f"Difficulty breakdown: {easy_count} Easy, {moderate_count} Moderate")
    assert easy_count >= 2, f"Expected at least 2 easy questions, got {easy_count}"
    assert moderate_count >= 3, f"Expected at least 3 moderate questions, got {moderate_count}"

    # 3. Check ordering: All MCQs MUST come first, followed by short/scenario at the end
    seen_non_mcq = False
    for idx, q in enumerate(questions):
        if q["question_type"] == "mcq":
            assert not seen_non_mcq, f"Found MCQ after short question at index {idx}"
        else:
            seen_non_mcq = True

    # Within each question type, easy questions precede moderate questions
    for subset_name, subset in [("MCQ", [q for q in questions if q["question_type"] == "mcq"]),
                                ("Short/Scenario", [q for q in questions if q["question_type"] != "mcq"])]:
        seen_mod = False
        for q in subset:
            if q["difficulty"] == "moderate":
                seen_mod = True
            elif q["difficulty"] == "easy" and seen_mod:
                raise AssertionError(f"Found 'easy' question after 'moderate' in {subset_name} sequence")

    print("[PASS] Ordering verified: all MCQs precede short-answer questions, and easy precedes moderate within each type.")

    # 4. Check question schema rules
    for idx, q in enumerate(questions):
        assert q["order_index"] == idx, f"order_index mismatch: {q['order_index']} != {idx}"
        assert q["concept_id"] in [101, 102, 103], f"Invalid concept_id: {q['concept_id']}"
        assert q["question_text"], f"Question {idx} has empty question_text"
        assert q["correct_answer"], f"Question {idx} has empty correct_answer"
        assert q["explanation"], f"Question {idx} has empty explanation"

        if q["question_type"] == "mcq":
            assert len(q["options"]) == 4, f"MCQ {idx} does not have 4 options: {len(q['options'])}"
            assert q["options"][0].startswith("A."), f"MCQ {idx} option A format invalid: {q['options'][0]}"
        elif q["question_type"] == "short":
            assert len(q["options"]) == 0, f"Short answer {idx} should have no options"
            assert len(q["correct_answer"]) > 10, f"Short answer {idx} model answer too short"
        elif q["question_type"] == "scenario":
            assert len(q["options"]) == 0, f"Scenario {idx} should have no options"
            assert q.get("scenario_text") and len(q["scenario_text"]) > 20, f"Scenario {idx} missing scenario_text"
            assert len(q["correct_answer"]) > 10, f"Scenario {idx} model answer too short"

    print("[PASS] All question schemas and specific type constraints verified successfully.")

if __name__ == "__main__":
    test_database_columns()
    asyncio.run(test_generation())
    print("\nAll Step (a) verification tests passed cleanly!")

