from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.all_models import User, Course, CourseEnrollment, Lecture, utcnow
from app.schemas.all_schemas import (
    CoursePreviewIn,
    CoursePreviewOut,
    CourseJoinIn,
    StudentEnrollmentOut,
)
from app.utils.security import require_student
from app.services.course_association_service import (
    count_student_course_associated_lectures,
    get_student_course_associated_lectures,
)

router = APIRouter(prefix="/student", tags=["Student Courses"])


@router.post("/courses/preview", response_model=CoursePreviewOut)
def preview_course(
    payload: CoursePreviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    Validate a teacher-generated join code and preview course details before joining.
    Shows course title, code, instructor name, and existing enrollment status.
    """
    course = db.query(Course).filter(Course.join_code == payload.join_code).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found. Please check the joining code and try again.",
        )

    teacher = db.query(User).filter(User.id == course.teacher_id).first()
    teacher_name = teacher.full_name if teacher else "Instructor"

    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == current_user.id,
        )
        .first()
    )

    already_enrolled = (
        enrollment is not None
        and enrollment.status == "active"
        and enrollment.consent_granted is True
    )

    return CoursePreviewOut(
        course_id=course.id,
        title=course.title,
        course_code=course.course_code,
        description=course.description,
        teacher_name=teacher_name,
        already_enrolled=already_enrolled,
        enrollment_status=enrollment.status if enrollment else None,
    )


@router.post("/courses/join", response_model=StudentEnrollmentOut, status_code=status.HTTP_201_CREATED)
def join_course(
    payload: CourseJoinIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    Join a course using the join code and grant one-time consent to share course-relevant learning activity.
    Re-activates revoked enrollments or creates a new enrollment.
    """
    if not payload.consent_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required to join the course and share learning insights.",
        )

    course = db.query(Course).filter(Course.join_code == payload.join_code).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found. Please check the joining code and try again.",
        )

    teacher = db.query(User).filter(User.id == course.teacher_id).first()
    teacher_name = teacher.full_name if teacher else "Instructor"

    existing_enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == current_user.id,
        )
        .first()
    )

    if existing_enrollment:
        if existing_enrollment.status == "active" and existing_enrollment.consent_granted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already enrolled in this course.",
            )
        # Reactivate previously revoked enrollment
        existing_enrollment.consent_granted = True
        existing_enrollment.status = "active"
        existing_enrollment.consent_at = utcnow()
        existing_enrollment.updated_at = utcnow()
        db.commit()
        db.refresh(existing_enrollment)
        enrollment = existing_enrollment
    else:
        now = utcnow()
        enrollment = CourseEnrollment(
            course_id=course.id,
            student_id=current_user.id,
            consent_granted=True,
            status="active",
            consent_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)

    associated_count = count_student_course_associated_lectures(
        db, student_id=current_user.id, course_id=course.id
    )

    return StudentEnrollmentOut(
        id=enrollment.id,
        course_id=course.id,
        title=course.title,
        course_code=course.course_code,
        description=course.description,
        teacher_name=teacher_name,
        consent_granted=enrollment.consent_granted,
        status=enrollment.status,
        consent_at=enrollment.consent_at,
        created_at=enrollment.created_at,
        associated_lectures_count=associated_count,
    )


@router.get("/courses", response_model=List[StudentEnrollmentOut])
def list_student_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    List all courses the student is enrolled in with enrollment status, consent details,
    and associated lectures count.
    """
    enrollments = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.student_id == current_user.id)
        .order_by(desc(CourseEnrollment.created_at))
        .all()
    )

    result = []
    for enr in enrollments:
        course = db.query(Course).filter(Course.id == enr.course_id).first()
        if not course:
            continue
        teacher = db.query(User).filter(User.id == course.teacher_id).first()
        teacher_name = teacher.full_name if teacher else "Instructor"

        assoc_count = count_student_course_associated_lectures(
            db, student_id=current_user.id, course_id=course.id
        ) if enr.status == "active" and enr.consent_granted else 0

        result.append(
            StudentEnrollmentOut(
                id=enr.id,
                course_id=course.id,
                title=course.title,
                course_code=course.course_code,
                description=course.description,
                teacher_name=teacher_name,
                consent_granted=enr.consent_granted,
                status=enr.status,
                consent_at=enr.consent_at,
                created_at=enr.created_at,
                associated_lectures_count=assoc_count,
            )
        )

    return result


@router.post("/courses/{course_id}/withdraw")
def withdraw_course_consent(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    Disconnect from a course and revoke consent.
    Immediately stops associating any learning activity with the teacher's course,
    while leaving the student's personal learning data (lectures, misconceptions) untouched.
    """
    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == current_user.id,
        )
        .first()
    )

    if not enrollment or enrollment.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active enrollment found for this course.",
        )

    enrollment.consent_granted = False
    enrollment.status = "revoked"
    enrollment.updated_at = utcnow()
    db.commit()

    return {
        "message": "Successfully disconnected from course and revoked consent.",
        "course_id": course_id,
        "status": "revoked",
    }


@router.get("/courses/{course_id}/associated-lectures")
def get_course_associated_lectures(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    Returns the list of the student's lectures that are currently associated with this course.
    Transparently informs the student which learning materials share insights with the instructor.
    """
    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == current_user.id,
            CourseEnrollment.status == "active",
            CourseEnrollment.consent_granted.is_(True),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active enrollment with consent not found.",
        )

    lectures = get_student_course_associated_lectures(
        db, student_id=current_user.id, course_id=course_id
    )

    return [
        {
            "id": lec.id,
            "title": lec.title,
            "course_code": lec.course_code,
            "created_at": lec.created_at,
        }
        for lec in lectures
    ]
