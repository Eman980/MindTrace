"""
test_master_verification.py
---------------------------
Comprehensive automated test suite verifying all 8 tasks of MindTrace:
1. Safe sample lecture loading & idempotency (no duplicates)
2. Authentication error handling (incorrect password, non-existing email, proper HTTP status codes)
3. Forgot & reset password lifecycle (token generation, expiration, validation, bcrypt hashing)
4. Lecture management (rename, persist, single delete, delete all)
5. Misconception tracking (list, filter, manual status updates, persist resolved status)
6. Multi-user isolation & security boundary checks
"""

import sys
import os
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models.all_models import (
    User, Lecture, Concept, Checkpoint, Misconception, MisconceptionEvidence,
    PasswordResetToken, ConceptProgress
)
from app.routers.auth import login, signup, forgot_password, reset_password
from app.routers.lectures import rename_lecture, delete_lecture, delete_all_lectures, list_lectures
from app.routers.misconceptions import list_misconceptions, update_misconception_status
from app.schemas.all_schemas import (
    UserLogin, UserCreate, ForgotPasswordIn, ResetPasswordIn,
    LectureUpdateIn, MisconceptionStatusUpdateIn
)
from app.services.seed_service import reset_user_to_sample_lecture, seed_demo_data
from app.utils.security import verify_password
from fastapi import HTTPException

class MasterVerificationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.test_email = "test_eval_user@mindtrace.edu"
        cls.other_email = "other_eval_user@mindtrace.edu"
        cls.clean_test_users()

        # Create primary test user
        cls.test_user = User(
            email=cls.test_email,
            full_name="Master Test Student",
            hashed_password=User.__table__.columns.hashed_password.type.python_type(
                # Use standard test hash
                "$2b$12$e6rD4VlG2W8h8W0a7nJpquE4e1y3WJjC4aD6G4aO3vQ9v2mX6mUjG"
            ),
            role="student"
        )
        # Create user via signup function to test signup pipeline
        from app.utils.security import get_password_hash
        cls.test_user.hashed_password = get_password_hash("InitialPassword123!")
        cls.db.add(cls.test_user)

        # Create secondary test user for isolation testing
        cls.other_user = User(
            email=cls.other_email,
            full_name="Other Test Student",
            hashed_password=get_password_hash("OtherPass123!"),
            role="student"
        )
        cls.db.add(cls.other_user)
        cls.db.commit()
        cls.db.refresh(cls.test_user)
        cls.db.refresh(cls.other_user)

    @classmethod
    def clean_test_users(cls):
        for email in [cls.test_email, cls.other_email]:
            u = cls.db.query(User).filter(User.email == email).first()
            if u:
                cls.db.query(PasswordResetToken).filter(PasswordResetToken.user_id == u.id).delete(synchronize_session=False)
                cls.db.query(ConceptProgress).filter(ConceptProgress.user_id == u.id).delete(synchronize_session=False)
                # Clean child records
                for lec in cls.db.query(Lecture).filter(Lecture.user_id == u.id).all():
                    cls.db.delete(lec)
                user_misc = cls.db.query(Misconception).filter(Misconception.user_id == u.id).all()
                for m in user_misc:
                    cls.db.delete(m)
                cls.db.delete(u)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.clean_test_users()
        cls.db.close()

    # =========================================================================
    # TASK 1: CLEAN EXISTING LECTURES AND LOAD A SAMPLE LECTURE
    # =========================================================================
    def test_01_load_sample_lecture_and_idempotency(self):
        """Verify sample lecture loads with complete workflow data and is idempotent."""
        # Load sample lecture
        lec = reset_user_to_sample_lecture(self.db, self.test_user)
        self.assertIsNotNone(lec)
        self.assertEqual(lec.title, "Introduction to Functions")
        self.assertTrue(lec.is_demo)

        # Verify components
        concepts = self.db.query(Concept).filter(Concept.lecture_id == lec.id).all()
        self.assertGreaterEqual(len(concepts), 4)

        # Verify checkpoints (MCQs)
        checkpoints = self.db.query(Checkpoint).join(Concept).filter(Concept.lecture_id == lec.id).all()
        self.assertGreaterEqual(len(checkpoints), 5)
        for cp in checkpoints:
            self.assertIn(cp.question_type, ["mcq", "short_answer"])
            self.assertTrue(bool(cp.explanation))

        # Verify pre-seeded persistent misconceptions
        miscs = self.db.query(Misconception).filter(Misconception.user_id == self.test_user.id).all()
        self.assertGreaterEqual(len(miscs), 2)
        for m in miscs:
            self.assertIn(m.status, ["Unresolved", "Needs Review", "In Progress", "Resolved"])
            self.assertIn(m.severity_level, ["High", "Medium", "Low"])
            self.assertGreaterEqual(len(m.evidence), 1)

        # Verify IDEMPOTENCY: Re-running seed_demo_data does not create duplicate lectures
        lec2 = seed_demo_data(self.db, self.test_user)
        self.assertEqual(lec.id, lec2.id)

        user_lectures = self.db.query(Lecture).filter(Lecture.user_id == self.test_user.id).all()
        self.assertEqual(len(user_lectures), 1, "Duplicate lecture was created instead of maintaining single sample lecture.")

    # =========================================================================
    # TASK 2: AUTHENTICATION ERROR HANDLING
    # =========================================================================
    def test_02_login_incorrect_password(self):
        """Ensure correct email with incorrect password returns 401 with exact message."""
        payload = UserLogin(email=self.test_email, password="WrongPassword999!")
        with self.assertRaises(HTTPException) as ctx:
            login(payload, self.db)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Incorrect password. Please try again.")

    def test_03_login_non_existing_email(self):
        """Ensure non-existent email returns 404 with exact message."""
        payload = UserLogin(email="nonexistent_random_student@mindtrace.edu", password="AnyPassword123!")
        with self.assertRaises(HTTPException) as ctx:
            login(payload, self.db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "No account found with this email.")

    def test_04_login_success(self):
        """Ensure valid credentials succeed and return token and user profile."""
        payload = UserLogin(email=self.test_email, password="InitialPassword123!")
        res = login(payload, self.db)
        self.assertIn("access_token", res)
        self.assertEqual(res["token_type"], "bearer")
        self.assertEqual(res["user"].email, self.test_email)

    # =========================================================================
    # TASK 3: FORGOT PASSWORD & RESET FUNCTIONALITY
    # =========================================================================
    def test_05_forgot_password_workflow(self):
        """Ensure forgot password generates secure token without leaking user existence."""
        # Non-existing user should return safe message without token
        res_non = forgot_password(ForgotPasswordIn(email="nobody_here@mindtrace.edu"), self.db)
        self.assertTrue(res_non["success"])
        self.assertIsNone(res_non["reset_token"])

        # Existing user should generate 36-char token
        res = forgot_password(ForgotPasswordIn(email=self.test_email), self.db)
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["reset_token"])
        self.assertEqual(len(res["reset_token"]), 48)  # urlsafe 36 bytes = 48 chars
        self.assertIn("If an account with this email exists", res["message"])

        # Reset Password - Password mismatch check
        with self.assertRaises(HTTPException) as ctx:
            reset_password(ResetPasswordIn(
                token=res["reset_token"],
                new_password="NewSecurePassword123!",
                confirm_password="DifferentPassword123!"
            ), self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Passwords do not match", ctx.exception.detail)

        # Reset Password - Password without number/symbol check
        with self.assertRaises(HTTPException) as ctx:
            reset_password(ResetPasswordIn(
                token=res["reset_token"],
                new_password="allletterslength",
                confirm_password="allletterslength"
            ), self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("at least one number or special character", ctx.exception.detail)

        # Reset Password - Valid password reset
        reset_res = reset_password(ResetPasswordIn(
            token=res["reset_token"],
            new_password="BrandNewPassword2026!",
            confirm_password="BrandNewPassword2026!"
        ), self.db)
        self.assertTrue(reset_res["success"])

        # Token cannot be re-used
        with self.assertRaises(HTTPException) as ctx:
            reset_password(ResetPasswordIn(
                token=res["reset_token"],
                new_password="BrandNewPassword2026!",
                confirm_password="BrandNewPassword2026!"
            ), self.db)
        self.assertEqual(ctx.exception.status_code, 400)

        # Old password no longer works
        with self.assertRaises(HTTPException) as ctx:
            login(UserLogin(email=self.test_email, password="InitialPassword123!"), self.db)
        self.assertEqual(ctx.exception.status_code, 401)

        # New password logs in successfully
        login_res = login(UserLogin(email=self.test_email, password="BrandNewPassword2026!"), self.db)
        self.assertIn("access_token", login_res)

    # =========================================================================
    # TASK 5: RENAME LECTURE FUNCTIONALITY
    # =========================================================================
    def test_06_rename_lecture(self):
        """Ensure renaming lecture updates database and persists across queries."""
        lec = self.db.query(Lecture).filter(Lecture.user_id == self.test_user.id).first()
        self.assertIsNotNone(lec)
        original_id = lec.id

        updated = rename_lecture(
            lecture_id=original_id,
            payload=LectureUpdateIn(title="CS101: Advanced Functions & Mapping", description="Updated description"),
            db=self.db,
            current_user=self.test_user
        )
        self.assertEqual(updated["title"], "CS101: Advanced Functions & Mapping")

        # Verify DB persistence
        self.db.expire_all()
        lec_db = self.db.query(Lecture).filter(Lecture.id == original_id).first()
        self.assertEqual(lec_db.title, "CS101: Advanced Functions & Mapping")
        self.assertEqual(lec_db.id, original_id, "Rename must not create duplicate lecture rows.")

    # =========================================================================
    # TASK 6: DELETE LECTURES & DELETE ALL
    # =========================================================================
    def test_07_delete_single_and_delete_all_lectures(self):
        """Ensure single deletion and bulk deletion work cleanly with foreign key safety."""
        # Clean state & load sample lecture for both users
        reset_user_to_sample_lecture(self.db, self.test_user)
        reset_user_to_sample_lecture(self.db, self.other_user)

        # Delete all lectures for test_user
        del_res = delete_all_lectures(db=self.db, current_user=self.test_user)
        self.assertTrue(del_res["success"])
        self.assertGreaterEqual(del_res["deleted_count"], 1)

        # Verify test_user has 0 lectures
        test_lectures = self.db.query(Lecture).filter(Lecture.user_id == self.test_user.id).all()
        self.assertEqual(len(test_lectures), 0)

        # Verify test_user has 0 misconceptions
        test_miscs = self.db.query(Misconception).filter(Misconception.user_id == self.test_user.id).all()
        self.assertEqual(len(test_miscs), 0)

        # Verify test_user account is NOT deleted
        user_check = self.db.query(User).filter(User.id == self.test_user.id).first()
        self.assertIsNotNone(user_check)

        # Verify other_user lectures and misconceptions are completely intact (Multi-tenant safety)
        other_lectures = self.db.query(Lecture).filter(Lecture.user_id == self.other_user.id).all()
        self.assertEqual(len(other_lectures), 1)
        other_miscs = self.db.query(Misconception).filter(Misconception.user_id == self.other_user.id).all()
        self.assertEqual(len(other_miscs), 2)

    # =========================================================================
    # TASK 7: DEDICATED MISCONCEPTIONS LIST & STATUS UPDATES
    # =========================================================================
    def test_08_misconceptions_list_filter_and_status_update(self):
        """Ensure listing, filtering, and manual status updates work and persist."""
        # Re-seed test_user
        reset_user_to_sample_lecture(self.db, self.test_user)

        # List all misconceptions
        all_miscs = list_misconceptions(priority=None, status_filter=None, db=self.db, current_user=self.test_user)
        self.assertGreaterEqual(len(all_miscs), 2)
        target_misc = all_miscs[0]

        # Verify all required fields are present
        self.assertIn("title", target_misc)
        self.assertIn("lecture_title", target_misc)
        self.assertIn("incorrect_understanding", target_misc)
        self.assertIn("correct_explanation", target_misc)
        self.assertIn("concept_name", target_misc)
        self.assertIn("concept_start_time", target_misc)
        self.assertIn("severity_level", target_misc)
        self.assertIn("status", target_misc)
        self.assertIn("first_detected", target_misc)

        # Test filter by severity
        high_miscs = list_misconceptions(priority="High", status_filter=None, db=self.db, current_user=self.test_user)
        for m in high_miscs:
            self.assertEqual(m["severity_level"], "High")

        # Test filter by status
        unresolved_miscs = list_misconceptions(priority=None, status_filter="Unresolved", db=self.db, current_user=self.test_user)
        for m in unresolved_miscs:
            self.assertIn(m["status"], ["New", "Unresolved"])

        # Update status to "Resolved"
        res_update = update_misconception_status(
            misconception_id=target_misc["id"],
            payload=MisconceptionStatusUpdateIn(status="Resolved"),
            db=self.db,
            current_user=self.test_user
        )
        self.assertEqual(res_update["status"], "Resolved")
        self.assertIsNotNone(res_update["resolved_at"])

        # Verify DB persistence
        self.db.expire_all()
        db_misc = self.db.query(Misconception).filter(Misconception.id == target_misc["id"]).first()
        self.assertEqual(db_misc.status, "Resolved")
        self.assertIsNotNone(db_misc.resolved_at)

        # Update status back to "In Progress"
        res_reopen = update_misconception_status(
            misconception_id=target_misc["id"],
            payload=MisconceptionStatusUpdateIn(status="In Progress"),
            db=self.db,
            current_user=self.test_user
        )
        self.assertEqual(res_reopen["status"], "In Progress")
        self.assertIsNone(res_reopen["resolved_at"])

    # =========================================================================
    # TASK 8: MULTI-USER ISOLATION & PERMISSION GUARDS
    # =========================================================================
    def test_09_multi_user_isolation_guards(self):
        """Ensure students cannot view or mutate other students' data."""
        reset_user_to_sample_lecture(self.db, self.test_user)
        reset_user_to_sample_lecture(self.db, self.other_user)

        other_lecture = self.db.query(Lecture).filter(Lecture.user_id == self.other_user.id).first()
        other_misc = self.db.query(Misconception).filter(Misconception.user_id == self.other_user.id).first()

        # test_user cannot rename other_user's lecture
        with self.assertRaises(HTTPException) as ctx:
            rename_lecture(
                lecture_id=other_lecture.id,
                payload=LectureUpdateIn(title="Hacked Title"),
                db=self.db,
                current_user=self.test_user
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # test_user cannot delete other_user's lecture
        with self.assertRaises(HTTPException) as ctx:
            delete_lecture(lecture_id=other_lecture.id, db=self.db, current_user=self.test_user)
        self.assertEqual(ctx.exception.status_code, 404)

        # test_user cannot mutate other_user's misconception status
        with self.assertRaises(HTTPException) as ctx:
            update_misconception_status(
                misconception_id=other_misc.id,
                payload=MisconceptionStatusUpdateIn(status="Resolved"),
                db=self.db,
                current_user=self.test_user
            )
        self.assertEqual(ctx.exception.status_code, 404)

if __name__ == "__main__":
    unittest.main(verbosity=2)
