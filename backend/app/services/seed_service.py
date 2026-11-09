import os
import datetime
from sqlalchemy.orm import Session

from app.models.all_models import (
    User, Lecture, MediaFile, Transcript, TranscriptSegment,
    Concept, Checkpoint, CheckpointAttempt, PlaybackEvent,
    Misconception, MisconceptionEvidence, ConceptProgress
)
from app.services.audio_gen import generate_sample_audio_if_needed
from app.services.checkpoint_service import checkpoint_service
from app.services.transcription_service import SAMPLE_FUNCTION_TRANSCRIPT
from app.services.concept_segmentation_service import SAMPLE_FUNCTION_CONCEPTS
from app.utils.security import get_password_hash
from app.config import settings

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def seed_demo_data(db: Session, target_user: User) -> Lecture:
    """
    Seeds the realistic Demo Lecture ('Introduction to Functions') with complete
    concepts, checkpoints, transcript segments, and pre-detected misconceptions.
    Allows viva demonstration without requiring any API keys or manual uploads.
    """
    if not target_user:
        raise ValueError("A valid target_user must be provided to seed_demo_data.")

    # Check if demo lecture already exists for this user
    existing_lecture = db.query(Lecture).filter(
        Lecture.user_id == target_user.id,
        Lecture.title == "Introduction to Functions",
        Lecture.is_demo == True
    ).first()
    
    if existing_lecture:
        return existing_lecture

    # Ensure playable sample audio exists
    sample_audio_path = os.path.join(settings.UPLOAD_DIR, "intro_to_functions.wav")
    generate_sample_audio_if_needed(sample_audio_path, duration_seconds=420)

    demo_hash = None
    if os.path.exists(sample_audio_path):
        import hashlib
        hasher = hashlib.sha256()
        with open(sample_audio_path, "rb") as sf:
            while chunk := sf.read(1024 * 1024):
                hasher.update(chunk)
        demo_hash = hasher.hexdigest()
    
    # 1. Create Lecture
    lecture = Lecture(
        user_id=target_user.id,
        title="Introduction to Functions",
        course_code="CS101",
        description="Comprehensive university lecture on pure functions, deterministic mapping, domain versus range, and function notation.",
        duration_seconds=420.0,
        media_type="audio",
        status="ready",
        is_demo=True,
        file_hash=demo_hash,
        created_at=utcnow()
    )
    db.add(lecture)
    db.flush()

    # 2. Media File
    media = MediaFile(
        lecture_id=lecture.id,
        original_filename="intro_to_functions.wav",
        stored_filename="intro_to_functions.wav",
        file_path=sample_audio_path,
        file_size=os.path.getsize(sample_audio_path) if os.path.exists(sample_audio_path) else 10240,
        mime_type="audio/wav",
        file_hash=demo_hash,
        created_at=utcnow()
    )
    db.add(media)

    # 3. Transcript
    full_text = " ".join(s["text"] for s in SAMPLE_FUNCTION_TRANSCRIPT)
    transcript = Transcript(
        lecture_id=lecture.id,
        full_text=full_text,
        word_count=len(full_text.split()),
        provider="MindTrace Demo STT Engine",
        created_at=utcnow()
    )
    db.add(transcript)
    db.flush()

    for idx, seg in enumerate(SAMPLE_FUNCTION_TRANSCRIPT):
        t_seg = TranscriptSegment(
            transcript_id=transcript.id,
            start_time=seg["start_time"],
            end_time=seg["end_time"],
            text=seg["text"],
            speaker=seg["speaker"],
            segment_index=idx
        )
        db.add(t_seg)

    # 4. Concepts & Checkpoints
    created_concepts = []
    for c_info in SAMPLE_FUNCTION_CONCEPTS:
        concept = Concept(
            lecture_id=lecture.id,
            title=c_info["title"],
            description=c_info["description"],
            start_time=c_info["start_time"],
            end_time=c_info["end_time"],
            transcript_text=c_info["transcript_text"],
            order_index=c_info["order_index"],
            confidence_score=c_info["confidence_score"],
            created_at=utcnow()
        )
        db.add(concept)
        db.flush()
        created_concepts.append(concept)

        # Checkpoints
        cps = checkpoint_service.get_checkpoints_for_concept(concept.title)
        for cp_idx, cp in enumerate(cps):
            chk = Checkpoint(
                concept_id=concept.id,
                question_type=cp["question_type"],
                question_text=cp["question_text"],
                options=cp["options"],
                correct_answer=cp["correct_answer"],
                explanation=cp["explanation"],
                order_index=cp_idx,
                is_review_checkpoint=False,
                item_family_role=cp.get("item_family_role", "original"),
                target_misconception=cp.get("target_misconception", None),
                source_excerpt=concept.transcript_text[:140] if concept.transcript_text else None,
                source_timestamp=concept.start_time,
                created_at=utcnow()
            )
            db.add(chk)

        # Initial Concept Progress
        prog = ConceptProgress(
            user_id=target_user.id,
            concept_id=concept.id,
            understanding_percentage=75 if c_info["order_index"] < 2 else (35 if c_info["order_index"] == 2 else 55),
            checkpoints_correct=1 if c_info["order_index"] < 2 else 0,
            checkpoints_total=len(cps),
            replay_count=4 if c_info["order_index"] == 2 else (2 if c_info["order_index"] == 3 else 1),
            marked_unresolved_count=1 if c_info["order_index"] == 2 else 0,
            status="Mastered" if c_info["order_index"] == 0 else ("Needs Attention" if c_info["order_index"] in [2, 3] else "In Progress"),
            last_studied=utcnow()
        )
        db.add(prog)

    db.flush()

    # 5. Pre-seed Demo Misconceptions
    domain_concept = next((c for c in created_concepts if "Domain and Range" in c.title), created_concepts[2])
    notation_concept = next((c for c in created_concepts if "Function Notation" in c.title), created_concepts[3])

    # Misconception 1: High Priority (Domain vs Range)
    misc_1 = Misconception(
        user_id=target_user.id,
        lecture_id=lecture.id,
        concept_id=domain_concept.id,
        concept_name="Domain vs Range",
        title="Domain vs Range Confusion",
        summary="Student persistently inverts the definition, treating output values as domain and inputs as range.",
        severity_score=7,
        severity_level="High",
        occurrence_count=3,
        status="Unresolved",
        evidence_status="Confirmed",
        remediation_segment_id=domain_concept.id,
        first_detected=utcnow() - datetime.timedelta(days=2),
        last_detected=utcnow() - datetime.timedelta(hours=3),
        created_at=utcnow() - datetime.timedelta(days=2)
    )
    db.add(misc_1)
    db.flush()

    # Evidence for Misc 1
    db.add(MisconceptionEvidence(
        misconception_id=misc_1.id,
        signal_type="explicit_checkpoint",
        evidence_text="Incorrect answer on checkpoint: Answered 'Range is the input set; Domain is the error boundary'",
        points_added=2,
        created_at=utcnow() - datetime.timedelta(days=2)
    ))
    db.add(MisconceptionEvidence(
        misconception_id=misc_1.id,
        signal_type="behavioural_replay",
        evidence_text="Student replayed 'Domain and Range Distinction' 4 times (Threshold: 3)",
        points_added=2,
        created_at=utcnow() - datetime.timedelta(days=1)
    ))
    db.add(MisconceptionEvidence(
        misconception_id=misc_1.id,
        signal_type="manual_unresolved",
        evidence_text="Student marked unresolved at 210s. Stated confusion: 'I don't understand why the output changes.'",
        points_added=3,
        created_at=utcnow() - datetime.timedelta(hours=3)
    ))

    # Misconception 2: Medium Priority (Function Notation)
    misc_2 = Misconception(
        user_id=target_user.id,
        lecture_id=lecture.id,
        concept_id=notation_concept.id,
        concept_name="Function Notation",
        title="Function Notation Misinterpretation",
        summary="Student confused variable parameters in notation f(x) with variable multiplication.",
        severity_score=4,
        severity_level="Medium",
        occurrence_count=2,
        status="Unresolved",
        evidence_status="Suspected",
        remediation_segment_id=notation_concept.id,
        first_detected=utcnow() - datetime.timedelta(days=1),
        last_detected=utcnow() - datetime.timedelta(hours=5),
        created_at=utcnow() - datetime.timedelta(days=1)
    )
    db.add(misc_2)
    db.flush()

    db.add(MisconceptionEvidence(
        misconception_id=misc_2.id,
        signal_type="explicit_checkpoint",
        evidence_text="Incorrect answer on checkpoint: Confused input parameter 'x' with multiplication.",
        points_added=2,
        created_at=utcnow() - datetime.timedelta(days=1)
    ))
    db.add(MisconceptionEvidence(
        misconception_id=misc_2.id,
        signal_type="behavioural_replay",
        evidence_text="Student replayed 'Function Notation & Syntax' 2 times.",
        points_added=2,
        created_at=utcnow() - datetime.timedelta(hours=5)
    ))

    db.commit()
    db.refresh(lecture)
    return lecture
