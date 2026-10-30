from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User
from app.schemas.all_schemas import PlaybackEventIn, UnresolvedMarkIn
from app.services.misconception_service import misconception_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/playback", tags=["Playback Tracking"])

@router.post("/event")
def record_event(
    event_in: PlaybackEventIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tracks video/audio player behavior.
    Automatically detects if replay threshold (>= 3) is exceeded and registers Signal 2 (Behavioural).
    """
    result = misconception_service.record_playback_event(
        db=db,
        user_id=current_user.id,
        lecture_id=event_in.lecture_id,
        concept_id=event_in.concept_id,
        event_type=event_in.event_type,
        timestamp_in_media=event_in.timestamp_in_media,
        details=event_in.details
    )
    return result

@router.post("/unresolved")
def mark_unresolved(
    unres_in: UnresolvedMarkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Handles student explicitly clicking 'Mark as Unresolved' on any concept segment.
    Stores explicit evidence with user's optional statement of confusion.
    """
    misc = misconception_service.mark_concept_unresolved(
        db=db,
        user_id=current_user.id,
        lecture_id=unres_in.lecture_id,
        concept_id=unres_in.concept_id,
        timestamp_in_media=unres_in.timestamp_in_media,
        reason=unres_in.reason
    )
    return {
        "success": True,
        "message": f"Concept marked as unresolved. Misconception priority: {misc.severity_level}",
        "misconception_id": misc.id,
        "severity_level": misc.severity_level,
        "severity_score": misc.severity_score
    }
