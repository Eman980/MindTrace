import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.all_models import (
    User, Lecture, Concept, Assessment, AssessmentAttempt, ConceptProgress, Misconception, utcnow
)
from app.routers.auth import get_current_user
from app.services.assessment_generation_service import assessment_generation_service
from app.services.evaluation_service import evaluation_service
from app.schemas.all_schemas import (
    AssessmentOut, AssessmentStartIn, AssessmentSaveIn, AssessmentSubmitIn,
    AssessmentResultOut, AssessmentStatusOut, AssessmentAttemptSummaryOut,
    AssessmentQuestionOut, AssessmentQuestionResultOut, RubricItemOut, RecommendedRevisionOut
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _sanitize_questions_for_taking(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Strips correct answers, explanations, and internal grading rubrics
    before the assessment is submitted, preventing early answer leakage.
    """
    sanitized = []
    for q in questions:
        sanitized.append({
            "id": q.get("id"),
            "type": q.get("type"),
            "difficulty": q.get("difficulty"),
            "question_text": q.get("question_text"),
            "options": q.get("options"),  # List of choices for MCQ
            "max_points": float(q.get("max_points", 5.0)),
            "concept_id": q.get("concept_id"),
            "concept_title": q.get("concept_title"),
            "source_timestamp": q.get("source_timestamp")
        })
    return sanitized


@router.get("/lecture/{lecture_id}/status", response_model=AssessmentStatusOut)
async def get_assessment_status(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns completion status across difficulties (Easy, Moderate, Hard),
    any active in-progress attempt (for seamless page refresh), and past attempt summaries.
    """
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    # Find all active/completed attempts by current user for this lecture (exclude abandoned)
    user_attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.lecture_id == lecture_id,
        AssessmentAttempt.user_id == current_user.id,
        AssessmentAttempt.status != "abandoned"
    ).order_by(AssessmentAttempt.started_at.desc()).all()

    completed_difficulties = list(set(
        att.difficulty.lower() for att in user_attempts if att.status == "submitted"
    ))

    # Check for active in-progress attempt
    in_progress = next((att for att in user_attempts if att.status == "in_progress"), None)
    in_prog_dict = None
    if in_progress:
        assessment = in_progress.assessment
        in_prog_dict = {
            "attempt_id": in_progress.id,
            "assessment_id": in_progress.assessment_id,
            "difficulty": in_progress.difficulty,
            "started_at": in_progress.started_at.isoformat() if in_progress.started_at else None,
            "saved_answers": in_progress.answers or {},
            "total_questions": len(assessment.questions) if assessment else 7
        }

    # Assign chronological attempt numbers per difficulty
    # Group submitted attempts by difficulty in ascending order of start time
    diff_counts: Dict[str, int] = {}
    attempts_sorted_asc = sorted(user_attempts, key=lambda a: a.started_at or utcnow())
    attempt_num_map: Dict[int, int] = {}
    for att in attempts_sorted_asc:
        d = att.difficulty.lower()
        diff_counts[d] = diff_counts.get(d, 0) + 1
        attempt_num_map[att.id] = diff_counts[d]

    attempts_summary = [
        AssessmentAttemptSummaryOut(
            id=att.id,
            attempt_number=attempt_num_map.get(att.id, 1),
            assessment_id=att.assessment_id,
            difficulty=att.difficulty,
            status=att.status,
            total_score=att.total_score,
            max_score=att.max_score,
            percentage=att.percentage,
            submitted_at=att.submitted_at,
            started_at=att.started_at
        )
        for att in user_attempts
    ]

    return AssessmentStatusOut(
        lecture_id=lecture_id,
        completed_difficulties=completed_difficulties,
        in_progress_attempt=in_prog_dict,
        attempts=attempts_summary
    )


@router.post("/start")
async def start_assessment(
    payload: AssessmentStartIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Starts an assessment at the chosen difficulty (Easy, Moderate, or Hard).
    If payload.retake is False and an in-progress attempt already exists, resumes it.
    If payload.retake is True, generates a fresh set of questions (avoiding previous questions)
    and starts a new attempt without overwriting previous attempts or misconception tracking.
    """
    difficulty = payload.difficulty.lower().strip()
    if difficulty not in ("easy", "moderate", "hard"):
        raise HTTPException(status_code=400, detail="Invalid difficulty. Choose 'easy', 'moderate', or 'hard'.")

    is_retake = bool(payload.retake)

    # 1. If not retaking, check for existing in-progress attempt for this lecture & difficulty to resume
    if not is_retake:
        existing_attempt = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.lecture_id == payload.lecture_id,
            AssessmentAttempt.user_id == current_user.id,
            AssessmentAttempt.difficulty == difficulty,
            AssessmentAttempt.status == "in_progress"
        ).first()

        if existing_attempt:
            assessment = existing_attempt.assessment
            sanitized_questions = _sanitize_questions_for_taking(assessment.questions)
            # Count chronological attempt number
            prior_count = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.lecture_id == payload.lecture_id,
                AssessmentAttempt.user_id == current_user.id,
                AssessmentAttempt.difficulty == difficulty,
                AssessmentAttempt.status == "submitted"
            ).count()

            return {
                "attempt_id": existing_attempt.id,
                "attempt_number": prior_count + 1,
                "resumed": True,
                "assessment": {
                    "id": assessment.id,
                    "lecture_id": assessment.lecture_id,
                    "difficulty": assessment.difficulty,
                    "title": assessment.title,
                    "description": assessment.description,
                    "total_questions": len(sanitized_questions),
                    "mcq_count": 4,
                    "short_answer_count": 3,
                    "max_score": 35.0,
                    "questions": sanitized_questions
                },
                "in_progress_answers": existing_attempt.answers or {}
            }
    else:
        # If retaking, mark any stale in-progress attempt as abandoned so its record is preserved
        in_prog_atts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.lecture_id == payload.lecture_id,
            AssessmentAttempt.user_id == current_user.id,
            AssessmentAttempt.difficulty == difficulty,
            AssessmentAttempt.status == "in_progress"
        ).all()
        for ip in in_prog_atts:
            ip.status = "abandoned"
        db.commit()

    # 2. Get or create the Assessment (force_fresh=True on retake generates non-repeating questions)
    assessment = await assessment_generation_service.get_or_create_assessment(
        db=db,
        lecture_id=payload.lecture_id,
        difficulty=difficulty,
        force_fresh=is_retake
    )

    # 3. Calculate fresh attempt number (excluding abandoned)
    submitted_prior_count = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.lecture_id == payload.lecture_id,
        AssessmentAttempt.user_id == current_user.id,
        AssessmentAttempt.difficulty == difficulty,
        AssessmentAttempt.status != "abandoned"
    ).count()
    attempt_num = submitted_prior_count + 1

    # 4. Create a new attempt record
    new_attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        user_id=current_user.id,
        lecture_id=payload.lecture_id,
        difficulty=difficulty,
        status="in_progress",
        answers={},
        total_score=0.0,
        max_score=35.0,
        percentage=0.0,
        mcq_correct_count=0,
        mcq_total_count=4,
        short_score=0.0,
        short_max_score=15.0
    )
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)

    sanitized_questions = _sanitize_questions_for_taking(assessment.questions)

    return {
        "attempt_id": new_attempt.id,
        "attempt_number": attempt_num,
        "resumed": False,
        "assessment": {
            "id": assessment.id,
            "lecture_id": assessment.lecture_id,
            "difficulty": assessment.difficulty,
            "title": assessment.title,
            "description": assessment.description,
            "total_questions": len(sanitized_questions),
            "mcq_count": 4,
            "short_answer_count": 3,
            "max_score": 35.0,
            "questions": sanitized_questions
        },
        "in_progress_answers": {}
    }


@router.post("/retake")
async def retake_assessment(
    payload: AssessmentStartIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Explicit endpoint to retake an assessment at the same difficulty level:
    - Generates a fresh set of questions avoiding previous questions.
    - Preserves previous attempts and results in the database.
    - Creates a new attempt record and returns the new sanitized questions.
    """
    payload = payload.model_copy(update={'retake': True})
    return await start_assessment(payload=payload, db=db, current_user=current_user)


@router.post("/{attempt_id}/save")
async def save_assessment_progress(
    attempt_id: int,
    payload: AssessmentSaveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Saves in-progress answers so refreshing the page or navigating away does not lose work.
    """
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.user_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found.")

    if attempt.status != "in_progress":
        return {"status": "already_submitted", "message": "This attempt has already been submitted."}

    # Merge / update answers
    current_answers = attempt.answers or {}
    current_answers.update(payload.answers)
    attempt.answers = current_answers
    db.commit()

    return {
        "status": "saved",
        "saved_count": len(current_answers)
    }


@router.post("/{attempt_id}/submit", response_model=AssessmentResultOut)
async def submit_assessment(
    attempt_id: int,
    payload: AssessmentSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits the assessment attempt:
    - Evaluates all 4 MCQs (reveals explanations and marks).
    - Evaluates all 3 Short Answers using the transparent rubric evaluator (Feature 1).
    - Awards partial marks (PARTIAL ANSWERS NEVER RECEIVE 0 POINTS).
    - Calculates total score, percentage, MCQ breakdown, and Short Answer breakdown.
    - Generates personalized feedback: concepts understood, concepts needing improvement, and timestamped revision links.
    - Updates misconception tracking signals and concept progress.
    - Marks attempt as submitted and persists all results.
    """
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.user_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found.")

    # Update latest answers from payload
    merged_answers = attempt.answers or {}
    merged_answers.update(payload.answers)
    attempt.answers = merged_answers

    assessment = attempt.assessment
    if not assessment:
        raise HTTPException(status_code=404, detail="Underlying assessment not found.")

    questions = assessment.questions or []
    question_results: List[AssessmentQuestionResultOut] = []

    total_score = 0.0
    max_score = 0.0
    mcq_correct = 0
    mcq_total = 0
    short_score = 0.0
    short_max = 0.0

    concept_performance: Dict[str, Dict[str, Any]] = {}

    for q in questions:
        q_id = q.get("id")
        q_type = q.get("type", "mcq")
        q_diff = q.get("difficulty", attempt.difficulty)
        q_text = q.get("question_text", "")
        corr_ans = q.get("correct_answer", "")
        expl = q.get("explanation", "")
        q_max_pts = float(q.get("max_points", 5.0))
        c_id = q.get("concept_id")
        c_title = q.get("concept_title") or "General Topic"
        c_ts = float(q.get("source_timestamp") or 0.0)

        student_ans = str(merged_answers.get(q_id, "")).strip()

        if c_title not in concept_performance:
            concept_performance[c_title] = {
                "concept_id": c_id,
                "timestamp": c_ts,
                "earned": 0.0,
                "possible": 0.0
            }

        if q_type == "mcq":
            mcq_total += 1
            # Check MCQ correctness
            # Strip prefix letter like "A. " or "A)" or just compare
            stud_clean = student_ans.strip()
            corr_clean = corr_ans.strip()

            is_correct = False
            if stud_clean:
                # Direct match
                if stud_clean.lower() == corr_clean.lower():
                    is_correct = True
                # Match by letter prefix (e.g. "B" vs "B. ...")
                elif len(stud_clean) == 1 and corr_clean.upper().startswith(stud_clean.upper()):
                    is_correct = True
                elif len(corr_clean) == 1 and stud_clean.upper().startswith(corr_clean.upper()):
                    is_correct = True
                elif len(stud_clean) >= 2 and stud_clean[:2].upper() == corr_clean[:2].upper():
                    is_correct = True

            awarded = q_max_pts if is_correct else 0.0
            verdict = "correct" if is_correct else "incorrect"
            if is_correct:
                mcq_correct += 1
                feedback_text = f"Correct! {expl}".strip()
            else:
                feedback_text = f"Incorrect. The correct answer is: {corr_ans}. {expl}".strip()

            total_score += awarded
            max_score += q_max_pts
            concept_performance[c_title]["earned"] += awarded
            concept_performance[c_title]["possible"] += q_max_pts

            # Misconception Signal Integration for MCQ
            if not is_correct and c_id:
                try:
                    # Register a misconception signal on this concept
                    existing_m = db.query(Misconception).filter(
                        Misconception.user_id == current_user.id,
                        Misconception.concept_id == c_id
                    ).first()
                    if existing_m and (existing_m.status or "").lower() != "resolved":
                        existing_m.occurrence_count = (existing_m.occurrence_count or 1) + 1
                    elif not existing_m:
                        new_m = Misconception(
                            user_id=current_user.id,
                            concept_id=c_id,
                            concept_name=c_title,
                            title=f"Assessment error in {c_title}",
                            summary=f"Student answered '{student_ans}' instead of '{corr_ans}' in {q_diff} assessment.",
                            severity_level="Medium",
                            severity_score=2,
                            status="open",
                            occurrence_count=1
                        )
                        db.add(new_m)
                    db.commit()
                except Exception as ex:
                    print(f"[AssessmentSubmit] Error recording MCQ misconception: {ex}")

            question_results.append(AssessmentQuestionResultOut(
                question_id=q_id,
                question_text=q_text,
                type="mcq",
                difficulty=q_diff,
                student_answer=student_ans if student_ans else "(No answer provided)",
                correct_answer=corr_ans,
                explanation=expl,
                is_correct=is_correct,
                verdict=verdict,
                score=awarded,
                max_score=q_max_pts,
                percentage=round((awarded / q_max_pts) * 100, 1),
                feedback=feedback_text,
                rubric_breakdown=None,
                what_understood="Selected the correct answer." if is_correct else None,
                what_missing=None if is_correct else f"Correct principle: {corr_ans}",
                what_needs_correction=None if is_correct else "Selected an incorrect option.",
                how_to_improve=None if is_correct else f"Review {c_title} at timestamp {c_ts:.0f}s.",
                concept_id=c_id,
                concept_title=c_title,
                remediation_timestamp=c_ts
            ))

        else:
            # Short Answer Question Evaluation (Feature 1: Rubric-Based Semantic Evaluator)
            short_max += q_max_pts
            eval_out = await evaluation_service.evaluate_short_answer_rubric(
                question_text=q_text,
                correct_answer=corr_ans,
                student_answer=student_ans,
                explanation=expl,
                rubric=q.get("rubric"),
                max_points=q_max_pts,
                target_misconception=None
            )

            awarded = float(eval_out.get("score", 0.0))
            is_corr = bool(eval_out.get("correct", False))
            v_dict = str(eval_out.get("verdict", "incorrect"))

            # Safety guarantee: Partial answers MUST receive > 0 points
            if v_dict == "partial" and awarded <= 0.0:
                awarded = max(1.0, round(q_max_pts * 0.5, 1))

            # Build rubric breakdown items with guaranteed point consistency
            raw_rubric = eval_out.get("rubric_breakdown") or []
            rubric_items: List[RubricItemOut] = []

            for r in raw_rubric:
                c_crit = str(r.get("criterion", "Criterion")).strip()
                c_status = str(r.get("status", "missing")).lower().strip()
                c_pts = float(r.get("points_awarded") if r.get("points_awarded") is not None else (r.get("points") or r.get("score") or 0.0))
                c_max = float(r.get("max_points") if r.get("max_points") is not None else (r.get("points_possible") or r.get("max_score") or 0.0))
                c_notes = r.get("notes") or r.get("comment") or r.get("reason") or None

                rubric_items.append(RubricItemOut(
                    criterion=c_crit,
                    status=c_status,
                    points_awarded=max(0.0, c_pts),
                    max_points=max(0.0, c_max),
                    notes=c_notes
                ))

            # If no rubric items or total max is 0, generate from question rubric or standard criteria
            total_rubric_max = sum(ri.max_points for ri in rubric_items)
            if not rubric_items or total_rubric_max <= 0:
                q_rubric = q.get("rubric") or []
                rubric_items = []
                if q_rubric:
                    for r in q_rubric:
                        c_max = float(r.get("max_points") or r.get("points_possible") or 2.5)
                        alloc_pts = min(c_max, round((awarded / q_max_pts) * c_max, 1)) if q_max_pts > 0 else 0.0
                        rubric_items.append(RubricItemOut(
                            criterion=r.get("criterion", "Criterion"),
                            status="correct" if alloc_pts >= c_max else ("partial" if alloc_pts > 0 else "missing"),
                            points_awarded=alloc_pts,
                            max_points=c_max,
                            notes=None
                        ))
                else:
                    half = round(q_max_pts * 0.5, 1)
                    rubric_items = [
                        RubricItemOut(
                            criterion="Core conceptual understanding",
                            status="correct" if awarded >= half else ("partial" if awarded > 0 else "missing"),
                            points_awarded=min(half, round(awarded * 0.5, 1)),
                            max_points=half,
                            notes=None
                        ),
                        RubricItemOut(
                            criterion="Explanation & supporting reasoning",
                            status="correct" if awarded >= q_max_pts else ("partial" if awarded > half else "missing"),
                            points_awarded=min(round(q_max_pts - half, 1), max(0.0, round(awarded - round(awarded * 0.5, 1), 1))),
                            max_points=round(q_max_pts - half, 1),
                            notes=None
                        )
                    ]

            # Re-normalize criteria max_points sum to strictly match q_max_pts (e.g. 5.0)
            total_rubric_max = sum(ri.max_points for ri in rubric_items)
            if abs(total_rubric_max - q_max_pts) > 0.05 and total_rubric_max > 0:
                running_max = 0.0
                for ri in rubric_items[:-1]:
                    ri.max_points = round((ri.max_points / total_rubric_max) * q_max_pts, 1)
                    running_max += ri.max_points
                rubric_items[-1].max_points = round(q_max_pts - running_max, 1)

            # Re-normalize criteria points_awarded sum to strictly match awarded score
            total_rubric_awarded = sum(ri.points_awarded for ri in rubric_items)
            if abs(total_rubric_awarded - awarded) > 0.05:
                if total_rubric_awarded > 0:
                    running_awarded = 0.0
                    for ri in rubric_items[:-1]:
                        ri.points_awarded = min(ri.max_points, round((ri.points_awarded / total_rubric_awarded) * awarded, 1))
                        running_awarded += ri.points_awarded
                    rubric_items[-1].points_awarded = min(rubric_items[-1].max_points, max(0.0, round(awarded - running_awarded, 1)))
                else:
                    rem = awarded
                    for ri in rubric_items:
                        alloc = min(ri.max_points, rem)
                        ri.points_awarded = alloc
                        rem -= alloc

            # Question score is derived strictly from sum of rubric points
            awarded = round(sum(ri.points_awarded for ri in rubric_items), 1)

            # Update statuses based on points
            for ri in rubric_items:
                if ri.points_awarded >= ri.max_points and ri.max_points > 0:
                    ri.status = "correct"
                elif ri.points_awarded > 0:
                    ri.status = "partial"
                elif ri.status not in ("incorrect", "missing"):
                    ri.status = "missing"

            total_score += awarded
            short_score += awarded
            max_score += q_max_pts
            concept_performance[c_title]["earned"] += awarded
            concept_performance[c_title]["possible"] += q_max_pts

            # Misconception Signal Integration for Short Answer
            if v_dict in ("partial", "incorrect") and c_id:
                try:
                    existing_m = db.query(Misconception).filter(
                        Misconception.user_id == current_user.id,
                        Misconception.concept_id == c_id,
                        Misconception.lecture_id == attempt.lecture_id
                    ).first()
                    if existing_m and (existing_m.status or "").lower() != "resolved":
                        existing_m.occurrence_count = (existing_m.occurrence_count or 1) + 1
                    elif not existing_m:
                        new_m = Misconception(
                            user_id=current_user.id,
                            lecture_id=attempt.lecture_id,
                            concept_id=c_id,
                            concept_name=c_title,
                            title=f"Incomplete explanation in {c_title}",
                            summary=eval_out.get("what_missing") or f"Partial understanding in {q_diff} assessment.",
                            severity_level="Low" if v_dict == "partial" else "Medium",
                            severity_score=1 if v_dict == "partial" else 2,
                            status="open",
                            occurrence_count=1
                        )
                        db.add(new_m)
                    db.commit()
                except Exception as ex:
                    print(f"[AssessmentSubmit] Error recording Short Answer misconception: {ex}")

            question_results.append(AssessmentQuestionResultOut(
                question_id=q_id,
                question_text=q_text,
                type="short_answer",
                difficulty=q_diff,
                student_answer=student_ans if student_ans else "(No answer provided)",
                correct_answer=corr_ans,
                explanation=expl,
                is_correct=is_corr,
                verdict=v_dict,
                score=awarded,
                max_score=q_max_pts,
                percentage=round((awarded / q_max_pts) * 100, 1),
                feedback=eval_out.get("feedback", ""),
                rubric_breakdown=rubric_items,
                what_understood=eval_out.get("what_understood"),
                what_missing=eval_out.get("what_missing"),
                what_needs_correction=eval_out.get("what_needs_correction"),
                how_to_improve=eval_out.get("how_to_improve"),
                concept_id=c_id,
                concept_title=c_title,
                remediation_timestamp=c_ts
            ))

    # Score consistency verification: ensure MCQ + short equals total
    mcq_score_sum = sum(qr.score for qr in question_results if qr.type == "mcq")
    short_score_sum = sum(qr.score for qr in question_results if qr.type == "short_answer")
    total_score = round(mcq_score_sum + short_score_sum, 1)
    short_score = round(short_score_sum, 1)

    mcq_max_sum = sum(qr.max_score for qr in question_results if qr.type == "mcq")
    short_max_sum = sum(qr.max_score for qr in question_results if qr.type == "short_answer")
    max_score = round(mcq_max_sum + short_max_sum, 1)
    short_max = round(short_max_sum, 1)

    pct = round((total_score / max_score) * 100, 1) if max_score > 0 else 0.0

    # Concepts Understood vs Partially Understood vs Needing Improvement
    concepts_understood: List[str] = []
    concepts_partially_understood: List[str] = []
    concepts_needing_improvement: List[str] = []
    recommended_revision: List[RecommendedRevisionOut] = []

    for title, perf in concept_performance.items():
        possible = perf["possible"]
        earned = perf["earned"]
        c_pct = (earned / possible) if possible > 0 else 0.0

        if c_pct >= 0.70:
            concepts_understood.append(title)
        elif c_pct >= 0.35:
            concepts_partially_understood.append(title)
            recommended_revision.append(RecommendedRevisionOut(
                concept_id=perf["concept_id"],
                concept_title=title,
                timestamp=perf["timestamp"],
                reason=f"Demonstrated partial understanding ({earned:.1f}/{possible:.1f} pts, {round(c_pct*100)}%). Review this section to master core mechanics."
            ))
        else:
            concepts_needing_improvement.append(title)
            recommended_revision.append(RecommendedRevisionOut(
                concept_id=perf["concept_id"],
                concept_title=title,
                timestamp=perf["timestamp"],
                reason=f"Needs improvement ({earned:.1f}/{possible:.1f} pts, {round(c_pct*100)}%). Review core principles at this timestamp."
            ))

    # Update ConceptProgress records in DB
    for title, perf in concept_performance.items():
        c_id = perf["concept_id"]
        if not c_id:
            continue
        try:
            prog = db.query(ConceptProgress).filter(
                ConceptProgress.user_id == current_user.id,
                ConceptProgress.concept_id == c_id
            ).first()
            if prog:
                possible = perf["possible"]
                earned = perf["earned"]
                c_pct = int(round((earned / possible) * 100)) if possible > 0 else 0
                prog.understanding_percentage = max(prog.understanding_percentage, c_pct)
                if prog.understanding_percentage >= 80:
                    prog.status = "Mastered"
                elif prog.understanding_percentage > 0:
                    prog.status = "In Progress"
                db.commit()
        except Exception as ex:
            print(f"[AssessmentSubmit] Error updating ConceptProgress: {ex}")

    # Persist attempt completion
    attempt.status = "submitted"
    attempt.submitted_at = utcnow()
    attempt.total_score = total_score
    attempt.max_score = max_score
    attempt.percentage = pct
    attempt.mcq_correct_count = mcq_correct
    attempt.mcq_total_count = mcq_total
    attempt.short_score = short_score
    attempt.short_max_score = short_max
    attempt.results = [qr.model_dump() for qr in question_results]
    attempt.feedback_summary = {
        "concepts_understood": concepts_understood,
        "concepts_partially_understood": concepts_partially_understood,
        "concepts_needing_improvement": concepts_needing_improvement,
        "recommended_revision": [r.model_dump() for r in recommended_revision]
    }
    db.commit()
    db.refresh(attempt)

    # Determine attempt number for this attempt (chronological among non-abandoned)
    attempt_num = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.lecture_id == attempt.lecture_id,
        AssessmentAttempt.user_id == current_user.id,
        AssessmentAttempt.difficulty == attempt.difficulty,
        AssessmentAttempt.status != "abandoned",
        AssessmentAttempt.id <= attempt.id
    ).count()

    return AssessmentResultOut(
        attempt_id=attempt.id,
        attempt_number=max(1, attempt_num),
        assessment_id=assessment.id,
        lecture_id=assessment.lecture_id,
        difficulty=attempt.difficulty,
        status="submitted",
        total_score=total_score,
        max_score=max_score,
        percentage=pct,
        mcq_correct_count=mcq_correct,
        mcq_total_count=mcq_total,
        short_score=short_score,
        short_max_score=short_max,
        question_results=question_results,
        concepts_understood=concepts_understood,
        concepts_partially_understood=concepts_partially_understood,
        concepts_needing_improvement=concepts_needing_improvement,
        recommended_revision=recommended_revision,
        submitted_at=attempt.submitted_at
    )


@router.get("/attempt/{attempt_id}", response_model=AssessmentResultOut)
async def get_assessment_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches completed assessment results with detailed rubric breakdown.
    """
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.user_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found.")

    if attempt.status != "submitted":
        raise HTTPException(status_code=400, detail="This attempt is still in progress.")

    results_data = attempt.results or []
    question_results = [AssessmentQuestionResultOut(**r) for r in results_data]

    summary = attempt.feedback_summary or {}
    revision_data = summary.get("recommended_revision", [])
    recommended_revision = [RecommendedRevisionOut(**r) for r in revision_data]

    attempt_num = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.lecture_id == attempt.lecture_id,
        AssessmentAttempt.user_id == current_user.id,
        AssessmentAttempt.difficulty == attempt.difficulty,
        AssessmentAttempt.status != "abandoned",
        AssessmentAttempt.id <= attempt.id
    ).count()

    return AssessmentResultOut(
        attempt_id=attempt.id,
        attempt_number=max(1, attempt_num),
        assessment_id=attempt.assessment_id,
        lecture_id=attempt.lecture_id,
        difficulty=attempt.difficulty,
        status=attempt.status,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        mcq_correct_count=attempt.mcq_correct_count,
        mcq_total_count=attempt.mcq_total_count,
        short_score=attempt.short_score,
        short_max_score=attempt.short_max_score,
        question_results=question_results,
        concepts_understood=summary.get("concepts_understood", []),
        concepts_partially_understood=summary.get("concepts_partially_understood", []),
        concepts_needing_improvement=summary.get("concepts_needing_improvement", []),
        recommended_revision=recommended_revision,
        submitted_at=attempt.submitted_at
    )
