import asyncio
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.checkpoint_service import checkpoint_service

async def test_question_ordering_and_types():
    mock_concepts = [
        {
            "id": 1,
            "title": "Introduction to Functions",
            "description": "Definition of inputs, outputs, domain and range.",
            "start_time": 0.0,
            "end_time": 120.0,
            "transcript_text": "A function maps every legal input from its domain to exactly one output value in its range.",
            "core_concepts": ["Function mappings", "Domain and Range"]
        },
        {
            "id": 2,
            "title": "Pure Functions & Determinism",
            "description": "Explains no side effects and referential transparency.",
            "start_time": 120.0,
            "end_time": 240.0,
            "transcript_text": "A pure function given the exact same input will always return the exact same output without side effects.",
            "core_concepts": ["Purity", "Determinism"]
        }
    ]

    mock_transcript = " ".join([c["transcript_text"] for c in mock_concepts])

    questions = await checkpoint_service.generate_lecture_checkpoints(
        concepts=mock_concepts,
        full_transcript=mock_transcript,
        lecture_title="Functions & Purity"
    )

    print(f"Generated {len(questions)} checkpoints.")
    assert len(questions) >= 4, f"Expected at least 4 questions, got {len(questions)}"

    seen_non_mcq = False
    for idx, q in enumerate(questions):
        q_type = q.get("question_type")
        assert q_type in ["mcq", "short", "scenario"], f"Invalid question_type: {q_type}"
        assert q.get("order_index") == idx, f"order_index {q.get('order_index')} != {idx}"

        if q_type == "mcq":
            assert not seen_non_mcq, f"Found MCQ at index {idx} AFTER a short/scenario question! Order must put all MCQs first."
            assert len(q.get("options", [])) == 4, f"MCQ at {idx} must have 4 options"
        else:
            seen_non_mcq = True
            assert len(q.get("options", [])) == 0, f"Non-MCQ at {idx} should have empty options"

    # Verify both MCQs and short answers are present
    mcqs = [q for q in questions if q["question_type"] == "mcq"]
    shorts = [q for q in questions if q["question_type"] in ["short", "scenario"]]
    print(f"Count of MCQs (first): {len(mcqs)}")
    print(f"Count of Short/Scenario (end): {len(shorts)}")
    assert len(mcqs) > 0, "No MCQs generated"
    assert len(shorts) > 0, "No short-answer questions generated"

    # Verify difficulty ordering within MCQs
    mcq_diffs = [q.get("difficulty") for q in mcqs]
    seen_moderate_mcq = False
    for d in mcq_diffs:
        if d == "moderate":
            seen_moderate_mcq = True
        elif d == "easy" and seen_moderate_mcq:
            raise AssertionError(f"MCQ Easy appeared after Moderate: {mcq_diffs}")

    print("[PASS] Test Step 2 passed: All MCQs are first, short-answer questions are at the end, and question_type is explicit.")

if __name__ == "__main__":
    asyncio.run(test_question_ordering_and_types())

