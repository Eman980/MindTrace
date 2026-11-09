import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.all_models import (
    Checkpoint, CheckpointAttempt, Concept, User, ConceptProgress, Misconception, Lecture
)
from app.schemas.all_schemas import CheckpointAnswerIn, CheckpointEvaluationOut
from app.services.evaluation_service import evaluation_service
from app.services.misconception_service import misconception_service
from app.services.explanation_check_service import (
    explanation_check_service,
    compute_evidence_status,
    should_count_as_pass,
    evaluate_resolution,
    VERDICTS_THAT_NEED_FOLLOWUP,
    VERDICT_NOT_CHECKED,
)
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/checkpoints", tags=["Checkpoints"])


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _hours_since_last_attempt(
    db: Session,
    user_id: int,
    concept_id: int,
    before_attempt_id: Optional[int] = None,
) -> Optional[float]:
    """
    Returns how many hours elapsed since the user's PREVIOUS attempt on any
    checkpoint belonging to this concept. Returns None if there was no prior
    attempt.
    """
    q = (
        db.query(CheckpointAttempt)
        .join(Checkpoint)
        .filter(
            CheckpointAttempt.user_id == user_id,
            Checkpoint.concept_id == concept_id,
        )
        .order_by(desc(CheckpointAttempt.created_at))
    )
    if before_attempt_id:
        q = q.filter(CheckpointAttempt.id != before_attempt_id)

    last = q.first()
    if not last or not last.created_at:
        return None

    now = _utcnow()
    last_ts = last.created_at
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=datetime.timezone.utc)
    delta = now - last_ts
    return delta.total_seconds() / 3600


def _count_valid_passes(
    db: Session,
    user_id: int,
    concept_id: int,
    intervention_shown_at: Optional[datetime.datetime],
    delay_hours: float,
) -> tuple[int, bool]:
    """
    Counts attempts that satisfy ALL pass criteria (correct + verdict=valid +
    confidence >= CONFIDENCE_FLOOR). Also returns whether at least one such
    pass occurred >= delay_hours after the intervention.

    Returns (n_passes, has_delayed_pass).
    """
    attempts = (
        db.query(CheckpointAttempt)
        .join(Checkpoint)
        .filter(
            CheckpointAttempt.user_id == user_id,
            CheckpointAttempt.is_correct == True,
            CheckpointAttempt.explanation_verdict == "valid",
            Checkpoint.concept_id == concept_id,
        )
        .all()
    )

    passes = [
        a for a in attempts
        if (a.confidence_level or 0) >= settings.CONFIDENCE_FLOOR
    ]
    n = len(passes)

    has_delayed = False
    if intervention_shown_at and passes:
        ivn = intervention_shown_at
        if ivn.tzinfo is None:
            ivn = ivn.replace(tzinfo=datetime.timezone.utc)
        for p in passes:
            ts = p.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            elapsed = (ts - ivn).total_seconds() / 3600
            if elapsed >= delay_hours:
                has_delayed = True
                break

    return n, has_delayed


@router.post("/answer", response_model=CheckpointEvaluationOut)
async def submit_checkpoint_answer(
    answer_in: CheckpointAnswerIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extended /answer endpoint.

    New fields accepted (all optional — old clients still work):
      confidence_level  : 1 (not sure) | 2 (somewhat sure) | 3 (very sure)
      explanation_text  : one-line "why" written BEFORE seeing feedback

    New fields returned:
      explanation_verdict : valid | too_brief | flawed_matches_label | flawed_other | not_checked
      verdict_reason      : one-sentence UI message about the explanation
      needs_followup      : True if a variant/transfer probe should be scheduled
      evidence_status     : current state-machine status (Suspected|Confirmed|Resolved|Recurred)

    State machine rules applied here (all thresholds from config, not hardcoded):
      - Wrong answer with confidence=3 OR 2+ wrongs → Confirmed
      - 1 wrong → Suspected
      - Pass = correct + verdict=valid + confidence >= CONFIDENCE_FLOOR
      - Resolved requires: intervention shown + N_PASS passes + one delayed pass
      - Any new wrong after Resolved → Recurred
    """
    # ── 1. Fetch checkpoint & concept ────────────────────────────────────────
    checkpoint = (
        db.query(Checkpoint)
        .join(Concept)
        .join(Lecture)
        .filter(Checkpoint.id == answer_in.checkpoint_id, Lecture.user_id == current_user.id)
        .first()
    )
    if not checkpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found.")

    concept = checkpoint.concept
    if not concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated concept not found.")

    # ── 2. Evaluate correctness (with 2-part diagnostic model) ──────────────
    eval_result = await evaluation_service.evaluate_answer(
        question_type=checkpoint.question_type,
        question_text=checkpoint.question_text,
        correct_answer=checkpoint.correct_answer,
        student_answer=answer_in.student_answer,
        explanation=checkpoint.explanation,
        target_misconception=checkpoint.target_misconception,
    )
    is_correct: bool = eval_result["correct"]

    # ── 3. Compute hours since previous attempt (for delay enforcement) ───────
    # We do this BEFORE inserting the new attempt so we don't count itself.
    hours_since = _hours_since_last_attempt(db, current_user.id, concept.id)

    # ── 4. Run explanation check (only on correct answers with explanation) ───
    explanation_verdict = VERDICT_NOT_CHECKED
    verdict_reason = ""
    raw_llm_eval = "{}"

    if is_correct and answer_in.explanation_text:
        check_result = await explanation_check_service.check(
            question_text=checkpoint.question_text,
            correct_answer=checkpoint.correct_answer,
            student_answer=answer_in.student_answer,
            explanation_text=answer_in.explanation_text,
            concept_title=concept.title,
            known_misconception_labels=None,  # Step 2 (catalog) will populate this
        )
        explanation_verdict = check_result["verdict"]
        verdict_reason = check_result["verdict_reason"]
        raw_llm_eval = check_result["raw_llm_output"]
    elif not answer_in.explanation_text:
        # No explanation provided at all — treat as not_checked (don't penalise)
        explanation_verdict = VERDICT_NOT_CHECKED
        verdict_reason = ""

    # ── 5. Save attempt with all new fields ──────────────────────────────────
    prior_attempts_count = db.query(CheckpointAttempt).filter(
        CheckpointAttempt.checkpoint_id == checkpoint.id,
        CheckpointAttempt.user_id == current_user.id
    ).count()
    current_attempt_number = prior_attempts_count + 1

    attempt = CheckpointAttempt(
        checkpoint_id=checkpoint.id,
        user_id=current_user.id,
        student_answer=answer_in.student_answer,
        is_correct=is_correct,
        confidence_score=eval_result.get("confidence", 1.0),   # system-computed (existing)
        feedback_reason=eval_result.get("reason", ""),
        detected_misconception_note=eval_result.get("misconception"),
        attempt_number=current_attempt_number,
        # ── New evidence fields ──────────────────────────────────────────────
        confidence_level=answer_in.confidence_level,
        explanation_text=answer_in.explanation_text,
        explanation_verdict=explanation_verdict,
        raw_llm_eval=raw_llm_eval,
        hours_since_prev=hours_since,
        created_at=_utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # ── 6. Update misconception record & state machine ────────────────────────
    misconception_updated = False
    new_severity_level = None
    needs_followup = False
    evidence_status_out: Optional[str] = None

    # Fetch (or create) active misconception for this user + concept
    misconception = (
        db.query(Misconception)
        .filter(
            Misconception.user_id == current_user.id,
            Misconception.concept_id == concept.id,
            Misconception.status != "Resolved",
        )
        .first()
    )

    if not is_correct:
        # ── Wrong answer: register signal + advance state machine ────────────
        evidence_text = (
            f"Incorrect answer on '{checkpoint.question_text[:60]}...'. "
            f"Student answered: '{answer_in.student_answer}'. "
            f"Note: {eval_result.get('misconception') or 'Conceptual misalignment'}"
        )
        if answer_in.confidence_level:
            evidence_text += f" | Student confidence: {answer_in.confidence_level}/3"

        misc = misconception_service.register_signal(
            db=db,
            user_id=current_user.id,
            lecture_id=concept.lecture_id,
            concept_id=concept.id,
            signal_type="explicit_checkpoint",
            evidence_text=evidence_text,
            misconception_title=eval_result.get("misconception") or f"Misconception in {concept.title}",
        )
        misconception_updated = True
        new_severity_level = misc.severity_level

        # Count total wrong evidences for this misconception
        wrong_count = sum(
            1 for e in misc.evidence if e.signal_type == "explicit_checkpoint"
        )

        new_ev_status = compute_evidence_status(
            current_status=misc.evidence_status,
            wrong_evidence_count=wrong_count,
            confidence_level=answer_in.confidence_level,
        )
        misc.evidence_status = new_ev_status
        db.commit()
        db.refresh(misc)
        evidence_status_out = new_ev_status

    else:
        # ── Correct answer ───────────────────────────────────────────────────

        # a) Update concept progress (existing logic)
        prog = db.query(ConceptProgress).filter(
            ConceptProgress.user_id == current_user.id,
            ConceptProgress.concept_id == concept.id,
        ).first()
        if prog:
            prog.checkpoints_correct += 1
            prog.understanding_percentage = min(100, prog.understanding_percentage + 25)
            if prog.understanding_percentage >= 80:
                prog.status = "Mastered"
            elif prog.status == "Not Started":
                prog.status = "In Progress"
            db.commit()

        # b) Explanation-check routing
        if explanation_verdict in VERDICTS_THAT_NEED_FOLLOWUP:
            # Does NOT count as a pass; schedule a follow-up variant/transfer
            needs_followup = True
            # IMPORTANT: do NOT set memorized_flag here (per brief rule).
            # memorized_flag is set only if the student THEN fails a follow-up.

        # c) Check if resolution criteria are now met
        if misconception:
            delay_hrs = settings.effective_delay_hours
            n_passes, has_delayed = _count_valid_passes(
                db,
                current_user.id,
                concept.id,
                misconception.intervention_shown_at,
                delay_hrs,
            )

            if evaluate_resolution(
                n_passing_attempts=n_passes,
                has_delayed_pass=has_delayed,
                intervention_shown=misconception.intervention_shown_at is not None,
                n_pass_threshold=settings.N_PASS,
            ):
                # All criteria met → mark Resolved
                misconception.evidence_status = "Resolved"
                misconception.status = "Resolved"          # keep legacy field in sync
                misconception.resolved_at = _utcnow()
                db.commit()
                db.refresh(misconception)
                misconception_updated = True
                new_severity_level = misconception.severity_level

            evidence_status_out = misconception.evidence_status

    # ── 7. Fetch complete attempts history for this checkpoint ────────────────
    all_attempts_db = db.query(CheckpointAttempt).filter(
        CheckpointAttempt.checkpoint_id == checkpoint.id,
        CheckpointAttempt.user_id == current_user.id
    ).order_by(CheckpointAttempt.created_at.asc()).all()

    attempts_history = [
        {
            "id": a.id,
            "checkpoint_id": a.checkpoint_id,
            "student_answer": a.student_answer,
            "is_correct": a.is_correct,
            "confidence_score": a.confidence_score,
            "feedback_reason": a.feedback_reason,
            "detected_misconception_note": a.detected_misconception_note,
            "confidence_level": a.confidence_level,
            "explanation_text": a.explanation_text,
            "explanation_verdict": a.explanation_verdict,
            "attempt_number": a.attempt_number or (att_idx + 1),
            "created_at": a.created_at,
            "correct_answer": checkpoint.correct_answer,
            "explanation": checkpoint.explanation,
        }
        for att_idx, a in enumerate(all_attempts_db)
    ]

    remediation_ts = float(checkpoint.source_timestamp) if checkpoint.source_timestamp is not None else (
        float(concept.start_time) if concept.start_time is not None else 0.0
    )

    return {
        "checkpoint_id": checkpoint.id,
        "student_answer": answer_in.student_answer,
        "is_correct": is_correct,
        "confidence": eval_result.get("confidence", 1.0),
        "feedback_reason": eval_result.get("reason", ""),
        "detected_misconception_note": eval_result.get("misconception"),
        "correct_answer": checkpoint.correct_answer,
        "explanation": checkpoint.explanation,
        "points_awarded": 10 if is_correct else 0,
        "misconception_created_or_updated": misconception_updated,
        "new_severity_level": new_severity_level,
        # ── 2-Part Misconception Signal Treatment & Remediation ──────────────
        "conceptual_trap": eval_result.get("conceptual_trap"),
        "correct_mental_model": eval_result.get("correct_mental_model"),
        "remediation_timestamp": remediation_ts,
        "concept_id": concept.id,
        "concept_title": concept.title,
        "source_excerpt": checkpoint.source_excerpt,
        "source_timestamp": checkpoint.source_timestamp,
        # ── Attempt Sequence & History ───────────────────────────────────────────
        "attempt_id": attempt.id,
        "attempt_number": current_attempt_number,
        "total_attempts": len(attempts_history),
        "attempts": attempts_history,
        # ── Evidence state machine fields ────────────────────────────────────
        "explanation_verdict": explanation_verdict,
        "verdict_reason": verdict_reason,
        "needs_followup": needs_followup,
        "evidence_status": evidence_status_out,
    }

@router.get("/{checkpoint_id}/attempts", response_model=list)
def get_checkpoint_attempts(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all saved attempts by the current user for this checkpoint."""
    checkpoint = (
        db.query(Checkpoint)
        .join(Concept)
        .join(Lecture)
        .filter(Checkpoint.id == checkpoint_id, Lecture.user_id == current_user.id)
        .first()
    )
    if not checkpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found.")

    attempts = db.query(CheckpointAttempt).filter(
        CheckpointAttempt.checkpoint_id == checkpoint_id,
        CheckpointAttempt.user_id == current_user.id,
    ).order_by(CheckpointAttempt.created_at.asc()).all()

    return [
        {
            "id": a.id,
            "checkpoint_id": a.checkpoint_id,
            "student_answer": a.student_answer,
            "is_correct": a.is_correct,
            "confidence_score": a.confidence_score,
            "feedback_reason": a.feedback_reason,
            "detected_misconception_note": a.detected_misconception_note,
            "confidence_level": a.confidence_level,
            "explanation_text": a.explanation_text,
            "explanation_verdict": a.explanation_verdict,
            "attempt_number": a.attempt_number or (idx + 1),
            "created_at": a.created_at,
            "correct_answer": checkpoint.correct_answer,
            "explanation": checkpoint.explanation,
        }
        for idx, a in enumerate(attempts)
    ]
