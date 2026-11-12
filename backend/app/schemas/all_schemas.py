from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, date

# --- Auth & User ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

class ForgotPasswordOut(BaseModel):
    success: bool
    message: str
    email_sent: bool = False
    reset_token: Optional[str] = None
    note: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


# --- Transcript & Segments ---
class TranscriptSegmentOut(BaseModel):
    id: int
    start_time: float
    end_time: float
    text: str
    speaker: str
    segment_index: int
    
    class Config:
        from_attributes = True

class TranscriptOut(BaseModel):
    id: int
    full_text: str
    word_count: int
    provider: str
    segments: List[TranscriptSegmentOut] = []
    
    class Config:
        from_attributes = True


# --- Checkpoints ---
class CheckpointAttemptDetailOut(BaseModel):
    id: int
    checkpoint_id: int
    student_answer: str
    is_correct: bool
    confidence_score: Optional[float] = 1.0
    feedback_reason: Optional[str] = None
    detected_misconception_note: Optional[str] = None
    confidence_level: Optional[int] = None
    explanation_text: Optional[str] = None
    explanation_verdict: Optional[str] = None
    grade: Optional[str] = None
    attempt_number: int = 1
    created_at: datetime
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

    class Config:
        from_attributes = True

class CheckpointOut(BaseModel):
    id: int
    concept_id: int
    question_type: str
    question_text: str
    options: List[str] = []
    explanation: Optional[str] = None
    correct_answer: Optional[str] = None
    order_index: int
    is_review_checkpoint: bool = False
    item_family_role: Optional[str] = "original"
    target_misconception: Optional[str] = None
    source_excerpt: Optional[str] = None
    source_timestamp: Optional[float] = None
    source_start_timestamp: Optional[float] = None
    source_end_timestamp: Optional[float] = None
    lecture_id: Optional[int] = None
    lecture_title: Optional[str] = None
    difficulty: Optional[str] = "easy"
    scenario_text: Optional[str] = None
    attempts: List[CheckpointAttemptDetailOut] = []
    latest_attempt: Optional[CheckpointAttemptDetailOut] = None
    
    class Config:
        from_attributes = True

class CheckpointAnswerIn(BaseModel):
    checkpoint_id: int
    student_answer: str
    # ── New evidence-capture fields (optional so old clients keep working) ──
    # Student-reported confidence: 1=not sure, 2=somewhat sure, 3=very sure
    confidence_level: Optional[int] = Field(None, ge=1, le=3)
    # One-line "why" written by student BEFORE seeing feedback
    explanation_text: Optional[str] = Field(None, max_length=500)

class CheckpointEvaluationOut(BaseModel):
    checkpoint_id: int
    student_answer: str
    is_correct: bool
    confidence: float
    feedback_reason: str
    detected_misconception_note: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    points_awarded: int = 0
    misconception_created_or_updated: bool = False
    new_severity_level: Optional[str] = None
    grade: Optional[str] = None
    verdict: Optional[str] = None
    feedback: Optional[str] = None
    missing_point: Optional[str] = None
    # ── Misconception Deep Treatment Breakdown ────────────────────────────────
    conceptual_trap: Optional[str] = None
    correct_mental_model: Optional[str] = None
    remediation_timestamp: Optional[float] = None
    concept_id: Optional[int] = None
    concept_title: Optional[str] = None
    source_excerpt: Optional[str] = None
    source_timestamp: Optional[float] = None
    source_start_timestamp: Optional[float] = None
    source_end_timestamp: Optional[float] = None
    lecture_id: Optional[int] = None
    lecture_title: Optional[str] = None
    # ── Attempt Sequence & History ───────────────────────────────────────────
    attempt_id: Optional[int] = None
    attempt_number: Optional[int] = 1
    total_attempts: Optional[int] = 1
    attempts: List[CheckpointAttemptDetailOut] = []
    # ── Evidence state machine fields ─────────────────────────────────────────
    explanation_verdict: Optional[str] = None   # valid|too_brief|flawed_*|not_checked
    verdict_reason: Optional[str] = None         # one-sentence explanation for the UI
    needs_followup: bool = False                 # True if a variant/transfer item is due
    evidence_status: Optional[str] = None        # Suspected|Confirmed|Resolved|Recurred
    misconception_status: Optional[str] = None   # open|improving|resolved
    recheck_due: Optional[str] = None
    misconception_id: Optional[str] = None


# --- Concepts ---
class ConceptOut(BaseModel):
    id: int
    lecture_id: int
    title: str
    description: str
    start_time: float
    end_time: float
    order_index: int
    confidence_score: float
    checkpoints_count: int = 0
    replay_count: int = 0
    understanding_percentage: int = 0
    status: str = "Not Started"
    core_concepts: List[str] = []
    confusing_topics: List[str] = []
    
    class Config:
        from_attributes = True

class ConceptDetailOut(ConceptOut):
    transcript_text: Optional[str] = None
    checkpoints: List[CheckpointOut] = []


# --- Lectures ---
class MediaFileOut(BaseModel):
    id: int
    original_filename: str
    file_size: int
    mime_type: str
    file_path: str
    file_hash: Optional[str] = None
    
    class Config:
        from_attributes = True

class LectureOut(BaseModel):
    id: int
    title: str
    course_code: str
    description: Optional[str] = None
    duration_seconds: float
    media_type: str
    status: str
    transcription_status: Optional[str] = "ready"
    processing_error: Optional[str] = None
    is_demo: bool
    file_hash: Optional[str] = None
    prerequisite_lecture_id: Optional[int] = None
    prerequisite_lecture_title: Optional[str] = None
    created_at: datetime
    concepts_count: int = 0
    unresolved_count: int = 0
    progress_percentage: int = 0
    media_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class LectureUploadOut(BaseModel):
    success: bool
    lecture_id: int
    recording_id: int
    title: str
    status: str
    duration_seconds: float
    concepts_count: int
    is_duplicate: bool = False
    message: Optional[str] = None

class LectureUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_code: Optional[str] = None
    prerequisite_lecture_id: Optional[int] = None

class LectureDetailOut(LectureOut):
    media_file: Optional[MediaFileOut] = None
    transcript: Optional[TranscriptOut] = None
    concepts: List[ConceptDetailOut] = []


# --- Playback Events ---
class PlaybackEventIn(BaseModel):
    lecture_id: int
    concept_id: Optional[int] = None
    event_type: str  # play, pause, seek, replay, complete, unresolved_click
    timestamp_in_media: float
    details: Optional[Dict[str, Any]] = None

class PlaybackEventOut(BaseModel):
    id: int
    user_id: int
    lecture_id: int
    concept_id: Optional[int]
    event_type: str
    timestamp_in_media: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class UnresolvedMarkIn(BaseModel):
    lecture_id: int
    concept_id: int
    timestamp_in_media: float
    reason: Optional[str] = None


# --- Misconceptions ---
class MisconceptionEvidenceOut(BaseModel):
    id: int
    signal_type: str
    evidence_text: str
    points_added: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MisconceptionOut(BaseModel):
    id: int
    user_id: int
    lecture_id: int
    lecture_title: Optional[str] = None
    concept_id: int
    concept_name: str
    title: str
    summary: Optional[str] = None
    incorrect_understanding: Optional[str] = None
    correct_explanation: Optional[str] = None
    concept_start_time: Optional[float] = None
    concept_end_time: Optional[float] = None
    severity_score: int
    severity_level: str  # Low, Medium, High
    occurrence_count: int
    status: str          # Unresolved, Needs Review, In Progress, Resolved
    first_detected: datetime
    last_detected: datetime
    evidence: List[MisconceptionEvidenceOut] = []
    # ── New evidence-based state machine fields ───────────────────────────────
    evidence_status: Optional[str] = None       # Suspected|Confirmed|Memorized|Resolved|Recurred
    memorized_flag: Optional[bool] = False
    recurrence_count: Optional[int] = 0
    remediation_segment_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    improving_at: Optional[date] = None
    recheck_due: Optional[date] = None
    relapse_count: Optional[int] = 0
    # ── Root-cause prerequisite info ──────────────────────────────────────────
    root_cause_concept: Optional[str] = None
    root_cause_lecture_title: Optional[str] = None
    root_cause_lecture_id: Optional[int] = None

    class Config:
        from_attributes = True

class MisconceptionStatusUpdateIn(BaseModel):
    status: str

class MisconceptionAttemptHistoryItem(BaseModel):
    question: str
    student_answer: str
    correct_answer: Optional[str] = None
    is_correct: bool
    context_type: str = "checkpoint"
    explanation: Optional[str] = None
    created_at: Optional[str] = None

class MisconceptionDetailOut(BaseModel):
    id: int
    concept_id: int
    concept_name: str
    lecture_id: int
    lecture_title: str
    why_detected: str
    original_question: str
    student_wrong_answer: str
    correct_answer: str
    detection_evidence: str
    lecture_evidence: str
    concept_start_time: float
    concept_end_time: float
    marked_unresolved: bool
    marked_unresolved_reason: str
    status: str
    severity_level: str
    severity_score: int
    improving_at: Optional[str] = None
    recheck_due: Optional[str] = None
    next_reassessment_info: Optional[str] = None
    relapse_count: int
    resolved_at: Optional[str] = None
    assessment_history: List[MisconceptionAttemptHistoryItem] = []

class MisconceptionReviewOut(BaseModel):
    misconception: MisconceptionOut
    concept_title: str
    concept_start_time: float
    concept_end_time: float
    transcript_snippet: str
    previous_bad_answer: Optional[str] = None
    why_problematic: str
    clarification_explanation: str
    review_checkpoint: Optional[CheckpointOut] = None

class MisconceptionResolveIn(BaseModel):
    misconception_id: int
    checkpoint_id: int
    student_answer: str

class MisconceptionStatsOut(BaseModel):
    total_detected: int
    high_priority: int
    medium_priority: int
    low_priority: int
    unresolved: int
    improving: int
    resolved: int

class DashboardStatsOut(BaseModel):
    total_lectures: int
    concepts_identified: int
    misconceptions_detected: int
    unresolved_concepts: int
    concepts_improved: int
    recent_lectures: List[LectureOut] = []
    misconception_summary: MisconceptionStatsOut


# --- Reprobe & Ledger Schemas ---
class ReprobeItemOut(BaseModel):
    misconception_id: int
    concept_id: int
    concept_name: str
    lecture_id: int
    lecture_title: Optional[str] = None
    title: str
    evidence_status: Optional[str] = None
    severity_level: str
    severity_score: int
    last_detected: datetime
    hours_since_last_seen: float
    required_delay_hours: float
    is_due: bool
    reprobe_checkpoint: Optional[CheckpointOut] = None

    class Config:
        from_attributes = True

class LedgerAttemptOut(BaseModel):
    id: int
    checkpoint_id: int
    is_correct: bool
    confidence_level: Optional[int] = None
    explanation_text: Optional[str] = None
    explanation_verdict: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MisconceptionLedgerItemOut(MisconceptionOut):
    remediation_start_time: Optional[float] = None
    remediation_end_time: Optional[float] = None
    attempts: List[LedgerAttemptOut] = []


# --- Cross-Topic Prerequisite Re-Checking ---
class PrerequisiteRecheckQuestionOut(BaseModel):
    id: int
    concept_id: int
    question_type: str
    question_text: str
    options: List[str] = []
    explanation: Optional[str] = None
    item_family_role: Optional[str] = "variant"

class PrerequisiteRecheckOut(BaseModel):
    misconception_id: int
    misconception_title: str
    earlier_lecture_id: int
    earlier_lecture_title: str
    earlier_concept_id: int
    earlier_concept_name: str
    dependent_concept_name: str
    question: PrerequisiteRecheckQuestionOut

class PrerequisiteRecheckSubmitIn(BaseModel):
    misconception_id: int
    checkpoint_id: int
    student_answer: str

class PrerequisiteRecheckSubmitOut(BaseModel):
    is_correct: bool
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    new_status: str
    new_severity_level: str
    new_severity_score: int
    message: str


# --- Disguise Test Lifecycle Schemas ---
class DisguiseQuestionOut(BaseModel):
    misconception_id: str
    concept: str
    status: str
    question: str
    options: List[str]
    recheck_due: Optional[str] = None
    message: str = "Disguise test question ready. Choose the correct option to verify conceptual mastery."

class DisguiseAnswerIn(BaseModel):
    selected_index: Optional[int] = None
    student_answer: Optional[str] = None

class DisguiseAnswerOut(BaseModel):
    misconception_id: str
    concept: str
    is_correct: bool
    new_status: str
    correct_index: int
    explanation: str
    relapse_count: int
    message: str

class RecheckDueItemOut(BaseModel):
    id: str
    misconception_id: str
    concept_name: str
    concept: Optional[str] = None
    original_question: Optional[str] = None
    improving_at: Optional[str] = None
    recheck_due: str
    relapse_count: int = 0
    status: str = "improving"

