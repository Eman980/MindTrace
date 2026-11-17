"""
Course Association Service (Teacher Insights Phase 3 & Security Remediation)

Enforces strict privacy and course boundaries via explicit Course ForeignKeys:
- A lecture is associated with a teacher's course ONLY when:
  1. The lecture explicitly references the course via `lecture.course_id == course_id`.
  2. The student has an active, consented enrollment in that course (`consent_granted=True`, `status='active'`).
  3. The course belongs to the requesting teacher (`course.teacher_id == teacher_id`).
- Independent Study lectures (`lecture.course_id is None`) remain 100% private to the student.
- Course code is NEVER used as sufficient proof of course membership.
- If consent is revoked/withdrawn, teacher access immediately cuts off.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.all_models import Course, CourseEnrollment, Lecture, User


def normalize_course_code(code: Optional[str]) -> Optional[str]:
    """
    Normalizes course codes by trimming whitespace and converting to uppercase.
    Empty or whitespace-only strings return None.
    """
    if code is None:
        return None
    cleaned = code.strip().upper()
    return cleaned if cleaned else None


def get_student_active_enrollment(
    db: Session, student_id: int, course_id: int
) -> Optional[CourseEnrollment]:
    """
    Retrieves the active, consented enrollment for a student in a course, if any.
    Returns None if enrollment does not exist, status != 'active', or consent_granted is False.
    """
    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
            CourseEnrollment.consent_granted.is_(True),
            CourseEnrollment.status == "active",
        )
        .first()
    )


def get_student_course_associated_lectures(
    db: Session, student_id: int, course_id: int
) -> List[Lecture]:
    """
    Retrieves all lectures belonging to a student that are explicitly associated with
    the given course (lecture.course_id == course_id), provided the student has an
    active, consented enrollment.

    If enrollment is not active, consent is not granted, or course does not exist,
    returns an empty list. Never falls back to loose string matching.
    """
    enrollment = get_student_active_enrollment(db, student_id=student_id, course_id=course_id)
    if not enrollment:
        return []

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return []

    # Query only lectures explicitly associated with this course_id
    lectures = (
        db.query(Lecture)
        .filter(
            Lecture.user_id == student_id,
            Lecture.course_id == course_id,
        )
        .all()
    )
    return lectures


def count_student_course_associated_lectures(
    db: Session, student_id: int, course_id: int
) -> int:
    """
    Counts how many lectures of a student are currently explicitly associated with the course.
    """
    return len(get_student_course_associated_lectures(db, student_id=student_id, course_id=course_id))


def get_teacher_course_associated_activity(
    db: Session, teacher_id: int, course_id: int
) -> List[Lecture]:
    """
    Retrieves all student lectures explicitly associated with a teacher's course
    (lecture.course_id == course_id) across all actively enrolled, consenting students.

    Verifies:
    1. The course belongs to the requesting teacher.
    2. Enrolled students have consent_granted=True and status='active'.
    3. Lectures explicitly reference this course_id.
    """
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not course:
        return []

    active_enrollments = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.consent_granted.is_(True),
            CourseEnrollment.status == "active",
        )
        .all()
    )
    if not active_enrollments:
        return []

    student_ids = [e.student_id for e in active_enrollments]

    lectures = (
        db.query(Lecture)
        .filter(
            Lecture.course_id == course_id,
            Lecture.user_id.in_(student_ids),
        )
        .all()
    )

    return lectures
