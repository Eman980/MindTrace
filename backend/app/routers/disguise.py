"""
app/routers/disguise.py
-----------------------
Endpoints for Disguise Test Generation, Answer Evaluation, and Due Rechecks.
"""

import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.all_models import User, Misconception
from app.utils.security import get_current_user
from app.schemas.all_schemas import (
    DisguiseQuestionOut,
    DisguiseAnswerIn,
    DisguiseAnswerOut,
    RecheckDueItemOut
)
from app.services.disguise_service import generate_disguise_mcq
from app.mongo import (
    get_misconception_by_id,
    save_disguise_to_misconception,
    mark_misconception_resolved,
    mark_misconception_relapse,
    format_misconception_doc,
)

router = APIRouter(tags=["Disguise Test & Rechecks"])


# ── GET /rechecks/due ──────────────────────────────────────────────────────────

@router.get("/rechecks/due", response_model=List[RecheckDueItemOut])
async def get_due_rechecks_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns misconceptions where status = 'improving' and recheck_due <= today.
    Includes misconception ID, concept name, original question, dates, and relapse count.
    """
    today_iso = datetime.date.today().isoformat()
    today_date = datetime.date.today()
    results: List[dict] = []
    seen_ids = set()

    # 1. Fetch from MongoDB Atlas
    try:
        from app.mongo import get_due_rechecks_list
        mongo_items = await get_due_rechecks_list(student_id=current_user.id)
        for m in mongo_items:
            m_id = str(m.get("id"))
            if m_id not in seen_ids:
                seen_ids.add(m_id)
                results.append({
                    "id": m_id,
                    "misconception_id": m_id,
                    "concept_name": m.get("concept") or "Unknown Concept",
                    "concept": m.get("concept"),
                    "original_question": m.get("original_question"),
                    "improving_at": m.get("improving_at"),
                    "recheck_due": str(m.get("recheck_due")),
                    "relapse_count": int(m.get("relapse_count", 0)),
                    "status": "improving"
                })
    except Exception as e:
        print(f"[Rechecks] MongoDB due query warning: {e}")

    # 2. Fetch from SQLite
    try:
        sqlite_items = db.query(Misconception).filter(
            Misconception.user_id == current_user.id,
            Misconception.status == "improving",
            Misconception.recheck_due <= today_date
        ).all()

        for sm in sqlite_items:
            sm_id = str(sm.id)
            if sm_id not in seen_ids:
                seen_ids.add(sm_id)
                results.append({
                    "id": sm_id,
                    "misconception_id": sm_id,
                    "concept_name": sm.concept_name or sm.title,
                    "concept": sm.concept_name or sm.title,
                    "original_question": sm.title,
                    "improving_at": str(sm.improving_at) if sm.improving_at else None,
                    "recheck_due": str(sm.recheck_due) if sm.recheck_due else today_iso,
                    "relapse_count": int(getattr(sm, "relapse_count", 0) or 0),
                    "status": "improving"
                })
    except Exception as e:
        print(f"[Rechecks] SQLite query warning: {e}")

    return results


# ── POST /disguise/{misconception_id}/generate ────────────────────────────────

@router.post("/disguise/{misconception_id}/generate", response_model=DisguiseQuestionOut)
async def generate_disguise_test_endpoint(
    misconception_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates or reuses a Disguise Test MCQ for an 'improving' misconception
    whose recheck_due date is on or before today.
    Never exposes correct_index or explanation before submission.
    """
    # 1. Fetch misconception (from MongoDB first, fallback to SQLite if needed)
    misc_doc = await get_misconception_by_id(misconception_id)
    sqlite_misc = None
    if not misc_doc and (misconception_id.isdigit() or len(misconception_id) < 10):
        try:
            sqlite_misc = db.query(Misconception).filter(
                Misconception.id == int(misconception_id),
                Misconception.user_id == current_user.id
            ).first()
            if sqlite_misc:
                misc_doc = {
                    "id": str(sqlite_misc.id),
                    "concept": sqlite_misc.concept_name or sqlite_misc.title,
                    "original_question": sqlite_misc.title,
                    "status": sqlite_misc.status or "open",
                    "recheck_due": str(sqlite_misc.recheck_due) if sqlite_misc.recheck_due else None,
                    "relapse_count": getattr(sqlite_misc, "relapse_count", 0),
                    "disguise": None
                }
        except Exception:
            pass

    if not misc_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Misconception with id '{misconception_id}' not found."
        )

    # 2. Verify status is 'improving'
    current_status = (misc_doc.get("status") or "open").lower()
    if current_status != "improving":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disguise test is only available for misconceptions with status 'improving' (current status: '{current_status}')."
        )

    # 3. Verify recheck_due is on or before today
    today_iso = datetime.date.today().isoformat()
    recheck_due = misc_doc.get("recheck_due")
    if recheck_due and str(recheck_due) > today_iso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disguise test cannot be taken before recheck_due date ({recheck_due}). Today is {today_iso}."
        )

    # 4. Reuse existing disguise test if already generated
    existing_disguise = misc_doc.get("disguise")
    if existing_disguise and isinstance(existing_disguise, dict) and existing_disguise.get("question"):
        disguise = existing_disguise
    else:
        # Generate using Groq openai/gpt-oss-20b
        concept_title = misc_doc.get("concept") or "Fundamental Concept"
        orig_q = misc_doc.get("original_question") or f"Concept question about {concept_title}"
        disguise = await generate_disguise_mcq(concept=concept_title, original_question=orig_q)
        await save_disguise_to_misconception(misconception_id, disguise)

    # 5. Return question and options WITHOUT exposing the answer
    return {
        "misconception_id": str(misc_doc.get("id", misconception_id)),
        "concept": misc_doc.get("concept") or "",
        "status": "improving",
        "question": disguise["question"],
        "options": disguise["options"],
        "recheck_due": recheck_due,
        "message": "Disguise test generated successfully. Select the correct option to prove understanding."
    }


# ── POST /disguise/{misconception_id}/answer ──────────────────────────────────

@router.post("/disguise/{misconception_id}/answer", response_model=DisguiseAnswerOut)
async def submit_disguise_answer_endpoint(
    misconception_id: str,
    payload: DisguiseAnswerIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits student's answer to the Disguise Test:
    - Checks if student answer matches stored correct_index.
    - If correct -> status moves to 'resolved'.
    - If incorrect -> status moves back to 'open', and relapse_count increases by 1.
    - A student cannot resolve an 'open' misconception directly.
    - A student cannot take the disguise test before recheck_due.
    """
    # 1. Fetch misconception
    misc_doc = await get_misconception_by_id(misconception_id)
    sqlite_misc = None
    if not misc_doc and (misconception_id.isdigit() or len(misconception_id) < 10):
        try:
            sqlite_misc = db.query(Misconception).filter(
                Misconception.id == int(misconception_id),
                Misconception.user_id == current_user.id
            ).first()
            if sqlite_misc:
                misc_doc = {
                    "id": str(sqlite_misc.id),
                    "concept": sqlite_misc.concept_name or sqlite_misc.title,
                    "original_question": sqlite_misc.title,
                    "status": sqlite_misc.status or "open",
                    "recheck_due": str(sqlite_misc.recheck_due) if sqlite_misc.recheck_due else None,
                    "relapse_count": getattr(sqlite_misc, "relapse_count", 0),
                    "disguise": None
                }
        except Exception:
            pass

    if not misc_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Misconception with id '{misconception_id}' not found."
        )

    # 2. Verify eligibility: status must be 'improving'
    current_status = (misc_doc.get("status") or "open").lower()
    if current_status != "improving":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disguise test can only be submitted for misconceptions in 'improving' status (current: '{current_status}'). A student cannot resolve an open misconception directly."
        )

    # 3. Verify eligibility: date must be on or after recheck_due
    today_iso = datetime.date.today().isoformat()
    recheck_due = misc_doc.get("recheck_due")
    if recheck_due and str(recheck_due) > today_iso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disguise test cannot be submitted before recheck_due ({recheck_due}). Today is {today_iso}."
        )

    # 4. Check that disguise test was generated
    disguise = misc_doc.get("disguise")
    if not disguise or not isinstance(disguise, dict) or "correct_index" not in disguise:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disguise test has not been generated for this misconception yet. Call POST /disguise/{misconception_id}/generate first."
        )

    correct_idx = int(disguise.get("correct_index", 0))
    options = disguise.get("options", [])

    # 5. Determine student correctness
    submitted_idx = payload.selected_index
    if submitted_idx is None and payload.student_answer:
        clean = payload.student_answer.strip().upper()
        letter_map = {"A": 0, "B": 1, "C": 2, "D": 3}
        if clean and clean[0] in letter_map:
            submitted_idx = letter_map[clean[0]]
        else:
            for i, opt in enumerate(options):
                if clean in opt.upper():
                    submitted_idx = i
                    break

    if submitted_idx is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide 'selected_index' (0, 1, 2, or 3) or 'student_answer'."
        )

    is_correct = (submitted_idx == correct_idx)

    # 6. Apply state transition
    if is_correct:
        # Move to 'resolved'
        new_status = "resolved"
        await mark_misconception_resolved(misconception_id)
        if sqlite_misc:
            sqlite_misc.status = "Resolved"
            sqlite_misc.resolved_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
        message = "Passed! You answered the Disguise Test correctly. The misconception is now Resolved."
        relapse_count = int(misc_doc.get("relapse_count", 0))
    else:
        # Move to 'open' and increment relapse_count
        new_status = "open"
        updated = await mark_misconception_relapse(misconception_id)
        relapse_count = updated.get("relapse_count", int(misc_doc.get("relapse_count", 0)) + 1) if updated else (int(misc_doc.get("relapse_count", 0)) + 1)
        if sqlite_misc:
            sqlite_misc.status = "open"
            sqlite_misc.relapse_count = getattr(sqlite_misc, "relapse_count", 0) + 1
            sqlite_misc.resolved_at = None
            db.commit()
        message = "Incorrect answer on the Disguise Test. Status reverted to 'open' (first correct answer was memorized, not understood)."

    try:
        from app.mongo import record_misconception_attempt
        await record_misconception_attempt(
            misconception_id=str(misc_doc.get("id", misconception_id)),
            question=disguise.get("question", ""),
            student_answer=payload.student_answer or str(payload.selected_index),
            is_correct=is_correct,
            context_type="reassessment",
            explanation=disguise.get("explanation")
        )
    except Exception as e:
        print(f"[Disguise] Error persisting attempt: {e}")

    return {
        "misconception_id": str(misc_doc.get("id", misconception_id)),
        "concept": misc_doc.get("concept") or "",
        "is_correct": is_correct,
        "new_status": new_status,
        "correct_index": correct_idx,
        "explanation": disguise.get("explanation") or "",
        "relapse_count": relapse_count,
        "message": message
    }
