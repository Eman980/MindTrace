import datetime
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="student")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    lectures = relationship("Lecture", back_populates="user", cascade="all, delete-orphan")
    playback_events = relationship("PlaybackEvent", back_populates="user", cascade="all, delete-orphan")
    checkpoint_attempts = relationship("CheckpointAttempt", back_populates="user", cascade="all, delete-orphan")
    misconceptions = relationship("Misconception", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("ConceptProgress", back_populates="user", cascade="all, delete-orphan")


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    course_code = Column(String(100), default="CS101")
    description = Column(Text, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    media_type = Column(String(50), default="video")  # video or audio
    status = Column(String(50), default="ready")      # processing, ready, failed, needs_transcription
    transcription_status = Column(String(50), default="ready")  # ready, untranscribed, transcribed
    processing_error = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="lectures")
    media_file = relationship("MediaFile", uselist=False, back_populates="lecture", cascade="all, delete-orphan")
    transcript = relationship("Transcript", uselist=False, back_populates="lecture", cascade="all, delete-orphan")
    concepts = relationship("Concept", back_populates="lecture", cascade="all, delete-orphan", order_by="Concept.order_index")
    playback_events = relationship("PlaybackEvent", back_populates="lecture", cascade="all, delete-orphan")
    misconceptions = relationship("Misconception", back_populates="lecture", cascade="all, delete-orphan")


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), unique=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    lecture = relationship("Lecture", back_populates="media_file")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    provider = Column(String(50), default="whisper")  # whisper, mock_demo, etc.
    created_at = Column(DateTime(timezone=True), default=utcnow)

    lecture = relationship("Lecture", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan", order_by="TranscriptSegment.start_time")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(Float, nullable=False, index=True)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    speaker = Column(String(100), default="Instructor")
    segment_index = Column(Integer, default=0)

    transcript = relationship("Transcript", back_populates="segments")


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False, index=True)
    end_time = Column(Float, nullable=False)
    transcript_text = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.95)
    _core_concepts = Column("core_concepts", Text, nullable=True)
    _confusing_topics = Column("confusing_topics", Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    @property
    def core_concepts(self) -> List[str]:
        if self._core_concepts:
            try:
                import json
                parsed = json.loads(self._core_concepts)
                if isinstance(parsed, list) and parsed:
                    return parsed
            except Exception:
                pass
        return self._generate_default_core_concepts()

    @core_concepts.setter
    def core_concepts(self, val: List[str]):
        import json
        self._core_concepts = json.dumps(val)

    @property
    def confusing_topics(self) -> List[str]:
        if self._confusing_topics:
            try:
                import json
                parsed = json.loads(self._confusing_topics)
                if isinstance(parsed, list) and parsed:
                    return parsed
            except Exception:
                pass
        return self._generate_default_confusing_topics()

    @confusing_topics.setter
    def confusing_topics(self, val: List[str]):
        import json
        self._confusing_topics = json.dumps(val)

    def _generate_default_core_concepts(self) -> List[str]:
        t = self.title or "Concept Overview"
        return [
            f"Core Invariant: Foundational definition and scope established in {t}.",
            f"System Mechanics: Input-output transformation rules and state relationships.",
            f"Operational Guarantee: Predictable behavior across computational boundaries."
        ]

    def _generate_default_confusing_topics(self) -> List[str]:
        t = self.title or "Concept Overview"
        return [
            f"Cognitive Trap: Conflating surface naming with the underlying invariant of {t}.",
            f"Boundary Misunderstanding: Overlooking constraints under edge conditions or type shifts.",
            f"Directional Confusion: Swapping input constraints with resulting output expectations."
        ]

    lecture = relationship("Lecture", back_populates="concepts")
    checkpoints = relationship("Checkpoint", back_populates="concept", cascade="all, delete-orphan", order_by="Checkpoint.order_index")
    misconceptions = relationship("Misconception", back_populates="concept", cascade="all, delete-orphan")
    progress_records = relationship("ConceptProgress", back_populates="concept", cascade="all, delete-orphan")


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_type = Column(String(50), default="mcq")  # mcq or short_answer
    question_text = Column(Text, nullable=False)
    _options = Column("options", Text, nullable=True)  # JSON-encoded array for MCQ
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)
    is_review_checkpoint = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # ── Item Families fields ──────────────────────────────────────────────────
    # original = first encounter in video | variant = isomorphic | transfer = novel near-transfer
    item_family_role = Column(String(50), nullable=True, default="original")
    target_misconception = Column(Text, nullable=True)
    source_excerpt = Column(Text, nullable=True)
    source_timestamp = Column(Float, nullable=True)

    concept = relationship("Concept", back_populates="checkpoints")
    attempts = relationship("CheckpointAttempt", back_populates="checkpoint", cascade="all, delete-orphan")

    @property
    def options(self):
        if not self._options:
            return []
        try:
            return json.loads(self._options)
        except Exception:
            return []

    @options.setter
    def options(self, val):
        if val is None:
            self._options = None
        else:
            self._options = json.dumps(val)


class CheckpointAttempt(Base):
    __tablename__ = "checkpoint_attempts"

    id = Column(Integer, primary_key=True, index=True)
    checkpoint_id = Column(Integer, ForeignKey("checkpoints.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Original columns (kept intact for backward-compat) ──────────────────
    student_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    confidence_score = Column(Float, default=1.0)        # system-computed (0-1)
    feedback_reason = Column(Text, nullable=True)
    detected_misconception_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # ── New columns for evidence-based resolution (all nullable / defaulted) ─
    # Student-reported confidence on a 1-3 scale: 1=not sure, 2=somewhat sure, 3=very sure
    confidence_level = Column(Integer, nullable=True)    # 1 | 2 | 3

    # One-line "why" explanation the student writes before seeing feedback
    explanation_text = Column(Text, nullable=True)

    # Verdict from the LLM explanation-checker
    # valid | too_brief | flawed_matches_label | flawed_other | not_checked
    explanation_verdict = Column(String(50), nullable=True, default="not_checked")

    # Full raw LLM output stored for auditability (E2 calibration study)
    raw_llm_eval = Column(Text, nullable=True)

    # Hours elapsed since the user's PREVIOUS attempt on any item in this concept family.
    # Null if this is the first attempt. Used to enforce MIN_DELAY_HOURS for resolution.
    hours_since_prev = Column(Float, nullable=True)

    # Sequence number for this student on this checkpoint (1, 2, 3...)
    attempt_number = Column(Integer, default=1, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    checkpoint = relationship("Checkpoint", back_populates="attempts")
    user = relationship("User", back_populates="checkpoint_attempts")


class PlaybackEvent(Base):
    __tablename__ = "playback_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)  # play, pause, seek, replay, complete, unresolved_click
    timestamp_in_media = Column(Float, default=0.0)
    _details = Column("details", Text, nullable=True)  # JSON-encoded extra details
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="playback_events")
    lecture = relationship("Lecture", back_populates="playback_events")

    @property
    def details(self):
        if not self._details:
            return {}
        try:
            return json.loads(self._details)
        except Exception:
            return {}

    @details.setter
    def details(self, val):
        if val is None:
            self._details = None
        else:
            self._details = json.dumps(val)


class Misconception(Base):
    __tablename__ = "misconceptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)

    severity_score = Column(Integer, default=2)
    severity_level = Column(String(20), default="Medium")  # Low, Medium, High
    occurrence_count = Column(Integer, default=1)

    # ── Old status field (KEPT for backward-compat with existing UI/queries) ─
    status = Column(String(50), default="Unresolved")   # New, Unresolved, Improving, Resolved

    # ── New parallel evidence_status field (state machine from brief) ────────
    # Suspected -> Confirmed -> Resolved | Memorized; any new evidence after
    # Resolved sets it to Recurred.
    evidence_status = Column(
        String(50), nullable=True, default=None,
        # Suspected | Confirmed | Memorized | Resolved | Recurred
    )

    # Set True only when student passed an original item but FAILED a follow-up
    # variant/transfer item — indicates rote memory without understanding.
    memorized_flag = Column(Boolean, default=False, nullable=True)

    # Concept segment ID where the correct idea was taught (remediation anchor).
    remediation_segment_id = Column(Integer, nullable=True)

    # Timestamp when the intervention (lecture replay + explanation) was shown
    intervention_shown_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamp when the record was first marked Resolved
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Count of times status went back to Confirmed after having been Resolved
    recurrence_count = Column(Integer, default=0, nullable=True)

    first_detected = Column(DateTime(timezone=True), default=utcnow)
    last_detected = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="misconceptions")
    lecture = relationship("Lecture", back_populates="misconceptions")
    concept = relationship("Concept", back_populates="misconceptions")
    evidence = relationship(
        "MisconceptionEvidence",
        back_populates="misconception",
        cascade="all, delete-orphan",
        order_by="MisconceptionEvidence.created_at.desc()"
    )


class MisconceptionEvidence(Base):
    __tablename__ = "misconception_evidence"

    id = Column(Integer, primary_key=True, index=True)
    misconception_id = Column(Integer, ForeignKey("misconceptions.id", ondelete="CASCADE"), nullable=False, index=True)
    # signal_type values:
    #   explicit_checkpoint | behavioural_replay | manual_unresolved |
    #   conversational_pattern | checkpoint_resolved |
    #   explanation_check_pass | explanation_check_fail | delayed_pass | recurred
    signal_type = Column(String(50), nullable=False)
    evidence_text = Column(Text, nullable=False)
    points_added = Column(Integer, default=2)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    misconception = relationship("Misconception", back_populates="evidence")


class ConceptProgress(Base):
    __tablename__ = "concept_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)

    understanding_percentage = Column(Integer, default=0)
    checkpoints_correct = Column(Integer, default=0)
    checkpoints_total = Column(Integer, default=0)
    replay_count = Column(Integer, default=0)
    marked_unresolved_count = Column(Integer, default=0)
    status = Column(String(50), default="Not Started")  # Not Started, In Progress, Needs Attention, Improving, Mastered

    last_studied = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="progress_records")
    concept = relationship("Concept", back_populates="progress_records")

    __table_args__ = (
        Index("idx_user_concept_progress", "user_id", "concept_id", unique=True),
    )
