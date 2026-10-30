import io
import csv
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.config import settings
from app.models.all_models import (
    Misconception, MisconceptionEvidence, User, Checkpoint, CheckpointAttempt, Lecture, Concept
)
from app.schemas.all_schemas import (
    MisconceptionOut,
    MisconceptionReviewOut,
    MisconceptionResolveIn,
    MisconceptionStatsOut,
    ReprobeItemOut,
    MisconceptionLedgerItemOut,
    LedgerAttemptOut,
    CheckpointOut,
)
from app.services.misconception_service import misconception_service
from app.services.evaluation_service import evaluation_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/misconceptions", tags=["Misconceptions"])


def _calculate_hours_since(dt: Optional[datetime]) -> float:
    """Safely calculate hours elapsed since a given datetime, handling tz-naive and tz-aware."""
    if not dt:
        return 0.0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elapsed_seconds = max(0.0, (now - dt).total_seconds())
    return round(elapsed_seconds / 3600.0, 2)


@router.get("", response_model=List[MisconceptionOut])
def list_misconceptions(
    priority: Optional[str] = Query(None),       # High, Medium, Low
    status_filter: Optional[str] = Query(None),  # Unresolved, Improving, Resolved
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Misconception).filter(Misconception.user_id == current_user.id)
    
    if priority and priority != "All":
        query = query.filter(Misconception.severity_level == priority.capitalize())
        
    if status_filter and status_filter != "All":
        if status_filter.lower() == "unresolved":
            query = query.filter(Misconception.status.in_(["New", "Unresolved"]))
        else:
            query = query.filter(Misconception.status == status_filter.capitalize())
            
    misconceptions = query.order_by(desc(Misconception.severity_score), desc(Misconception.last_detected)).all()
    
    results = []
    for m in misconceptions:
        lec = db.query(Lecture).filter(Lecture.id == m.lecture_id).first()
        results.append({
            "id": m.id,
            "user_id": m.user_id,
            "lecture_id": m.lecture_id,
            "lecture_title": lec.title if lec else "Lecture",
            "concept_id": m.concept_id,
            "concept_name": m.concept_name,
            "title": m.title,
            "summary": m.summary,
            "severity_score": m.severity_score,
            "severity_level": m.severity_level,
            "occurrence_count": m.occurrence_count,
            "status": m.status,
            "first_detected": m.first_detected,
            "last_detected": m.last_detected,
            "evidence_status": m.evidence_status,
            "memorized_flag": m.memorized_flag or False,
            "recurrence_count": m.recurrence_count or 0,
            "remediation_segment_id": m.remediation_segment_id,
            "resolved_at": m.resolved_at,
            "evidence": [
                {
                    "id": e.id,
                    "signal_type": e.signal_type,
                    "evidence_text": e.evidence_text,
                    "points_added": e.points_added,
                    "created_at": e.created_at
                }
                for e in m.evidence
            ]
        })
    return results


@router.get("/stats", response_model=MisconceptionStatsOut)
def get_misconception_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    all_misc = db.query(Misconception).filter(Misconception.user_id == current_user.id).all()
    
    total = len(all_misc)
    high = sum(1 for m in all_misc if m.severity_level == "High" and m.status != "Resolved")
    med = sum(1 for m in all_misc if m.severity_level == "Medium" and m.status != "Resolved")
    low = sum(1 for m in all_misc if m.severity_level == "Low" and m.status != "Resolved")
    unres = sum(1 for m in all_misc if m.status in ["New", "Unresolved"])
    imp = sum(1 for m in all_misc if m.status == "Improving")
    res = sum(1 for m in all_misc if m.status == "Resolved")
    
    return {
        "total_detected": total,
        "high_priority": high,
        "medium_priority": med,
        "low_priority": low,
        "unresolved": unres,
        "improving": imp,
        "resolved": res
    }


@router.get("/reprobe", response_model=List[ReprobeItemOut])
def get_reprobe_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns items due for spaced reassessment/re-probing.
    Evaluates delay thresholds against configured MIN_DELAY_HOURS or DEMO_DELAY_HOURS.
    """
    # Active misconceptions that are not resolved, or were marked Memorized / Recurred
    misconceptions = db.query(Misconception).filter(
        Misconception.user_id == current_user.id,
        Misconception.status != "Resolved"
    ).order_by(desc(Misconception.severity_score)).all()

    delay_required = settings.effective_delay_hours
    results = []

    for m in misconceptions:
        last_seen = m.last_detected or m.created_at
        hours_elapsed = _calculate_hours_since(last_seen)

        # Due if enough time elapsed or in demo mode / suspected state
        is_due = hours_elapsed >= delay_required or settings.USE_DEMO_DELAY

        # Find best checkpoint for re-probing this concept
        checkpoints = db.query(Checkpoint).filter(
            Checkpoint.concept_id == m.concept_id
        ).order_by(desc(Checkpoint.is_review_checkpoint), Checkpoint.order_index).all()

        reprobe_chk = None
        if checkpoints:
            chosen = checkpoints[0]
            reprobe_chk = {
                "id": chosen.id,
                "concept_id": chosen.concept_id,
                "question_type": chosen.question_type,
                "question_text": chosen.question_text,
                "options": chosen.options,
                "explanation": chosen.explanation,
                "order_index": chosen.order_index,
                "is_review_checkpoint": chosen.is_review_checkpoint,
            }

        lec = db.query(Lecture).filter(Lecture.id == m.lecture_id).first()

        results.append({
            "misconception_id": m.id,
            "concept_id": m.concept_id,
            "concept_name": m.concept_name,
            "lecture_id": m.lecture_id,
            "lecture_title": lec.title if lec else "Lecture",
            "title": m.title,
            "evidence_status": m.evidence_status or ("Confirmed" if m.severity_score >= 4 else "Suspected"),
            "severity_level": m.severity_level,
            "severity_score": m.severity_score,
            "last_detected": last_seen,
            "hours_since_last_seen": hours_elapsed,
            "required_delay_hours": delay_required,
            "is_due": is_due,
            "reprobe_checkpoint": reprobe_chk,
        })

    return results


@router.get("/ledger", response_model=List[MisconceptionLedgerItemOut])
def get_misconception_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the comprehensive misconception ledger for the student,
    including evidence chain, explanation checks, and video remediation anchors.
    """
    misconceptions = db.query(Misconception).filter(
        Misconception.user_id == current_user.id
    ).order_by(desc(Misconception.last_detected)).all()

    results = []
    for m in misconceptions:
        lec = db.query(Lecture).filter(Lecture.id == m.lecture_id).first()
        concept = db.query(Concept).filter(Concept.id == m.concept_id).first()

        # Find all checkpoint attempts by this user for checkpoints in this concept
        concept_checkpoint_ids = [c.id for c in (concept.checkpoints if concept else [])]
        attempts = []
        if concept_checkpoint_ids:
            raw_attempts = db.query(CheckpointAttempt).filter(
                CheckpointAttempt.user_id == current_user.id,
                CheckpointAttempt.checkpoint_id.in_(concept_checkpoint_ids)
            ).order_by(desc(CheckpointAttempt.created_at)).all()

            for a in raw_attempts:
                attempts.append({
                    "id": a.id,
                    "checkpoint_id": a.checkpoint_id,
                    "is_correct": a.is_correct,
                    "confidence_level": a.confidence_level,
                    "explanation_text": a.explanation_text,
                    "explanation_verdict": a.explanation_verdict,
                    "created_at": a.created_at,
                })

        results.append({
            "id": m.id,
            "user_id": m.user_id,
            "lecture_id": m.lecture_id,
            "lecture_title": lec.title if lec else "Lecture",
            "concept_id": m.concept_id,
            "concept_name": m.concept_name,
            "title": m.title,
            "summary": m.summary,
            "severity_score": m.severity_score,
            "severity_level": m.severity_level,
            "occurrence_count": m.occurrence_count,
            "status": m.status,
            "first_detected": m.first_detected,
            "last_detected": m.last_detected,
            "evidence_status": m.evidence_status or ("Confirmed" if m.severity_score >= 4 else "Suspected"),
            "memorized_flag": m.memorized_flag or False,
            "recurrence_count": m.recurrence_count or 0,
            "remediation_segment_id": m.remediation_segment_id or (concept.id if concept else None),
            "remediation_start_time": concept.start_time if concept else None,
            "remediation_end_time": concept.end_time if concept else None,
            "resolved_at": m.resolved_at,
            "attempts": attempts,
            "evidence": [
                {
                    "id": e.id,
                    "signal_type": e.signal_type,
                    "evidence_text": e.evidence_text,
                    "points_added": e.points_added,
                    "created_at": e.created_at
                }
                for e in m.evidence
            ]
        })

    return results


@router.get("/export-evidence")
def export_evidence_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exports all misconception evidence as a downloadable CSV for evaluation experiments (E3/E4).
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "evidence_id",
        "misconception_id",
        "user_id",
        "lecture_title",
        "concept_name",
        "misconception_title",
        "evidence_status",
        "severity_level",
        "severity_score",
        "signal_type",
        "evidence_text",
        "points_added",
        "created_at"
    ])

    misconceptions = db.query(Misconception).filter(
        Misconception.user_id == current_user.id
    ).all()

    for m in misconceptions:
        lec = db.query(Lecture).filter(Lecture.id == m.lecture_id).first()
        lec_title = lec.title if lec else "Unknown Lecture"
        status_val = m.evidence_status or m.status

        for e in m.evidence:
            writer.writerow([
                e.id,
                m.id,
                m.user_id,
                lec_title,
                m.concept_name,
                m.title,
                status_val,
                m.severity_level,
                m.severity_score,
                e.signal_type,
                e.evidence_text,
                e.points_added,
                e.created_at.isoformat() if e.created_at else ""
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mindtrace_evidence_log.csv"}
    )


@router.get("/{misconception_id}/review", response_model=MisconceptionReviewOut)
def get_misconception_review(
    misconception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    review_data = misconception_service.get_review_data(db, current_user.id, misconception_id)
    if not review_data:
        raise HTTPException(status_code=404, detail="Misconception not found.")
        
    m = review_data["misconception"]
    lec = db.query(Lecture).filter(Lecture.id == m.lecture_id).first()
    
    misc_out = {
        "id": m.id,
        "user_id": m.user_id,
        "lecture_id": m.lecture_id,
        "lecture_title": lec.title if lec else "Lecture",
        "concept_id": m.concept_id,
        "concept_name": m.concept_name,
        "title": m.title,
        "summary": m.summary,
        "severity_score": m.severity_score,
        "severity_level": m.severity_level,
        "occurrence_count": m.occurrence_count,
        "status": m.status,
        "first_detected": m.first_detected,
        "last_detected": m.last_detected,
        "evidence_status": m.evidence_status,
        "memorized_flag": m.memorized_flag or False,
        "recurrence_count": m.recurrence_count or 0,
        "remediation_segment_id": m.remediation_segment_id,
        "resolved_at": m.resolved_at,
        "evidence": [
            {
                "id": e.id,
                "signal_type": e.signal_type,
                "evidence_text": e.evidence_text,
                "points_added": e.points_added,
                "created_at": e.created_at
            }
            for e in m.evidence
        ]
    }
    
    chk_out = None
    if review_data["review_checkpoint"]:
        rc = review_data["review_checkpoint"]
        chk_out = {
            "id": rc.id,
            "concept_id": rc.concept_id,
            "question_type": rc.question_type,
            "question_text": rc.question_text,
            "options": rc.options,
            "explanation": rc.explanation,
            "order_index": rc.order_index,
            "is_review_checkpoint": rc.is_review_checkpoint
        }
        
    return {
        "misconception": misc_out,
        "concept_title": review_data["concept_title"],
        "concept_start_time": review_data["concept_start_time"],
        "concept_end_time": review_data["concept_end_time"],
        "transcript_snippet": review_data["transcript_snippet"],
        "previous_bad_answer": review_data["previous_bad_answer"],
        "why_problematic": review_data["why_problematic"],
        "clarification_explanation": review_data["clarification_explanation"],
        "review_checkpoint": chk_out
    }


@router.post("/{misconception_id}/resolve")
async def resolve_misconception(
    misconception_id: int,
    resolve_in: MisconceptionResolveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits answer to the targeted review checkpoint.
    If answered accurately, updates status: High Priority -> Improving -> Resolved!
    """
    checkpoint = db.query(Checkpoint).filter(Checkpoint.id == resolve_in.checkpoint_id).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Review checkpoint not found.")
        
    eval_result = await evaluation_service.evaluate_answer(
        question_type=checkpoint.question_type,
        question_text=checkpoint.question_text,
        correct_answer=checkpoint.correct_answer,
        student_answer=resolve_in.student_answer,
        explanation=checkpoint.explanation
    )
    
    updated_misc = misconception_service.resolve_misconception_checkpoint(
        db=db,
        user_id=current_user.id,
        misconception_id=misconception_id,
        is_correct=eval_result["correct"]
    )
    
    return {
        "is_correct": eval_result["correct"],
        "feedback_reason": eval_result.get("reason", ""),
        "new_status": updated_misc.status if updated_misc else "Unknown",
        "new_severity_level": updated_misc.severity_level if updated_misc else "Low",
        "new_severity_score": updated_misc.severity_score if updated_misc else 0,
        "message": "Misconception updated based on review performance."
    }
