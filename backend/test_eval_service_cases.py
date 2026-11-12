import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.evaluation_service import evaluation_service

async def run_tests():
    q = "What is HTML?"
    ref = "HTML is the standard markup language used for structuring web pages."
    exp = "HTML defines elements and structure of web pages."
    
    cases = [
        ("Hi", "incorrect"),
        ("Hello", "incorrect"),
        ("I don't know", "unanswered"),
        ("idk", "unanswered"),
        ("asdfghjkl", "incorrect"),
        ("", "unanswered"),
        ("   ", "unanswered"),
        ("HTML is a markup language used to structure web pages.", "correct"),
        ("HTML is used to create websites.", "partial"),
        ("CSS is used to style web pages.", "incorrect"),
        ("HTML is the standard markup language for creating the structural foundation of web pages.", "correct"),
        ("u", "incorrect"),
        ("Okay", "incorrect"),
        ("Thanks", "incorrect"),
    ]
    
    all_passed = True
    print("\n--- TEST EVALUATION SERVICE CASES ---")
    for student_ans, expected_verdict in cases:
        res = await evaluation_service.evaluate_answer(
            question_type="short_answer",
            question_text=q,
            correct_answer=ref,
            student_answer=student_ans,
            explanation=exp
        )
        passed = (res["verdict"] == expected_verdict)
        if not passed:
            all_passed = False
        print(f"Ans: {student_ans!r:<55} -> Verdict: {res['verdict']:<10} (correct={res['correct']!s:<5}) | Expected: {expected_verdict:<10} | Passed: {passed}")
        print(f"     Feedback: {res.get('feedback')}")
    
    print("\nALL CASES PASSED:", all_passed)
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

