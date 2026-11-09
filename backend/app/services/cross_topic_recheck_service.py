import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.all_models import (
    Lecture, Concept, Checkpoint, CheckpointAttempt, Misconception, MisconceptionEvidence
)
from app.services.severity_service import calculate_misconception_severity

# Retained for reference from earlier version (no longer used for recheck triggering)
CONCEPT_DEPENDENCY_MAP: Dict[str, List[str]] = {
    "recursion": ["function", "functions", "return value"],
    "recursive": ["function", "functions", "return value"],
    "function composition": ["function", "functions"],
    "domain and range": ["function", "functions"],
    "higher order functions": ["function", "functions"],
    "tree traversal": ["recursion", "binary tree"],
}

def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class CrossTopicRecheckService:
    def get_prerequisite_rechecks(
        self,
        db: Session,
        user_id: int,
        lecture_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves unresolved misconceptions (at most 2, highest severity first)
        from the manually-linked PREREQUISITE lecture chosen by the student.
        Picks MCQ-type questions only (type = 'mcq').
        """
        current_lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.user_id == user_id
        ).first()
        if not current_lecture:
            return []

        # If this lecture has no prerequisite lecture assigned, nothing to recheck
        prereq_id = getattr(current_lecture, "prerequisite_lecture_id", None)
        if not prereq_id:
            return []

        prereq_lecture = db.query(Lecture).filter(
            Lecture.id == prereq_id,
            Lecture.user_id == user_id
        ).first()
        if not prereq_lecture:
            return []

        # Query open misconceptions from the prerequisite lecture
        # Status must be Unresolved or Needs Review (or New)
        open_misconceptions = (
            db.query(Misconception)
            .filter(
                Misconception.user_id == user_id,
                Misconception.lecture_id == prereq_lecture.id,
                Misconception.status.in_(["Unresolved", "Needs Review", "New"])
            )
            .order_by(desc(Misconception.severity_score), desc(Misconception.id))
            .limit(2)
            .all()
        )
        if not open_misconceptions:
            return []

        rechecks: List[Dict[str, Any]] = []

        for misc in open_misconceptions:
            # Find an existing MCQ question for this earlier concept (MCQ only)
            candidate_checkpoints = (
                db.query(Checkpoint)
                .filter(
                    Checkpoint.concept_id == misc.concept_id,
                    Checkpoint.question_type == "mcq"
                )
                .all()
            )

            chosen_chk: Optional[Checkpoint] = None
            # 1. Prefer variant or transfer question
            for chk in candidate_checkpoints:
                if chk.item_family_role in ["variant", "transfer"]:
                    chosen_chk = chk
                    break

            # 2. Prefer review checkpoint
            if not chosen_chk:
                for chk in candidate_checkpoints:
                    if chk.is_review_checkpoint:
                        chosen_chk = chk
                        break

            # 3. Fall back to any original MCQ checkpoint
            if not chosen_chk and candidate_checkpoints:
                chosen_chk = candidate_checkpoints[0]

            if not chosen_chk:
                continue

            rechecks.append({
                "misconception_id": misc.id,
                "misconception_title": misc.title,
                "earlier_lecture_id": prereq_lecture.id,
                "earlier_lecture_title": prereq_lecture.title,
                "earlier_concept_id": misc.concept_id,
                "earlier_concept_name": misc.concept_name,
                "dependent_concept_name": prereq_lecture.title,
                "question": {
                    "id": chosen_chk.id,
                    "concept_id": chosen_chk.concept_id,
                    "question_type": "mcq",
                    "question_text": chosen_chk.question_text,
                    "options": chosen_chk.options or [],
                    "explanation": chosen_chk.explanation,
                    "item_family_role": chosen_chk.item_family_role or "variant",
                }
            })

        return rechecks

    def submit_recheck_answer(
        self,
        db: Session,
        user_id: int,
        lecture_id: int,
        misconception_id: int,
        checkpoint_id: int,
        student_answer: str,
    ) -> Dict[str, Any]:
        """
        Evaluates the student's answer to a prerequisite recheck question.
        Correct -> marks misconception Resolved and logs 'Cross-topic recheck passed'.
        Incorrect -> keeps misconception open, logs 'Cross-topic recheck failed', increases severity.
        """
        misconception = db.query(Misconception).filter(
            Misconception.id == misconception_id,
            Misconception.user_id == user_id
        ).first()
        if not misconception:
            raise ValueError(f"Misconception {misconception_id} not found.")

        checkpoint = db.query(Checkpoint).filter(
            Checkpoint.id == checkpoint_id,
            Checkpoint.question_type == "mcq"
        ).first()
        if not checkpoint:
            # Also check if checkpoint exists regardless of type to provide informative error
            chk_any = db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
            if not chk_any:
                raise ValueError(f"Checkpoint {checkpoint_id} not found.")
            checkpoint = chk_any

        current_lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.user_id == user_id
        ).first()
        lec_title = current_lecture.title if current_lecture else f"Lecture #{lecture_id}"

        # Normalize and evaluate answer
        s_ans = (student_answer or "").strip()
        c_ans = (checkpoint.correct_answer or "").strip()
        is_correct = (s_ans.lower() == c_ans.lower())

        # Check letter / prefix match like "B) ..." vs "B" or "A. ..." vs "A"
        if not is_correct and checkpoint.options:
            if s_ans.startswith(c_ans + ")") or s_ans.startswith(c_ans + ".") or s_ans.startswith(c_ans + " "):
                is_correct = True
            elif c_ans.startswith(s_ans + ")") or c_ans.startswith(s_ans + ".") or c_ans.startswith(s_ans + " "):
                is_correct = True

        now = utcnow()

        if is_correct:
            misconception.status = "Resolved"
            misconception.evidence_status = "Resolved"
            misconception.resolved_at = now

            evidence_text = f"Cross-topic recheck passed in {lec_title}"
            points_added = -3
            signal_type = "checkpoint_resolved"
        else:
            misconception.status = "Unresolved"
            if misconception.evidence_status == "Resolved":
                misconception.evidence_status = "Recurred"
                misconception.recurrence_count = (misconception.recurrence_count or 0) + 1

            evidence_text = f"Cross-topic recheck failed in {lec_title}"
            points_added = 3
            signal_type = "explicit_checkpoint"

        # Record evidentiary signal in signal trail (once on submit)
        evidence = MisconceptionEvidence(
            misconception_id=misconception.id,
            signal_type=signal_type,
            evidence_text=evidence_text,
            points_added=points_added,
            created_at=now
        )
        db.add(evidence)
        db.flush()

        # Recalculate cumulative severity score & level from all evidence
        all_evidence = db.query(MisconceptionEvidence).filter(
            MisconceptionEvidence.misconception_id == misconception.id
        ).all()
        total_score, level = calculate_misconception_severity([e.points_added for e in all_evidence])
        misconception.severity_score = max(0, total_score)
        misconception.severity_level = level if misconception.status != "Resolved" else "Low"

        # Record checkpoint attempt for audit ledger
        attempt = CheckpointAttempt(
            checkpoint_id=checkpoint.id,
            user_id=user_id,
            student_answer=s_ans,
            is_correct=is_correct,
            confidence_score=1.0 if is_correct else 0.0,
            feedback_reason=f"Cross-topic recheck for {lec_title}: {'Correct' if is_correct else 'Incorrect'}",
            detected_misconception_note=f"Cross-topic check from {lec_title}",
            created_at=now
        )
        db.add(attempt)

        db.commit()
        db.refresh(misconception)

        return {
            "is_correct": is_correct,
            "correct_answer": checkpoint.correct_answer,
            "explanation": checkpoint.explanation,
            "new_status": misconception.status,
            "new_severity_level": misconception.severity_level,
            "new_severity_score": misconception.severity_score,
            "message": (
                "Prerequisite concept verified! Misconception marked Resolved."
                if is_correct
                else f"Prerequisite misconception remains open (+3 severity recorded)."
            )
        }

cross_topic_recheck_service = CrossTopicRecheckService()
