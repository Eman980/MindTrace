import sys
import os
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.main import app
from app.database import get_db, Base, engine, SessionLocal
from app.models.all_models import User, Lecture, Concept, Checkpoint, CheckpointAttempt, Misconception
from app.utils.security import create_access_token

class TestShortAnswerEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Create or fetch test user
        user = cls.db.query(User).filter(User.email == "short_eval_test@mindtrace.edu").first()
        if not user:
            user = User(
                email="short_eval_test@mindtrace.edu",
                hashed_password="hashed_pw_test",
                full_name="Short Eval Tester"
            )
            cls.db.add(user)
            cls.db.commit()
            cls.db.refresh(user)
        cls.user = user
        cls.token = create_access_token(data={"sub": str(user.id), "email": user.email})
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Create test lecture
        lecture = cls.db.query(Lecture).filter(Lecture.title == "Test Web Tech Lecture", Lecture.user_id == user.id).first()
        if not lecture:
            lecture = Lecture(
                user_id=user.id,
                title="Test Web Tech Lecture",
                course_code="CS101",
                description="Intro to web technologies",
                media_type="audio",
                status="completed"
            )
            cls.db.add(lecture)
            cls.db.commit()
            cls.db.refresh(lecture)
        cls.lecture = lecture

        # Create test concept
        concept = cls.db.query(Concept).filter(Concept.title == "HTML Fundamentals", Concept.lecture_id == lecture.id).first()
        if not concept:
            concept = Concept(
                lecture_id=lecture.id,
                title="HTML Fundamentals",
                description="Core markup structure of web documents.",
                start_time=10.0,
                end_time=60.0,
                order_index=1
            )
            cls.db.add(concept)
            cls.db.commit()
            cls.db.refresh(concept)
        cls.concept = concept

        # Create test short-answer checkpoint
        checkpoint = cls.db.query(Checkpoint).filter(
            Checkpoint.concept_id == concept.id,
            Checkpoint.question_type == "short_answer"
        ).first()
        if not checkpoint:
            checkpoint = Checkpoint(
                concept_id=concept.id,
                question_type="short_answer",
                difficulty="easy",
                question_text="What is HTML?",
                options=[],
                correct_answer="HTML is the standard markup language used for structuring web pages.",
                explanation="HTML defines the core structural elements and layout of web pages.",
                order_index=1,
                is_review_checkpoint=False,
                target_misconception="Conflating HTML structure with CSS styling"
            )
            cls.db.add(checkpoint)
            cls.db.commit()
            cls.db.refresh(checkpoint)
        cls.checkpoint = checkpoint

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_all_evaluation_cases(self):
        cases = [
            # (student_answer, expected_verdict, expected_correct, expected_points)
            ("Hi", "incorrect", False, 0),
            ("Hello", "incorrect", False, 0),
            ("Okay", "incorrect", False, 0),
            ("Thanks", "incorrect", False, 0),
            ("I don't know", "unanswered", False, 0),
            ("idk", "unanswered", False, 0),
            ("", "unanswered", False, 0),
            ("   ", "unanswered", False, 0),
            ("asdfghjkl", "incorrect", False, 0),
            ("u", "incorrect", False, 0),
            ("xyz", "incorrect", False, 0),
            ("HTML is a markup language used to structure web pages.", "correct", True, 10),
            ("HTML is used to create websites.", "partial", False, 0),
            ("CSS is used to style web pages.", "incorrect", False, 0),
            ("HTML is the standard markup language for creating the structural foundation of web pages.", "correct", True, 10),
        ]

        print("\n=======================================================")
        print("  END-TO-END /api/v1/checkpoints/answer VERIFICATION")
        print("=======================================================")

        for ans, exp_verdict, exp_correct, exp_points in cases:
            resp = self.client.post(
                "/api/v1/checkpoints/answer",
                headers=self.headers,
                json={
                    "checkpoint_id": self.checkpoint.id,
                    "student_answer": ans
                }
            )
            self.assertEqual(resp.status_code, 200, f"HTTP failure for answer: {ans!r}")
            data = resp.json()

            actual_verdict = data.get("verdict")
            actual_correct = data.get("is_correct")
            actual_points = data.get("points_awarded")
            actual_feedback = data.get("feedback")
            explanation_verdict = data.get("explanation_verdict")

            print(f"Input: {ans!r:<58} -> Verdict: {actual_verdict:<10} | Correct: {actual_correct!s:<5} | Pts: {actual_points} | LLM Verdict: {explanation_verdict}")
            print(f"       Feedback: {actual_feedback}")

            self.assertEqual(actual_verdict, exp_verdict, f"Verdict mismatch for {ans!r}: got {actual_verdict}, expected {exp_verdict}")
            self.assertEqual(actual_correct, exp_correct, f"is_correct mismatch for {ans!r}: got {actual_correct}, expected {exp_correct}")
            self.assertEqual(actual_points, exp_points, f"points_awarded mismatch for {ans!r}: got {actual_points}, expected {exp_points}")
            self.assertEqual(explanation_verdict, exp_verdict, f"explanation_verdict mismatch for {ans!r}")

        print("=======================================================")
        print("  ALL END-TO-END CHECKPOINT ANSWER TESTS PASSED!")
        print("=======================================================\n")

if __name__ == "__main__":
    unittest.main()
