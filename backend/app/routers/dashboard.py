from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.all_models import (
    User, Lecture, Concept, Misconception, ConceptProgress
)
from app.schemas.all_schemas import DashboardStatsOut
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    
    total_lectures = db.query(Lecture).filter(Lecture.user_id == user_id).count()
    
    concepts_count = (
        db.query(Concept)
        .join(Lecture)
        .filter(Lecture.user_id == user_id)
        .count()
    )
    
    all_misc = db.query(Misconception).filter(Misconception.user_id == user_id).all()
    total_misc = len(all_misc)
    high_p = sum(1 for m in all_misc if m.severity_level == "High" and m.status != "Resolved")
    med_p = sum(1 for m in all_misc if m.severity_level == "Medium" and m.status != "Resolved")
    low_p = sum(1 for m in all_misc if m.severity_level == "Low" and m.status != "Resolved")
    unres = sum(1 for m in all_misc if m.status in ["New", "Unresolved", "Needs Review"])
    improving = sum(1 for m in all_misc if m.status == "Improving")
    resolved = sum(1 for m in all_misc if m.status == "Resolved")
    
    # Recent Lectures
    recent_lectures_db = (
        db.query(Lecture)
        .filter(Lecture.user_id == user_id)
        .order_by(desc(Lecture.created_at))
        .limit(6)
        .all()
    )
    
    recent_lectures = []
    for lec in recent_lectures_db:
        c_count = len(lec.concepts)
        unresolved_c = db.query(Misconception).filter(
            Misconception.lecture_id == lec.id,
            Misconception.user_id == user_id,
            Misconception.status.in_(["Unresolved", "Needs Review", "New"])
        ).count()
        
        progress_records = db.query(ConceptProgress).join(Concept).filter(
            Concept.lecture_id == lec.id,
            ConceptProgress.user_id == user_id
        ).all()
        avg_progress = int(sum(p.understanding_percentage for p in progress_records) / len(progress_records)) if progress_records else 0

        recent_lectures.append({
            "id": lec.id,
            "title": lec.title,
            "course_code": lec.course_code,
            "description": lec.description,
            "duration_seconds": lec.duration_seconds,
            "media_type": lec.media_type,
            "status": lec.status,
            "is_demo": lec.is_demo,
            "created_at": lec.created_at,
            "concepts_count": c_count,
            "unresolved_count": unresolved_c,
            "progress_percentage": avg_progress,
            "media_url": f"{settings.API_V1_PREFIX}/lectures/{lec.id}/media"
        })

    return {
        "total_lectures": total_lectures,
        "concepts_identified": concepts_count,
        "misconceptions_detected": total_misc,
        "unresolved_concepts": unres,
        "concepts_improved": improving + resolved,
        "recent_lectures": recent_lectures,
        "misconception_summary": {
            "total_detected": total_misc,
            "high_priority": high_p,
            "medium_priority": med_p,
            "low_priority": low_p,
            "unresolved": unres,
            "improving": improving,
            "resolved": resolved
        }
    }
