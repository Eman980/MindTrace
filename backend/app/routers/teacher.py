import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.all_models import User, Course
from app.schemas.all_schemas import CourseCreateIn, CourseUpdateIn, CourseOut
from app.utils.security import require_teacher

router = APIRouter(prefix="/teacher", tags=["Teacher Courses"])

def generate_unique_join_code(db: Session, max_attempts: int = 10) -> str:
    """
    Generate a collision-resistant, human-friendly joining code using Python's secrets module.
    Format: MIND-XXXXXX (6 alphanumeric chars, avoiding ambiguous glyphs like 0/O, 1/I).
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(max_attempts):
        suffix = "".join(secrets.choice(alphabet) for _ in range(6))
        code = f"MIND-{suffix}"
        if not db.query(Course).filter(Course.join_code == code).first():
            return code
    # Fallback with token_hex if collision loop exceeds max attempts
    return f"MIND-{secrets.token_hex(4).upper()}"

@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Create a new course owned by the authenticated teacher.
    Generates a unique, collision-resistant join code automatically.
    """
    join_code = generate_unique_join_code(db)
    course = Course(
        teacher_id=current_user.id,
        title=payload.title,
        course_code=payload.course_code,
        description=payload.description.strip() if payload.description else None,
        join_code=join_code
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.get("/courses", response_model=List[CourseOut])
def list_teacher_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    List all courses created by the authenticated teacher.
    Strictly isolated: Teachers only ever see their own courses.
    """
    courses = db.query(Course).filter(
        Course.teacher_id == current_user.id
    ).order_by(desc(Course.created_at)).all()
    return courses

@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course_detail(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Get detailed information for a specific course owned by the teacher.
    Rejects unauthorized access to other teachers' courses with HTTP 403.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this course."
        )
    return course

@router.patch("/courses/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    payload: CourseUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Update course title, course code, or description.
    Never allows altering teacher_id or join_code.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this course."
        )

    if payload.title is not None:
        course.title = payload.title
    if payload.course_code is not None:
        course.course_code = payload.course_code
    if payload.description is not None:
        course.description = payload.description.strip() if payload.description else None

    db.commit()
    db.refresh(course)
    return course

@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Delete a course owned by the authenticated teacher.
    Cannot delete another teacher's course.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this course."
        )

    db.delete(course)
    db.commit()
    return {"success": True, "message": f"Course '{course.title}' has been successfully deleted."}
