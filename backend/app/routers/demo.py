from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User
from app.services.seed_service import seed_demo_data
from app.utils.security import get_current_user

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

@router.post("/seed")
def seed_demo_lecture(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Seeds the standard 'Introduction to Functions' lecture into the active user's account.
    """
    lecture = seed_demo_data(db, current_user)
    return {
        "success": True,
        "message": "Demo lecture 'Introduction to Functions' seeded successfully with concepts, timeline, checkpoints, and misconceptions.",
        "lecture_id": lecture.id,
        "title": lecture.title
    }
