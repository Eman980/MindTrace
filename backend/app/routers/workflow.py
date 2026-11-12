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
async def workflow_answer(
    answer_in: CheckpointAnswerIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await submit_checkpoint_answer(
        answer_in=answer_in,
        db=db,
        current_user=current_user
    )

@router.post("/flag/{concept_id}")
async def workflow_flag(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await flag_concept_endpoint(
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
async def workflow_report(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_recording_report_endpoint(
        recording_id=recording_id,
        db=db,
        current_user=current_user
    )

@router.get("/report")
async def workflow_general_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Overall report across all recordings for the current student."""
    from app.models.all_models import Misconception
    all_misc = db.query(Misconception).filter(Misconception.user_id == current_user.id).all()

    open_count = 0
    improving_count = 0
    resolved_count = 0
    relapse_list = []

    for m in all_misc:
        st = (m.status or "open").lower()
        if st == "improving":
            improving_count += 1
        elif st in ["resolved", "mastered"]:
            resolved_count += 1
        else:
            open_count += 1

        relapse_cnt = getattr(m, "relapse_count", 0) or 0
        if relapse_cnt > 0:
            relapse_list.append({
                "misconception_id": str(m.id),
                "concept": m.concept_name or m.title,
                "status": m.status,
                "relapse_count": relapse_cnt,
                "label": "memorized, not understood",
                "explanation": m.summary or "First correct answer was memorized, not understood."
            })

    try:
        from app.mongo import get_misconceptions_report_data
        mongo_rep = await get_misconceptions_report_data(student_id=current_user.id)
        if mongo_rep:
            sc = mongo_rep.get("status_counts", {})
            if sc.get("open", 0) > 0 or sc.get("improving", 0) > 0 or sc.get("resolved", 0) > 0:
                open_count = max(open_count, sc.get("open", 0))
                improving_count = max(improving_count, sc.get("improving", 0))
                resolved_count = max(resolved_count, sc.get("resolved", 0))

            seen_ids = {r["misconception_id"] for r in relapse_list}
            for mr in mongo_rep.get("relapses", []):
                if mr["misconception_id"] not in seen_ids:
                    relapse_list.append(mr)
                    seen_ids.add(mr["misconception_id"])
    except Exception as e:
        print(f"[WorkflowReport] Mongo merge warning: {e}")

    return {
        "status_counts": {
            "open": open_count,
            "improving": improving_count,
            "resolved": resolved_count
        },
        "relapse_list": relapse_list,
        "relapses": relapse_list,
        "total_misconceptions": open_count + improving_count + resolved_count
    }

@router.get("/rechecks/due")
async def workflow_due_rechecks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.routers.disguise import get_due_rechecks_endpoint
    return await get_due_rechecks_endpoint(db=db, current_user=current_user)


