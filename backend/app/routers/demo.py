from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User
from app.services.seed_service import seed_demo_data, reset_user_to_sample_lecture
from app.utils.security import get_current_user

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

@router.post("/seed")
def seed_demo_lecture(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Seeds the standard 'Introduction to Functions' lecture into the active user's account
    if not already present. Idempotent.
    """
    lecture = seed_demo_data(db, current_user)
    return {
        "success": True,
        "message": "Sample lecture 'Introduction to Functions' loaded successfully.",
        "lecture_id": lecture.id,
        "title": lecture.title
    }

@router.post("/reset-sample")
def reset_sample_lecture(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Cleans all existing lecture/test data for the current user and loads
    one fresh, properly structured sample lecture with complete concepts,
    checkpoints, transcript segments, and pre-detected misconceptions.
    """
    lecture = reset_user_to_sample_lecture(db, current_user)
    return {
        "success": True,
        "message": "All existing test lectures cleaned and fresh sample lecture loaded successfully.",
        "lecture_id": lecture.id,
        "title": lecture.title
    }
