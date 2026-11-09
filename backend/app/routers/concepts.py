from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import Concept, ConceptProgress, User, Lecture
from app.schemas.all_schemas import ConceptDetailOut, ConceptOut
from app.utils.security import get_current_user

router = APIRouter(prefix="/concepts", tags=["Concepts"])

@router.get("/progress", response_model=List[ConceptOut])
def get_all_concepts_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns progress across all concepts the student has studied.
    """
    concepts = (
        db.query(Concept)
        .join(Lecture)
        .filter(Lecture.user_id == current_user.id)
        .order_by(Concept.lecture_id, Concept.order_index)
        .all()
    )
    
    results = []
    for c in concepts:
        prog = db.query(ConceptProgress).filter(
            ConceptProgress.concept_id == c.id,
            ConceptProgress.user_id == current_user.id
        ).first()
        
        results.append({
            "id": c.id,
            "lecture_id": c.lecture_id,
            "title": c.title,
            "description": c.description,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "order_index": c.order_index,
            "confidence_score": c.confidence_score,
            "checkpoints_count": len([chk for chk in c.checkpoints if not chk.is_review_checkpoint]),
            "replay_count": prog.replay_count if prog else 0,
            "understanding_percentage": prog.understanding_percentage if prog else 0,
            "status": prog.status if prog else "Not Started"
        })
    return results

@router.get("/{concept_id}", response_model=ConceptDetailOut)
def get_concept_detail(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    concept = (
        db.query(Concept)
        .join(Lecture)
        .filter(Concept.id == concept_id, Lecture.user_id == current_user.id)
        .first()
    )
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found.")
        
    prog = db.query(ConceptProgress).filter(
        ConceptProgress.concept_id == concept.id,
        ConceptProgress.user_id == current_user.id
    ).first()
    
    checkpoints_out = []
    for chk in concept.checkpoints:
        if not chk.is_review_checkpoint:
            checkpoints_out.append({
                "id": chk.id,
                "concept_id": chk.concept_id,
                "question_type": chk.question_type,
                "question_text": chk.question_text,
                "options": chk.options,
                "explanation": chk.explanation,
                "order_index": chk.order_index,
                "is_review_checkpoint": chk.is_review_checkpoint
            })

    return {
        "id": concept.id,
        "lecture_id": concept.lecture_id,
        "title": concept.title,
        "description": concept.description,
        "start_time": concept.start_time,
        "end_time": concept.end_time,
        "order_index": concept.order_index,
        "confidence_score": concept.confidence_score,
        "transcript_text": concept.transcript_text,
        "checkpoints_count": len(checkpoints_out),
        "checkpoints": checkpoints_out,
        "replay_count": prog.replay_count if prog else 0,
        "understanding_percentage": prog.understanding_percentage if prog else 0,
        "status": prog.status if prog else "Not Started"
    }
