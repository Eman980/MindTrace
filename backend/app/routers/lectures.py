import os
import uuid
import hashlib
import aiofiles
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.all_models import (
    User, Lecture, MediaFile, Transcript, TranscriptSegment,
    Concept, Checkpoint, CheckpointAttempt, Misconception, ConceptProgress
)
from app.schemas.all_schemas import LectureOut, LectureDetailOut
from app.utils.security import get_current_user
from app.services.transcription_service import transcription_service
from app.services.concept_segmentation_service import concept_segmentation_service
from app.services.checkpoint_service import checkpoint_service
from app.services.audio_gen import generate_sample_audio_if_needed
from app.services.audio_processing_service import audio_processing_service
from app.config import settings

router = APIRouter(prefix="/lectures", tags=["Lectures"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".ogg"}
ALLOWED_MIME_TYPES = {
    "video/mp4", "video/quicktime", "video/webm", "video/ogg",
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/wave",
    "audio/m4a", "audio/mp4", "audio/x-m4a",
    "audio/ogg", "application/ogg", "audio/vorbis", "audio/opus"
}

@router.get("", response_model=List[LectureOut])
def list_lectures(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lectures = db.query(Lecture).filter(Lecture.user_id == current_user.id).order_by(desc(Lecture.created_at)).all()
    results = []
    for lec in lectures:
        c_count = len(lec.concepts)
        unresolved_count = db.query(Misconception).filter(
            Misconception.lecture_id == lec.id,
            Misconception.user_id == current_user.id,
            Misconception.status == "Unresolved"
        ).count()
        
        # Calculate average progress
        progress_records = db.query(ConceptProgress).join(Concept).filter(
            Concept.lecture_id == lec.id,
            ConceptProgress.user_id == current_user.id
        ).all()
        
        if progress_records:
            avg_progress = int(sum(p.understanding_percentage for p in progress_records) / len(progress_records))
        else:
            avg_progress = 0

        results.append({
            "id": lec.id,
            "title": lec.title,
            "course_code": lec.course_code,
            "description": lec.description,
            "duration_seconds": lec.duration_seconds,
            "media_type": lec.media_type,
            "status": lec.status,
            "is_demo": lec.is_demo,
            "file_hash": lec.file_hash,
            "created_at": lec.created_at,
            "concepts_count": c_count,
            "unresolved_count": unresolved_count,
            "progress_percentage": avg_progress,
            "media_url": f"{settings.API_V1_PREFIX}/lectures/{lec.id}/media"
        })
    return results

async def transcribe_lecture_internal(
    lecture: Lecture,
    db: Session,
    manual_transcript: Optional[str] = None
) -> dict:
    if not lecture.media_file or not os.path.exists(lecture.media_file.file_path):
        raise ValueError("Associated media file does not exist on server storage.")

    media_path = lecture.media_file.file_path
    acoustic_info = await audio_processing_service.extract_acoustic_data(media_path)
    audio_for_stt = acoustic_info.get("audio_path_for_stt", media_path)
    detected_duration = acoustic_info.get("duration_seconds")

    stt_result = await transcription_service.transcribe_audio(
        audio_for_stt,
        filename=lecture.media_file.original_filename or "",
        title=lecture.title,
        detected_duration=detected_duration,
        manual_transcript=manual_transcript,
        is_demo=lecture.is_demo
    )
    lecture.duration_seconds = stt_result.get("duration", detected_duration or 300.0)
    lecture.transcription_status = "transcribed"
    db.commit()

    # Clear existing transcript if re-transcribing
    if lecture.transcript:
        db.delete(lecture.transcript)
        db.commit()

    transcript = Transcript(
        lecture_id=lecture.id,
        full_text=stt_result["full_text"],
        word_count=stt_result["word_count"],
        provider=stt_result["provider"]
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    for s_idx, seg in enumerate(stt_result["segments"]):
        t_seg = TranscriptSegment(
            transcript_id=transcript.id,
            start_time=seg["start_time"],
            end_time=seg["end_time"],
            text=seg["text"],
            speaker=seg.get("speaker", "Instructor"),
            segment_index=s_idx
        )
        db.add(t_seg)
    db.commit()
    return stt_result


async def generate_concepts_for_lecture_internal(
    lecture: Lecture,
    user_id: int,
    db: Session
) -> dict:
    if not lecture.transcript or not lecture.transcript.segments:
        await transcribe_lecture_internal(lecture, db)

    segments_data = [
        {"start_time": s.start_time, "end_time": s.end_time, "text": s.text}
        for s in lecture.transcript.segments
    ]
    concepts_data = await concept_segmentation_service.segment_transcript(
        transcript_segments=segments_data,
        full_text=lecture.transcript.full_text,
        lecture_title=lecture.title,
        duration=lecture.duration_seconds
    )

    # Delete existing concepts and checkpoints to regenerate cleanly
    for old_c in list(lecture.concepts):
        db.delete(old_c)
    db.commit()

    concepts_out = []
    total_chks = 0
    for c_idx, c_info in enumerate(concepts_data):
        concept = Concept(
            lecture_id=lecture.id,
            title=c_info["title"],
            description=c_info["description"],
            start_time=c_info["start_time"],
            end_time=c_info["end_time"],
            transcript_text=c_info.get("transcript_text", ""),
            order_index=c_info.get("order_index", c_idx),
            confidence_score=c_info.get("confidence_score", 0.95),
            core_concepts=c_info.get("core_concepts", []),
            confusing_topics=c_info.get("confusing_topics", [])
        )
        db.add(concept)
        db.commit()
        db.refresh(concept)

        chk_list = await checkpoint_service.generate_item_family_for_concept(
            concept_title=concept.title,
            concept_description=concept.description,
            transcript_text=concept.transcript_text or ""
        )
        total_chks += len(chk_list)
        for q_idx, q_item in enumerate(chk_list):
            chk = Checkpoint(
                concept_id=concept.id,
                question_type=q_item.get("question_type", "mcq"),
                question_text=q_item["question_text"],
                options=q_item.get("options", []),
                correct_answer=q_item["correct_answer"],
                explanation=q_item.get("explanation", ""),
                order_index=q_item.get("order_index", q_idx),
                is_review_checkpoint=q_item.get("is_review_checkpoint", False),
                item_family_role=q_item.get("item_family_role", "original"),
                target_misconception=q_item.get("target_misconception", None),
                source_excerpt=q_item.get("source_excerpt", None),
                source_timestamp=q_item.get("source_timestamp", None)
            )
            db.add(chk)

        prog = ConceptProgress(
            user_id=user_id,
            concept_id=concept.id,
            understanding_percentage=0,
            status="Not Started"
        )
        db.add(prog)

        concepts_out.append({
            "id": concept.id,
            "title": concept.title,
            "start_time": concept.start_time,
            "end_time": concept.end_time,
            "checkpoints_count": len(chk_list)
        })

    lecture.status = "ready"
    lecture.processing_error = None
    db.commit()
    db.refresh(lecture)

    return {
        "success": True,
        "recording_id": lecture.id,
        "lecture_id": lecture.id,
        "status": "ready",
        "concepts_count": len(concepts_out),
        "checkpoints_count": total_chks,
        "concepts": concepts_out
    }


@router.post("/upload")
async def upload_lecture(
    title: str = Form(...),
    course_code: str = Form("CS101"),
    description: Optional[str] = Form(""),
    transcript_text: Optional[str] = Form(None),
    transcript_file: Optional[UploadFile] = File(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validation
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media format '{ext}'. Allowed formats: MP4, MOV, WEBM, MP3, WAV, M4A, OGG"
        )

    content_type = (file.content_type or "").lower().strip()
    if content_type and content_type != "application/octet-stream" and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media MIME type '{file.content_type}'. Allowed MIME types include audio/ogg, application/ogg, MP3, WAV, MP4, etc."
        )

    media_type = "video" if ext in {".mp4", ".mov", ".webm"} else "audio"
    if ext == ".ogg":
        media_type = "audio"
        stored_mime_type = "audio/ogg" if content_type in ("audio/ogg", "application/ogg", "audio/vorbis", "audio/opus") else "audio/ogg"
    else:
        stored_mime_type = content_type or f"{media_type}/{ext[1:]}"

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    saved_file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save uploaded file and compute SHA-256 hash
    file_size = 0
    hasher = hashlib.sha256()
    try:
        async with aiofiles.open(saved_file_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                file_size += len(content)
                if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
                    )
                hasher.update(content)
                await out_file.write(content)
    except HTTPException:
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise
    except Exception as e:
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store media file on server: {str(e)}"
        )

    file_hash = hasher.hexdigest()

    # Check for existing duplicate lecture by content SHA-256 hash for the current user
    # If an existing lecture succeeded (status != "failed"), return it as a duplicate.
    # If a previous attempt failed, clean up the failed record to allow a fresh retry.
    existing_lecture = db.query(Lecture).filter(
        Lecture.user_id == current_user.id,
        Lecture.file_hash == file_hash,
        Lecture.status != "failed"
    ).first()
    if existing_lecture:
        # File is a duplicate! Remove redundant uploaded file to conserve disk space.
        if os.path.exists(saved_file_path):
            try:
                os.remove(saved_file_path)
            except OSError:
                pass

        return {
            "success": True,
            "is_duplicate": True,
            "message": "This lecture already exists in your library.",
            "lecture_id": existing_lecture.id,
            "recording_id": existing_lecture.id,
            "title": existing_lecture.title,
            "status": existing_lecture.status,
            "duration_seconds": existing_lecture.duration_seconds,
            "concepts_count": len(existing_lecture.concepts)
        }

    # Clean up any lingering failed record for this user and hash before re-attempting
    failed_prior = db.query(Lecture).filter(
        Lecture.user_id == current_user.id,
        Lecture.file_hash == file_hash,
        Lecture.status == "failed"
    ).all()
    for fp in failed_prior:
        db.delete(fp)
    if failed_prior:
        db.commit()

    # Read manual transcript if provided as file or text
    manual_transcript_content = None
    if transcript_file and transcript_file.filename:
        try:
            content_bytes = await transcript_file.read()
            manual_transcript_content = content_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass
    if not manual_transcript_content and transcript_text and transcript_text.strip():
        manual_transcript_content = transcript_text.strip()

    # 2. Create Lecture Record (safely handling simultaneous concurrent uploads)
    lecture = Lecture(
        user_id=current_user.id,
        title=title.strip(),
        course_code=course_code.strip() or "CS101",
        description=description.strip() if description else f"Lecture recording uploaded on {file.filename}",
        media_type=media_type,
        status="processing",
        is_demo=False,
        file_hash=file_hash
    )
    db.add(lecture)
    try:
        db.commit()
        db.refresh(lecture)
    except IntegrityError:
        db.rollback()
        # Another simultaneous upload with the identical hash committed first
        if os.path.exists(saved_file_path):
            try:
                os.remove(saved_file_path)
            except OSError:
                pass
        existing_lecture = db.query(Lecture).filter(
            Lecture.user_id == current_user.id,
            Lecture.file_hash == file_hash
        ).first()
        if existing_lecture:
            return {
                "success": True,
                "is_duplicate": True,
                "message": "This lecture already exists in your library.",
                "lecture_id": existing_lecture.id,
                "recording_id": existing_lecture.id,
                "title": existing_lecture.title,
                "status": existing_lecture.status,
                "duration_seconds": existing_lecture.duration_seconds,
                "concepts_count": len(existing_lecture.concepts)
            }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A lecture with this file is already being processed."
        )

    # 3. Store MediaFile Record
    media = MediaFile(
        lecture_id=lecture.id,
        original_filename=file.filename,
        stored_filename=unique_filename,
        file_path=saved_file_path,
        file_size=file_size,
        mime_type=stored_mime_type,
        file_hash=file_hash
    )
    db.add(media)
    db.commit()

    # 4. Execute Multi-stage Processing Pipeline
    try:
        await transcribe_lecture_internal(lecture, db, manual_transcript=manual_transcript_content)
        await generate_concepts_for_lecture_internal(lecture, current_user.id, db)
    except Exception as e:
        db.rollback()
        lecture.status = "failed"
        lecture.processing_error = str(e)
        db.commit()
        print(f"[UploadPipeline] Processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(e, ValueError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    return {
        "success": True,
        "is_duplicate": False,
        "message": "Lecture uploaded and processed successfully.",
        "lecture_id": lecture.id,
        "recording_id": lecture.id,
        "title": lecture.title,
        "status": lecture.status,
        "duration_seconds": lecture.duration_seconds,
        "concepts_count": len(lecture.concepts)
    }


@router.post("/transcribe/{lecture_id}")
@router.post("/transcribe/{lecture_id}")
@router.post("/{lecture_id}/transcribe")
async def transcribe_lecture_endpoint(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lecture = db.query(Lecture).filter(
        Lecture.id == lecture_id,
        Lecture.user_id == current_user.id
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Recording/Lecture {lecture_id} not found.")

    try:
        stt_result = await transcribe_lecture_internal(lecture, db)
        return {
            "success": True,
            "recording_id": lecture.id,
            "lecture_id": lecture.id,
            "transcription_status": "transcribed",
            "provider": stt_result["provider"],
            "full_text": stt_result["full_text"],
            "duration": lecture.duration_seconds,
            "word_count": stt_result["word_count"],
            "segments": stt_result["segments"]
        }
    except Exception as e:
        lecture.status = "failed"
        lecture.processing_error = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(e, ValueError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate/{lecture_id}")
@router.post("/{lecture_id}/generate")
async def generate_lecture_endpoint(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lecture = db.query(Lecture).filter(
        Lecture.id == lecture_id,
        Lecture.user_id == current_user.id
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Recording/Lecture {lecture_id} not found.")

    try:
        gen_result = await generate_concepts_for_lecture_internal(lecture, current_user.id, db)
        return gen_result
    except Exception as e:
        lecture.status = "failed"
        lecture.processing_error = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(e, ValueError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/segments/{lecture_id}")
@router.get("/{lecture_id}/segments")
def get_lecture_segments_endpoint(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lecture = db.query(Lecture).filter(
        Lecture.id == lecture_id,
        Lecture.user_id == current_user.id
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Recording/Lecture {lecture_id} not found.")

    segments = []
    if lecture.transcript and lecture.transcript.segments:
        segments = [
            {
                "id": s.id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text,
                "speaker": s.speaker,
                "segment_index": s.segment_index
            }
            for s in lecture.transcript.segments
        ]
    return {
        "success": True,
        "recording_id": lecture.id,
        "lecture_id": lecture.id,
        "full_text": lecture.transcript.full_text if lecture.transcript else "",
        "segments_count": len(segments),
        "segments": segments
    }


@router.post("/flag/{concept_id}")
def flag_concept_endpoint(
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

    from app.services.misconception_service import misconception_service
    res = misconception_service.mark_concept_unresolved(
        db=db,
        user_id=current_user.id,
        lecture_id=concept.lecture_id,
        concept_id=concept.id,
        timestamp_in_media=concept.start_time,
        reason="Explicitly flagged by student for revision"
    )
    return {"success": True, "message": "Concept flagged for review", "misconception_id": res.id if res else None}


@router.post("/replay/{concept_id}")
def replay_concept_endpoint(
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

    from app.services.misconception_service import misconception_service
    res = misconception_service.record_playback_event(
        db=db,
        user_id=current_user.id,
        lecture_id=concept.lecture_id,
        concept_id=concept.id,
        event_type="remediation_replay",
        timestamp_in_media=concept.start_time,
        details={"reason": "student_requested_replay"}
    )
    return res


@router.get("/report/{recording_id}")
def get_recording_report_endpoint(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lecture = db.query(Lecture).filter(
        Lecture.id == recording_id,
        Lecture.user_id == current_user.id
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found.")

    concepts = lecture.concepts
    total_checkpoints = sum(len(c.checkpoints) for c in concepts)
    
    attempts = (
        db.query(CheckpointAttempt)
        .join(Checkpoint)
        .join(Concept)
        .filter(Concept.lecture_id == lecture.id, CheckpointAttempt.user_id == current_user.id)
        .all()
    )
    
    correct_attempts = sum(1 for a in attempts if a.is_correct)
    accuracy = round((correct_attempts / len(attempts) * 100), 1) if attempts else 0.0

    misconceptions = (
        db.query(Misconception)
        .filter(Misconception.lecture_id == lecture.id, Misconception.user_id == current_user.id)
        .all()
    )

    return {
        "recording_id": lecture.id,
        "title": lecture.title,
        "duration_seconds": lecture.duration_seconds,
        "concepts_count": len(concepts),
        "total_checkpoints": total_checkpoints,
        "total_attempts": len(attempts),
        "correct_attempts": correct_attempts,
        "accuracy_percentage": accuracy,
        "misconceptions_count": len(misconceptions),
        "misconceptions": [
            {
                "id": m.id,
                "concept_id": m.concept_id,
                "label": m.label,
                "status": m.status,
                "severity_level": m.severity_level
            }
            for m in misconceptions
        ]
    }

@router.get("/{lecture_id}", response_model=LectureDetailOut)
def get_lecture(lecture_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lecture = db.query(Lecture).filter(
        Lecture.id == lecture_id,
        Lecture.user_id == current_user.id
    ).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture not found.")

    concepts_out = []
    for c in lecture.concepts:
        prog = db.query(ConceptProgress).filter(
            ConceptProgress.concept_id == c.id,
            ConceptProgress.user_id == current_user.id
        ).first()
        
        # Checkpoints - expose all diagnostic questions (Original, Variant, Near-Transfer) with student attempt history
        checkpoints_out = []
        for chk in sorted(c.checkpoints, key=lambda q: (q.order_index or 0)):
            chk_attempts = db.query(CheckpointAttempt).filter(
                CheckpointAttempt.checkpoint_id == chk.id,
                CheckpointAttempt.user_id == current_user.id
            ).order_by(CheckpointAttempt.created_at.asc()).all()

            attempts_data = [
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
                    "correct_answer": chk.correct_answer,
                    "explanation": chk.explanation,
                }
                for att_idx, a in enumerate(chk_attempts)
            ]
            latest_att = attempts_data[-1] if attempts_data else None

            checkpoints_out.append({
                "id": chk.id,
                "concept_id": chk.concept_id,
                "question_type": chk.question_type,
                "question_text": chk.question_text,
                "options": chk.options,
                "explanation": chk.explanation,
                "correct_answer": chk.correct_answer if latest_att else None,
                "order_index": chk.order_index,
                "is_review_checkpoint": chk.is_review_checkpoint,
                "item_family_role": chk.item_family_role or "original",
                "target_misconception": chk.target_misconception,
                "source_excerpt": chk.source_excerpt,
                "source_timestamp": chk.source_timestamp,
                "attempts": attempts_data,
                "latest_attempt": latest_att
            })

        concepts_out.append({
            "id": c.id,
            "lecture_id": c.lecture_id,
            "title": c.title,
            "description": c.description,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "order_index": c.order_index,
            "confidence_score": c.confidence_score,
            "transcript_text": c.transcript_text,
            "core_concepts": c.core_concepts,
            "confusing_topics": c.confusing_topics,
            "checkpoints_count": len(checkpoints_out),
            "checkpoints": checkpoints_out,
            "replay_count": prog.replay_count if prog else 0,
            "understanding_percentage": prog.understanding_percentage if prog else 0,
            "status": prog.status if prog else "Not Started"
        })

    # Unresolved count
    unresolved_count = db.query(Misconception).filter(
        Misconception.lecture_id == lecture.id,
        Misconception.user_id == current_user.id,
        Misconception.status == "Unresolved"
    ).count()

    # Progress
    progress_records = db.query(ConceptProgress).join(Concept).filter(
        Concept.lecture_id == lecture.id,
        ConceptProgress.user_id == current_user.id
    ).all()
    avg_progress = int(sum(p.understanding_percentage for p in progress_records) / len(progress_records)) if progress_records else 0

    transcript_out = None
    if lecture.transcript:
        segments_out = [
            {
                "id": s.id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text,
                "speaker": s.speaker,
                "segment_index": s.segment_index
            }
            for s in lecture.transcript.segments
        ]
        transcript_out = {
            "id": lecture.transcript.id,
            "full_text": lecture.transcript.full_text,
            "word_count": lecture.transcript.word_count,
            "provider": lecture.transcript.provider,
            "segments": segments_out
        }

    media_out = None
    if lecture.media_file:
        media_out = {
            "id": lecture.media_file.id,
            "original_filename": lecture.media_file.original_filename,
            "file_size": lecture.media_file.file_size,
            "mime_type": lecture.media_file.mime_type,
            "file_path": lecture.media_file.file_path,
            "file_hash": lecture.media_file.file_hash
        }

    return {
        "id": lecture.id,
        "title": lecture.title,
        "course_code": lecture.course_code,
        "description": lecture.description,
        "duration_seconds": lecture.duration_seconds,
        "media_type": lecture.media_type,
        "status": lecture.status,
        "is_demo": lecture.is_demo,
        "file_hash": lecture.file_hash,
        "created_at": lecture.created_at,
        "concepts_count": len(concepts_out),
        "unresolved_count": unresolved_count,
        "progress_percentage": avg_progress,
        "media_url": f"{settings.API_V1_PREFIX}/lectures/{lecture.id}/media",
        "media_file": media_out,
        "transcript": transcript_out,
        "concepts": concepts_out
    }

@router.get("/{lecture_id}/media")
def stream_media(lecture_id: int, request: Request, db: Session = Depends(get_db)):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture or not lecture.media_file:
        raise HTTPException(status_code=404, detail="Media file not found.")

    file_path = lecture.media_file.file_path
    
    # If sample audio was requested and file missing, generate it on-the-fly
    if not os.path.exists(file_path):
        sample_audio_path = os.path.join(settings.UPLOAD_DIR, "intro_to_functions.wav")
        generate_sample_audio_if_needed(sample_audio_path)
        file_path = sample_audio_path

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file missing from storage.")

    file_size = os.path.getsize(file_path)
    _, file_ext = os.path.splitext(file_path.lower())
    if file_ext == ".ogg":
        mime_type = "audio/ogg"
    else:
        mime_type = lecture.media_file.mime_type or "audio/wav"

    range_header = request.headers.get("range")
    if range_header:
        byte1, byte2 = 0, None
        match = range_header.replace("bytes=", "").split("-")
        if match[0]:
            byte1 = int(match[0])
        if len(match) > 1 and match[1]:
            byte2 = int(match[1])

        length = file_size - byte1 if byte2 is None else byte2 - byte1 + 1
        
        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(byte1)
                remaining = length
                while remaining > 0:
                    chunk_size = min(64 * 1024, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {byte1}-{byte1 + length - 1}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": mime_type,
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)

    return FileResponse(file_path, media_type=mime_type, filename=lecture.media_file.original_filename)

@router.delete("/{lecture_id}")
def delete_lecture(lecture_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lecture = db.query(Lecture).filter(
        Lecture.id == lecture_id,
        Lecture.user_id == current_user.id
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
        
    # Delete media file on disk if exists
    if lecture.media_file and os.path.exists(lecture.media_file.file_path):
        try:
            if not lecture.is_demo:  # Keep demo audio intact
                os.remove(lecture.media_file.file_path)
        except Exception:
            pass
            
    db.delete(lecture)
    db.commit()
    return {"success": True, "message": "Lecture deleted successfully."}
