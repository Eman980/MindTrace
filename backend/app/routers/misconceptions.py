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
    MisconceptionStatusUpdateIn,
    MisconceptionDetailOut,
    MisconceptionAttemptHistoryItem,
)
from app.services.misconception_service import misconception_service
from app.services.evaluation_service import evaluation_service
from app.services.prerequisite_link_service import find_root_causes_for_misconceptions
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
async def list_misconceptions(
    priority: Optional[str] = Query(None),       # High, Medium, Low
    status_filter: Optional[str] = Query(None),  # Unresolved, Needs Review, In Progress, Resolved
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Misconception).filter(Misconception.user_id == current_user.id)
    
    if priority and priority != "All":
        query = query.filter(Misconception.severity_level == priority.capitalize())
        
    if status_filter and status_filter != "All":
        sf = status_filter.strip().lower()
        if sf == "unresolved":
            query = query.filter(Misconception.status.in_(["New", "Unresolved"]))
        elif sf in ["needs review", "needs_review"]:
            query = query.filter(Misconception.status.in_(["Needs Review", "Needs_Review"]))
        elif sf in ["in progress", "in_progress", "improving"]:
            query = query.filter(Misconception.status.in_(["In Progress", "Improving", "in_progress"]))
        elif sf == "resolved":
            query = query.filter(Misconception.status == "Resolved")
        else:
            query = query.filter(Misconception.status.ilike(status_filter))
            
    misconceptions = query.order_by(desc(Misconception.severity_score), desc(Misconception.last_detected)).all()
    
    results = []
    for m in misconceptions:
        lec = db.query(Lecture).filter(Lecture.id == m.lecture_id).first()
        concept = db.query(Concept).filter(Concept.id == m.concept_id).first()
        
        c_start = concept.start_time if concept else 0.0
        c_end = concept.end_time if concept else 0.0
        correct_exp = (concept.core_concepts[0] if (concept and concept.core_concepts) else "Master foundational definition and invariant relationships.")
        incorrect_und = (concept.confusing_topics[0] if (concept and concept.confusing_topics) else (m.summary or "Superficial intuition ignoring core constraints."))

        results.append({
            "id": m.id,
            "user_id": m.user_id,
            "lecture_id": m.lecture_id,
            "lecture_title": lec.title if lec else "Lecture",
            "concept_id": m.concept_id,
            "concept_name": m.concept_name,
            "title": m.title,
            "summary": m.summary,
            "incorrect_understanding": incorrect_und,
            "correct_explanation": correct_exp,
            "concept_start_time": c_start,
            "concept_end_time": c_end,
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

    # ── Root-cause enrichment via prerequisite links ──────────────────────────
    try:
        # Build set of unresolved concept names (lowercase for matching)
        unresolved_names = set()
        concept_name_map: dict = {}  # concept_name -> result dict(s)
        for r in results:
            st = (r.get("status") or "").lower()
            cname = r.get("concept_name", "")
            if st not in ("resolved",):
                unresolved_names.add(cname.lower())
            concept_name_map.setdefault(cname, []).append(r)

        if unresolved_names:
            root_causes = await find_root_causes_for_misconceptions(
                student_id=current_user.id,
                misconception_concept_names=[r["concept_name"] for r in results],
                unresolved_concept_names=unresolved_names,
            )
            # Enrich results with root-cause info
            for concept_name, rc_info in root_causes.items():
                rc_lid = rc_info.get("from_lecture_id")
                rc_lecture = db.query(Lecture).filter(Lecture.id == rc_lid).first() if rc_lid else None
                for r in concept_name_map.get(concept_name, []):
                    r["root_cause_concept"] = rc_info["root_cause_concept"]
                    r["root_cause_lecture_id"] = rc_lid
                    r["root_cause_lecture_title"] = rc_lecture.title if rc_lecture else None
    except Exception as _rc_err:
        print(f"[RootCause] Non-fatal enrichment error: {_rc_err}")

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


@router.get("/{misconception_id}/details", response_model=MisconceptionDetailOut)
async def get_misconception_details_endpoint(
    misconception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns complete breakdown of why the system detected that misconception:
    - Concept Name
    - Why It Was Detected (based on question & student's wrong answer)
    - Original Question
    - Student's Wrong Answer
    - Correct Answer
    - Detection Evidence
    - Lecture Evidence (supporting transcript excerpt or 'Evidence not available')
    - Replay timestamps (concept_start_time, concept_end_time)
    - Marked Unresolved status and reason
    - Assessment History (chronological list of attempts)
    - Current System Status
    - Next Reassessment information
    """
    misc = db.query(Misconception).filter(
        Misconception.id == misconception_id,
        Misconception.user_id == current_user.id
    ).first()
    if not misc:
        raise HTTPException(status_code=404, detail="Misconception not found.")

    concept = db.query(Concept).filter(Concept.id == misc.concept_id).first()
    lecture = db.query(Lecture).filter(Lecture.id == misc.lecture_id).first()

    # Query all attempts for this concept by this student in chronological order
    attempts_db = (
        db.query(CheckpointAttempt)
        .join(Checkpoint)
        .filter(
            Checkpoint.concept_id == misc.concept_id,
            CheckpointAttempt.user_id == current_user.id
        )
        .order_by(CheckpointAttempt.created_at.asc())
        .all()
    )

    # Find the initial failed attempt
    first_bad = next((a for a in attempts_db if not a.is_correct), None)
    if not first_bad and attempts_db:
        first_bad = attempts_db[0]

    if first_bad:
        chk = first_bad.checkpoint
        orig_q = chk.question_text if chk else (misc.title or f"Diagnostic question on {misc.concept_name}")
        student_wrong = first_bad.student_answer or "Incorrect answer"
        correct_ans = (chk.correct_answer if chk else None) or (concept.core_concepts[0] if concept and concept.core_concepts else "Expected conceptual answer")
        feedback = first_bad.feedback_reason or first_bad.detected_misconception_note
        det_evidence = (
            feedback.strip()
            if feedback and feedback.strip()
            else f"Student selected '{student_wrong}' instead of '{correct_ans}', indicating conceptual misalignment with {misc.concept_name}."
        )
    else:
        orig_q = misc.title or f"Diagnostic assessment on {misc.concept_name}"
        student_wrong = "Incorrect option"
        correct_ans = concept.core_concepts[0] if (concept and concept.core_concepts) else "Core conceptual definition"
        det_evidence = misc.summary or f"Conceptual discrepancy identified in {misc.concept_name}."

    why_detected = (
        f"System identified this misconception because when asked: \"{orig_q}\", "
        f"the student answered \"{student_wrong}\" instead of \"{correct_ans}\". "
        f"This response demonstrates that the student misunderstood the core invariant of {misc.concept_name}."
    )

    # Lecture transcript evidence excerpt
    transcript_snippet = ""
    if concept and concept.transcript_text and concept.transcript_text.strip():
        transcript_snippet = concept.transcript_text.strip()
    elif lecture and getattr(lecture, "transcript_text", None):
        lt = lecture.transcript_text
        if concept and concept.title.lower() in lt.lower():
            idx = lt.lower().find(concept.title.lower())
            start = max(0, idx - 100)
            end = min(len(lt), idx + 250)
            transcript_snippet = "..." + lt[start:end].strip() + "..."
    
    lecture_evidence = transcript_snippet if transcript_snippet else "Evidence not available"

    # Marked unresolved details
    is_unresolved = (misc.status or "open").lower() in ["open", "unresolved", "new"]
    marked_unresolved_reason = (
        "Marked Unresolved because student demonstrated a misconception on this concept and has not yet passed the required reassessment."
        if is_unresolved
        else f"Concept is currently {misc.status}."
    )

    # Next reassessment details
    st = (misc.status or "open").lower()
    today_str = datetime.now(timezone.utc).date().isoformat()
    recheck_str = misc.recheck_due.isoformat() if misc.recheck_due else None
    improving_str = misc.improving_at.isoformat() if misc.improving_at else None
    
    if st == "resolved":
        next_reassessment_info = "Concept is successfully resolved through targeted reassessment. No pending reassessment."
    elif st == "improving":
        if recheck_str and recheck_str <= today_str:
            next_reassessment_info = f"Targeted reassessment is due and available now (scheduled for {recheck_str})."
        elif recheck_str:
            next_reassessment_info = f"Targeted reassessment scheduled for {recheck_str} (after 2-day consolidation window)."
        else:
            next_reassessment_info = "Targeted reassessment in preparation."
    else:
        next_reassessment_info = "Concept has active misconception ('open'). Will be included in next targeted reassessment session."

    # Build assessment history
    history_items = []
    seen_history = set()
    for a in attempts_db:
        key = (a.created_at.isoformat() if a.created_at else "", a.student_answer or "")
        seen_history.add(key)
        history_items.append({
            "question": a.checkpoint.question_text if a.checkpoint else orig_q,
            "student_answer": a.student_answer or "",
            "correct_answer": a.checkpoint.correct_answer if a.checkpoint else correct_ans,
            "is_correct": a.is_correct,
            "context_type": "checkpoint",
            "explanation": a.feedback_reason or (a.checkpoint.explanation if a.checkpoint else None),
            "created_at": a.created_at.isoformat() if a.created_at else None
        })

    # Also query MongoDB attempts if available
    try:
        from app.mongo import get_active_misconception
        m_doc = await get_active_misconception(student_id=current_user.id, concept=misc.concept_name)
        if m_doc and "attempts" in m_doc:
            for ma in m_doc.get("attempts", []):
                m_key = (ma.get("timestamp", ""), ma.get("student_answer", ""))
                if m_key not in seen_history:
                    seen_history.add(m_key)
                    history_items.append({
                        "question": ma.get("question", orig_q),
                        "student_answer": ma.get("student_answer", ""),
                        "correct_answer": correct_ans,
                        "is_correct": ma.get("is_correct", False),
                        "context_type": ma.get("context_type", "reassessment"),
                        "explanation": ma.get("explanation"),
                        "created_at": ma.get("timestamp")
                    })
    except Exception as e:
        print(f"[Details] MongoDB history warning: {e}")

    # Fallback if no history items exist yet: create 1 history entry for the initial detection
    if not history_items:
        history_items.append({
            "question": orig_q,
            "student_answer": student_wrong,
            "correct_answer": correct_ans,
            "is_correct": False,
            "context_type": "initial_checkpoint",
            "explanation": det_evidence,
            "created_at": misc.first_detected.isoformat() if misc.first_detected else None
        })

    return {
        "id": misc.id,
        "concept_id": misc.concept_id,
        "concept_name": misc.concept_name,
        "lecture_id": misc.lecture_id,
        "lecture_title": lecture.title if lecture else "Lecture",
        "why_detected": why_detected,
        "original_question": orig_q,
        "student_wrong_answer": student_wrong,
        "correct_answer": correct_ans,
        "detection_evidence": det_evidence,
        "lecture_evidence": lecture_evidence,
        "concept_start_time": concept.start_time if concept else 0.0,
        "concept_end_time": concept.end_time if concept else 60.0,
        "marked_unresolved": is_unresolved,
        "marked_unresolved_reason": marked_unresolved_reason,
        "status": misc.status or "open",
        "severity_level": misc.severity_level or "Medium",
        "severity_score": misc.severity_score or 2,
        "improving_at": improving_str,
        "recheck_due": recheck_str,
        "next_reassessment_info": next_reassessment_info,
        "relapse_count": getattr(misc, "relapse_count", 0) or 0,
        "resolved_at": misc.resolved_at.isoformat() if misc.resolved_at else None,
        "assessment_history": history_items
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
    misc = db.query(Misconception).filter(
        Misconception.id == misconception_id,
        Misconception.user_id == current_user.id
    ).first()
    if not misc:
        raise HTTPException(status_code=404, detail="Misconception not found.")

    checkpoint = (
        db.query(Checkpoint)
        .join(Concept)
        .join(Lecture)
        .filter(Checkpoint.id == resolve_in.checkpoint_id, Lecture.user_id == current_user.id)
        .first()
    )
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


@router.patch("/{misconception_id}/status")
@router.put("/{misconception_id}/status")
def update_misconception_status(
    misconception_id: int,
    payload: MisconceptionStatusUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Misconception status is strictly system-controlled based on assessment results.
    Students cannot manually update statuses (Open, Improving, Resolved).
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Misconception status is strictly system-controlled based on assessment and reassessment results. Manual status modification is not permitted."
    )

