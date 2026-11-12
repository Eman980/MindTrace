import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.all_models import (
    Misconception, MisconceptionEvidence, Concept, Lecture, ConceptProgress,
    Checkpoint, CheckpointAttempt, PlaybackEvent, User
)
from app.services.severity_service import calculate_misconception_severity, get_signal_weight
from app.services.checkpoint_service import checkpoint_service
from app.config import settings

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class MisconceptionService:
    def register_signal(
        self,
        db: Session,
        user_id: int,
        lecture_id: int,
        concept_id: int,
        signal_type: str,
        evidence_text: str,
        custom_points: Optional[int] = None,
        misconception_title: Optional[str] = None
    ) -> Misconception:
        """
        Core persistent misconception tracking engine.
        Appends evidence to an existing concept misconception or initializes a new one.
        Updates cumulative score, severity classification, and student progress records.
        """
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        concept_name = concept.title if concept else f"Concept #{concept_id}"
        
        # Determine points for this evidence
        points = get_signal_weight(signal_type, custom_points)
        
        # Look for existing active misconception for this user & concept
        misconception = (
            db.query(Misconception)
            .filter(
                Misconception.user_id == user_id,
                Misconception.concept_id == concept_id,
                Misconception.status.notin_(["Resolved", "resolved"])
            )
            .first()
        )
        
        if not misconception:
            title = misconception_title or f"Conceptual Confusion in {concept_name}"
            misconception = Misconception(
                user_id=user_id,
                lecture_id=lecture_id,
                concept_id=concept_id,
                concept_name=concept_name,
                title=title,
                summary=evidence_text,
                severity_score=0,
                severity_level="Low",
                occurrence_count=1,
                status="open",
                first_detected=utcnow(),
                last_detected=utcnow()
            )
            db.add(misconception)
            db.flush()
        else:
            misconception.status = "open"
            misconception.occurrence_count += 1
            misconception.last_detected = utcnow()
            if misconception_title and (not misconception.title or "Conceptual Confusion" in misconception.title):
                misconception.title = misconception_title
                
        # Append new evidence entry
        evidence = MisconceptionEvidence(
            misconception_id=misconception.id,
            signal_type=signal_type,
            evidence_text=evidence_text,
            points_added=points,
            created_at=utcnow()
        )
        db.add(evidence)
        db.flush()
        
        # Recalculate total severity from all accumulated evidence points
        all_evidence = db.query(MisconceptionEvidence).filter(
            MisconceptionEvidence.misconception_id == misconception.id
        ).all()
        
        total_score, level = calculate_misconception_severity([e.points_added for e in all_evidence])
        misconception.severity_score = total_score
        misconception.severity_level = level
        
        # Update Concept Progress
        self._update_concept_progress(db, user_id, concept_id, signal_type)
        
        db.commit()
        db.refresh(misconception)
        return misconception

    def _update_concept_progress(self, db: Session, user_id: int, concept_id: int, signal_type: str):
        progress = db.query(ConceptProgress).filter(
            ConceptProgress.user_id == user_id,
            ConceptProgress.concept_id == concept_id
        ).first()
        
        if not progress:
            progress = ConceptProgress(
                user_id=user_id,
                concept_id=concept_id,
                understanding_percentage=50,
                status="In Progress",
                last_studied=utcnow()
            )
            db.add(progress)
            db.flush()
            
        progress.last_studied = utcnow()
        
        if signal_type == "behavioural_replay":
            progress.replay_count += 1
            progress.understanding_percentage = max(10, progress.understanding_percentage - 10)
            progress.status = "Needs Attention"
        elif signal_type == "manual_unresolved":
            progress.marked_unresolved_count += 1
            progress.understanding_percentage = max(10, progress.understanding_percentage - 15)
            progress.status = "Needs Attention"
        elif signal_type == "explicit_checkpoint":
            progress.understanding_percentage = max(10, progress.understanding_percentage - 10)
            progress.status = "Needs Attention"

    def record_playback_event(
        self,
        db: Session,
        user_id: int,
        lecture_id: int,
        concept_id: Optional[int],
        event_type: str,
        timestamp_in_media: float,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records a video/audio player behavioral event.
        Detects if replay threshold is exceeded (e.g. 3 replays) and triggers behavioral signal.
        """
        event = PlaybackEvent(
            user_id=user_id,
            lecture_id=lecture_id,
            concept_id=concept_id,
            event_type=event_type,
            timestamp_in_media=timestamp_in_media,
            created_at=utcnow()
        )
        if details:
            event.details = details
        db.add(event)
        db.flush()
        
        replay_signal_triggered = False
        message = ""
        
        if event_type == "replay" and concept_id:
            # Count replays for this user and concept
            replay_count = db.query(PlaybackEvent).filter(
                PlaybackEvent.user_id == user_id,
                PlaybackEvent.concept_id == concept_id,
                PlaybackEvent.event_type == "replay"
            ).count()
            
            concept = db.query(Concept).filter(Concept.id == concept_id).first()
            c_title = concept.title if concept else f"Concept #{concept_id}"
            
            if replay_count >= settings.REPLAY_THRESHOLD:
                # Trigger behavioural misconception signal
                evidence_text = f"Student replayed '{c_title}' {replay_count} times (Threshold: {settings.REPLAY_THRESHOLD})"
                self.register_signal(
                    db=db,
                    user_id=user_id,
                    lecture_id=lecture_id,
                    concept_id=concept_id,
                    signal_type="behavioural_replay",
                    evidence_text=evidence_text,
                    misconception_title=f"Difficulty Grasping: {c_title}"
                )
                replay_signal_triggered = True
                message = f"Possible misconception detected: '{c_title}' has been replayed {replay_count} times."

        db.commit()
        return {
            "recorded": True,
            "replay_signal_triggered": replay_signal_triggered,
            "message": message
        }

    def mark_concept_unresolved(
        self,
        db: Session,
        user_id: int,
        lecture_id: int,
        concept_id: int,
        timestamp_in_media: float,
        reason: Optional[str] = None
    ) -> Misconception:
        """
        Handles the student explicitly clicking 'Mark as Unresolved'.
        Stores explicit signal with the student's stated point of confusion.
        """
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        c_name = concept.title if concept else f"Concept #{concept_id}"
        
        evidence_text = f"Student manually marked segment as unresolved at {int(timestamp_in_media)}s."
        if reason and reason.strip():
            evidence_text += f" Stated confusion: '{reason.strip()}'"
            
        misconception = self.register_signal(
            db=db,
            user_id=user_id,
            lecture_id=lecture_id,
            concept_id=concept_id,
            signal_type="manual_unresolved",
            evidence_text=evidence_text,
            misconception_title=f"Unresolved Point: {c_name}"
        )
        return misconception

    def get_review_data(self, db: Session, user_id: int, misconception_id: int) -> Dict[str, Any]:
        """
        Prepares the dedicated 'Review Concept' learning view.
        """
        misconception = db.query(Misconception).filter(
            Misconception.id == misconception_id,
            Misconception.user_id == user_id
        ).first()
        if not misconception:
            return None
            
        concept = db.query(Concept).filter(Concept.id == misconception.concept_id).first()
        
        # Find latest failed checkpoint attempt if any
        latest_bad_attempt = (
            db.query(CheckpointAttempt)
            .join(Checkpoint)
            .filter(
                Checkpoint.concept_id == misconception.concept_id,
                CheckpointAttempt.user_id == user_id,
                CheckpointAttempt.is_correct == False
            )
            .order_by(desc(CheckpointAttempt.created_at))
            .first()
        )
        
        bad_answer = latest_bad_attempt.student_answer if latest_bad_attempt else None
        why_problematic = latest_bad_attempt.feedback_reason if latest_bad_attempt and latest_bad_attempt.feedback_reason else "The previous answer conflated the conceptual boundaries of this topic."
        
        # Build pedagogically clear explanation
        clarification = (
            f"Key clarification for {misconception.concept_name}: "
            f"{concept.description if concept else 'Focus on the definition and distinguishing rules.'} "
            f"Always verify inputs versus outputs before applying operations."
        )
        
        # Retrieve or create a review checkpoint
        review_cp_data = checkpoint_service.get_review_checkpoint(misconception.concept_name)
        review_checkpoint = db.query(Checkpoint).filter(
            Checkpoint.concept_id == misconception.concept_id,
            Checkpoint.is_review_checkpoint == True
        ).first()
        
        if not review_checkpoint and concept:
            review_checkpoint = Checkpoint(
                concept_id=concept.id,
                question_type=review_cp_data["question_type"],
                question_text=review_cp_data["question_text"],
                options=review_cp_data["options"],
                correct_answer=review_cp_data["correct_answer"],
                explanation=review_cp_data["explanation"],
                is_review_checkpoint=True,
                order_index=99
            )
            db.add(review_checkpoint)
            db.commit()
            db.refresh(review_checkpoint)

        return {
            "misconception": misconception,
            "concept_title": concept.title if concept else misconception.concept_name,
            "concept_start_time": concept.start_time if concept else 0.0,
            "concept_end_time": concept.end_time if concept else 60.0,
            "transcript_snippet": concept.transcript_text if concept else "Transcript snippet available in player.",
            "previous_bad_answer": bad_answer,
            "why_problematic": why_problematic,
            "clarification_explanation": clarification,
            "review_checkpoint": review_checkpoint
        }

    def resolve_misconception_checkpoint(
        self,
        db: Session,
        user_id: int,
        misconception_id: int,
        is_correct: bool
    ) -> Misconception:
        """
        Updates the misconception status upon passing the review checkpoint.
        High Priority -> Improving -> Resolved
        """
        misconception = db.query(Misconception).filter(
            Misconception.id == misconception_id,
            Misconception.user_id == user_id
        ).first()
        if not misconception:
            return None
            
        if is_correct:
            # Misconception must NEVER move directly to Resolved without passing targeted reassessment
            misconception.status = "improving"
            misconception.improving_at = datetime.date.today()
            misconception.recheck_due = datetime.date.today() + datetime.timedelta(days=2)
            evidence_text = "Review checkpoint answered successfully; understanding is actively improving. Recheck scheduled."
            points = -2
                
            evidence = MisconceptionEvidence(
                misconception_id=misconception.id,
                signal_type="checkpoint_improving",
                evidence_text=evidence_text,
                points_added=points,
                created_at=utcnow()
            )
            db.add(evidence)
            
            # Recalculate severity
            all_evidence = db.query(MisconceptionEvidence).filter(
                MisconceptionEvidence.misconception_id == misconception.id
            ).all()
            total_score, level = calculate_misconception_severity([e.points_added for e in all_evidence])
            misconception.severity_score = max(0, total_score)
            misconception.severity_level = level if misconception.status != "Resolved" else "Low"
            
            # Update Concept Progress to Improving
            progress = db.query(ConceptProgress).filter(
                ConceptProgress.user_id == user_id,
                ConceptProgress.concept_id == misconception.concept_id
            ).first()
            if progress:
                progress.understanding_percentage = min(100, progress.understanding_percentage + 20)
                progress.status = "Improving"
                progress.last_studied = utcnow()
        else:
            was_improving = (misconception.status or "").lower() == "improving"
            misconception.status = "open"
            if was_improving:
                misconception.relapse_count = (getattr(misconception, "relapse_count", 0) or 0) + 1
            evidence = MisconceptionEvidence(
                misconception_id=misconception.id,
                signal_type="explicit_checkpoint",
                evidence_text="Review checkpoint attempt failed; requires additional instruction.",
                points_added=1,
                created_at=utcnow()
            )
            db.add(evidence)
            
        db.commit()
        db.refresh(misconception)
        return misconception

misconception_service = MisconceptionService()
