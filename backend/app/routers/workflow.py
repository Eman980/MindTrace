import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.all_models import User
from app.schemas.all_schemas import CheckpointAnswerIn, CheckpointEvaluationOut
from app.utils.security import get_current_user
from app.routers.lectures import (
    upload_lecture,
    transcribe_lecture_endpoint,
    generate_lecture_endpoint,
    get_lecture_segments_endpoint,
    flag_concept_endpoint,
    replay_concept_endpoint,
    get_recording_report_endpoint,
)
from app.routers.checkpoints import submit_checkpoint_answer

router = APIRouter(tags=["Workflow"])

@router.post("/upload")
async def workflow_upload(
    title: str = Form(...),
    course_code: str = Form("CS101"),
    description: Optional[str] = Form(""),
    transcript_text: Optional[str] = Form(None),
    transcript_file: Optional[UploadFile] = File(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await upload_lecture(
        title=title,
        course_code=course_code,
        description=description,
        transcript_text=transcript_text,
        transcript_file=transcript_file,
        file=file,
        db=db,
        current_user=current_user
    )

@router.post("/transcribe/{lecture_id}")
async def workflow_transcribe(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await transcribe_lecture_endpoint(
        lecture_id=lecture_id,
        db=db,
        current_user=current_user
    )

@router.post("/generate/{lecture_id}")
async def workflow_generate(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await generate_lecture_endpoint(
        lecture_id=lecture_id,
        db=db,
        current_user=current_user
    )

@router.get("/segments/{lecture_id}")
def workflow_segments(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_lecture_segments_endpoint(
        lecture_id=lecture_id,
        db=db,
        current_user=current_user
    )

@router.post("/answer", response_model=CheckpointEvaluationOut)
def workflow_answer(
    answer_in: CheckpointAnswerIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return submit_checkpoint_answer(
        answer_in=answer_in,
        db=db,
        current_user=current_user
    )

@router.post("/flag/{concept_id}")
def workflow_flag(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return flag_concept_endpoint(
        concept_id=concept_id,
        db=db,
        current_user=current_user
    )

@router.post("/replay/{concept_id}")
def workflow_replay(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return replay_concept_endpoint(
        concept_id=concept_id,
        db=db,
        current_user=current_user
    )

@router.get("/report/{recording_id}")
def workflow_report(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_recording_report_endpoint(
        recording_id=recording_id,
        db=db,
        current_user=current_user
    )

