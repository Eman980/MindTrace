from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.all_models import (
    Concept, Lecture, Checkpoint, CheckpointAttempt, Misconception, User
)
from app.utils.security import get_current_user
from app.canonical import CanonicalConcept, CanonicalConceptLink, sync_links

router = APIRouter(prefix="/canonical", tags=["Canonical"])


def get_status(attempted: int, pct: int, open_count: int) -> str:
    if attempted == 0:
        return "Not Started"
    if pct >= 80 and open_count == 0:
        return "Mastered"
    if pct < 50:
        return "Needs Attention"
    return "Improving"


@router.get("/progress")
def concept_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sync_links(db, current_user.id)

    rows = (
        db.query(CanonicalConcept, Concept, Lecture)
        .join(CanonicalConceptLink, CanonicalConceptLink.canonical_id == CanonicalConcept.id)
        .join(Concept, Concept.id == CanonicalConceptLink.concept_id)
        .join(Lecture, Lecture.id == Concept.lecture_id)
        .filter(CanonicalConcept.user_id == current_user.id)
        .order_by(CanonicalConcept.name, Lecture.created_at, Concept.order_index)
        .all()
    )
    if not rows:
        return []

    concept_ids = [c.id for _, c, _ in rows]

    # Latest attempt per checkpoint
    attempts = (
        db.query(Checkpoint.concept_id, CheckpointAttempt.checkpoint_id, CheckpointAttempt.is_correct)
        .join(CheckpointAttempt, CheckpointAttempt.checkpoint_id == Checkpoint.id)
        .filter(
            CheckpointAttempt.user_id == current_user.id,
            Checkpoint.concept_id.in_(concept_ids),
        )
        .order_by(CheckpointAttempt.created_at, CheckpointAttempt.id)
        .all()
    )
    latest = {}
    for concept_id, checkpoint_id, is_correct in attempts:
        latest[checkpoint_id] = (concept_id, bool(is_correct))

    per_concept = defaultdict(lambda: [0, 0])  # concept_id -> [attempted, correct]
    for concept_id, ok in latest.values():
        per_concept[concept_id][0] += 1
        if ok:
            per_concept[concept_id][1] += 1

    # Open misconceptions per concept
    open_misc = defaultdict(int)
    misconceptions = (
        db.query(Misconception)
        .filter(
            Misconception.user_id == current_user.id,
            Misconception.concept_id.in_(concept_ids),
            (Misconception.is_archived == False) | (Misconception.is_archived.is_(None)),
        )
        .all()
    )
    for m in misconceptions:
        if m.concept_id and (m.status or "").lower() != "resolved":
            open_misc[m.concept_id] += 1

    # Group by canonical concept
    groups = {}
    for canon, concept, lecture in rows:
        g = groups.setdefault(canon.id, {
            "id": canon.id,
            "name": canon.name,
            "questions_attempted": 0,
            "questions_correct": 0,
            "open_misconceptions": 0,
            "videos": [],
        })
        attempted, correct = per_concept[concept.id]
        opened = open_misc[concept.id]

        g["questions_attempted"] += attempted
        g["questions_correct"] += correct
        g["open_misconceptions"] += opened
        g["videos"].append({
            "lecture_id": lecture.id,
            "lecture_title": lecture.title,
            "concept_id": concept.id,
            "start_time": concept.start_time,
            "end_time": concept.end_time,
            "questions_attempted": attempted,
            "questions_correct": correct,
        })

    result = []
    for g in groups.values():
        attempted = g["questions_attempted"]
        pct = round(g["questions_correct"] * 100 / attempted) if attempted else 0
        g["understanding_percentage"] = pct
        g["status"] = get_status(attempted, pct, g["open_misconceptions"])
        result.append(g)

    order = {"Needs Attention": 0, "Improving": 1, "Not Started": 2, "Mastered": 3}
    result.sort(key=lambda x: (order.get(x["status"], 9), x["name"]))
    return result