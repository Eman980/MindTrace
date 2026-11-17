"""
Concept-based views for MindTrace.

  GET /insights/lectures/{lecture_id}/misconceptions   only THIS lecture, grouped by concept
  GET /insights/concepts/{canonical_id}/history        one concept across ALL videos
  GET /insights/progress                               progress grouped by concept, with video names

Read-only: nothing here changes existing data (it only links unlinked concepts).
"""
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
# If this import fails, copy the "get_current_user" import line from routers/misconceptions.py
from app.routers.auth import get_current_user
from app.models.all_models import (
    Lecture,
    Concept,
    Checkpoint,
    CheckpointAttempt,
    Misconception,
    MisconceptionEvidence,
)
from app.models.concept_groups import CanonicalConcept, CanonicalConceptLink
from app.services.concept_group_service import link_unlinked_concepts

router = APIRouter(prefix="/insights", tags=["insights"])

# Newer attempts count more: weight = MASTERY_DECAY ** (how many attempts ago)
MASTERY_DECAY = 0.8
SEVERITY_RANK = {"High": 3, "Medium": 2, "Low": 1}
STATUS_ORDER = {"needs_attention": 0, "improving": 1, "resolved": 2, "no_issue": 3, "not_started": 4}


# ----------------------------------------------------------------- helpers
def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def rollup_status(statuses: List[Optional[str]]) -> str:
    s = {x for x in statuses if x}
    if not s:
        return "none"
    if s & {"open", "relapse"}:
        return "needs_attention"
    if "improving" in s:
        return "improving"
    if s <= {"resolved"}:
        return "resolved"
    return "needs_attention"


def compute_mastery(results_newest_first: List[bool]) -> Optional[int]:
    """Recency-weighted accuracy, 0-100. None when the student has no attempts yet."""
    if not results_newest_first:
        return None
    weight, total, got = 1.0, 0.0, 0.0
    for ok in results_newest_first:
        total += weight
        if ok:
            got += weight
        weight *= MASTERY_DECAY
    return round(100 * got / total)


def _evidence_dict(e: MisconceptionEvidence) -> dict:
    return {
        "signal_type": e.signal_type,
        "evidence_text": e.evidence_text,
        "points_added": e.points_added,
        "created_at": _iso(e.created_at),
    }


def _evidence_by_misconception(db: Session, misconception_ids: List[int]) -> Dict[int, List[MisconceptionEvidence]]:
    out: Dict[int, List[MisconceptionEvidence]] = defaultdict(list)
    if not misconception_ids:
        return out
    rows = (
        db.query(MisconceptionEvidence)
        .filter(MisconceptionEvidence.misconception_id.in_(misconception_ids))
        .order_by(MisconceptionEvidence.created_at.desc(), MisconceptionEvidence.id.desc())
        .all()
    )
    for e in rows:
        out[e.misconception_id].append(e)
    return out


# --------------------------------------------- 1. this lecture's misconceptions
@router.get("/lectures/{lecture_id}/misconceptions")
def lecture_misconceptions(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user.id
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == uid).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    link_unlinked_concepts(db, uid)

    miscs = (
        db.query(Misconception)
        .filter(Misconception.user_id == uid, Misconception.lecture_id == lecture_id)
        .all()
    )
    if not miscs:
        return {
            "lecture_id": lecture.id,
            "lecture_title": lecture.title,
            "total": 0,
            "unresolved_count": 0,
            "groups": [],
        }

    concept_ids = list({m.concept_id for m in miscs if m.concept_id})
    concepts = {c.id: c for c in db.query(Concept).filter(Concept.id.in_(concept_ids)).all()}

    canon_by_concept: Dict[int, CanonicalConcept] = {}
    for link, canon in (
        db.query(CanonicalConceptLink, CanonicalConcept)
        .join(CanonicalConcept, CanonicalConcept.id == CanonicalConceptLink.canonical_concept_id)
        .filter(CanonicalConceptLink.concept_id.in_(concept_ids))
        .all()
    ):
        canon_by_concept[link.concept_id] = canon

    # Other videos where the same concept also caused trouble
    canon_ids = list({c.id for c in canon_by_concept.values()})
    also_seen: Dict[int, List[dict]] = defaultdict(list)
    if canon_ids:
        other_rows = (
            db.query(CanonicalConceptLink.canonical_concept_id, Misconception.lecture_id, Lecture.title)
            .join(Misconception, Misconception.concept_id == CanonicalConceptLink.concept_id)
            .join(Lecture, Lecture.id == Misconception.lecture_id)
            .filter(
                Misconception.user_id == uid,
                Misconception.lecture_id != lecture_id,
                CanonicalConceptLink.canonical_concept_id.in_(canon_ids),
            )
            .distinct()
            .all()
        )
        for canon_id, other_lecture_id, title in other_rows:
            also_seen[canon_id].append({"lecture_id": other_lecture_id, "title": title})

    evidence = _evidence_by_misconception(db, [m.id for m in miscs])

    groups: Dict[object, dict] = {}
    for m in miscs:
        canon = canon_by_concept.get(m.concept_id)
        key = canon.id if canon else ("concept", m.concept_id)
        concept = concepts.get(m.concept_id)
        group = groups.get(key)
        if group is None:
            group = {
                "canonical_concept_id": canon.id if canon else None,
                "concept_name": canon.name if canon else m.concept_name,
                "concept_id": m.concept_id,
                "concept_start_time": concept.start_time if concept else None,
                "also_seen_in": also_seen.get(canon.id, []) if canon else [],
                "misconceptions": [],
            }
            groups[key] = group

        evs = evidence.get(m.id, [])
        latest = evs[0] if evs else None
        group["misconceptions"].append(
            {
                "id": m.id,
                "title": m.title,
                "summary": m.summary,
                # The NEWEST evidence from this lecture (fixes the stale "why it was detected")
                "why_detected": latest.evidence_text if latest else (m.summary or ""),
                "why_detected_at": _iso(latest.created_at if latest else m.last_detected),
                "signal_type": latest.signal_type if latest else None,
                "status": m.status,
                "evidence_status": m.evidence_status,
                "severity_level": m.severity_level,
                "severity_score": m.severity_score,
                "occurrence_count": m.occurrence_count,
                "first_detected": _iso(m.first_detected),
                "last_detected": _iso(m.last_detected),
                "evidence": [_evidence_dict(e) for e in evs[:20]],
            }
        )

    out_groups = []
    for group in groups.values():
        items = group["misconceptions"]
        group["status"] = rollup_status([i["status"] for i in items])
        group["severity_level"] = max(
            (i["severity_level"] for i in items), key=lambda s: SEVERITY_RANK.get(s, 0), default=None
        )
        out_groups.append(group)

    out_groups.sort(
        key=lambda g: (STATUS_ORDER.get(g["status"], 9), -SEVERITY_RANK.get(g["severity_level"], 0), g["concept_name"])
    )

    unresolved = sum(1 for m in miscs if m.status != "resolved")
    return {
        "lecture_id": lecture.id,
        "lecture_title": lecture.title,
        "total": len(miscs),
        "unresolved_count": unresolved,
        "groups": out_groups,
    }


# --------------------------------------------- 2. one concept across all videos
@router.get("/concepts/{canonical_id}/history")
def concept_history(
    canonical_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user.id
    link_unlinked_concepts(db, uid)

    canon = (
        db.query(CanonicalConcept)
        .filter(CanonicalConcept.id == canonical_id, CanonicalConcept.user_id == uid)
        .first()
    )
    if not canon:
        raise HTTPException(status_code=404, detail="Concept not found")

    links = db.query(CanonicalConceptLink).filter(CanonicalConceptLink.canonical_concept_id == canon.id).all()
    concept_ids = [l.concept_id for l in links]
    lecture_ids = list({l.lecture_id for l in links})

    lectures = {
        l.id: l
        for l in db.query(Lecture).filter(Lecture.id.in_(lecture_ids), Lecture.user_id == uid).all()
    } if lecture_ids else {}
    concepts = {c.id: c for c in db.query(Concept).filter(Concept.id.in_(concept_ids)).all()} if concept_ids else {}

    miscs = (
        db.query(Misconception)
        .filter(Misconception.user_id == uid, Misconception.concept_id.in_(concept_ids))
        .all()
    ) if concept_ids else []
    evidence = _evidence_by_misconception(db, [m.id for m in miscs])

    attempt_rows = (
        db.query(CheckpointAttempt, Checkpoint)
        .join(Checkpoint, Checkpoint.id == CheckpointAttempt.checkpoint_id)
        .filter(CheckpointAttempt.user_id == uid, Checkpoint.concept_id.in_(concept_ids))
        .order_by(CheckpointAttempt.created_at.asc(), CheckpointAttempt.id.asc())
        .all()
    ) if concept_ids else []

    attempts_by_concept: Dict[int, List[dict]] = defaultdict(list)
    all_results_newest_first: List[bool] = []
    for att, chk in attempt_rows:
        attempts_by_concept[chk.concept_id].append(
            {
                "checkpoint_id": chk.id,
                "question_text": (chk.question_text or "")[:300],
                "student_answer": att.student_answer,
                "is_correct": att.is_correct,
                "grade": att.grade,
                "attempt_number": att.attempt_number,
                "created_at": _iso(att.created_at),
            }
        )
        all_results_newest_first.insert(0, bool(att.is_correct))

    miscs_by_concept: Dict[int, List[Misconception]] = defaultdict(list)
    for m in miscs:
        miscs_by_concept[m.concept_id].append(m)

    videos = []
    for link in links:
        lec = lectures.get(link.lecture_id)
        if lec is None:
            continue
        concept = concepts.get(link.concept_id)
        attempts = attempts_by_concept.get(link.concept_id, [])
        videos.append(
            {
                "lecture_id": lec.id,
                "lecture_title": lec.title,
                "lecture_date": _iso(lec.created_at),
                "concept_id": link.concept_id,
                "concept_start_time": concept.start_time if concept else None,
                "misconceptions": [
                    {
                        "id": m.id,
                        "title": m.title,
                        "status": m.status,
                        "severity_level": m.severity_level,
                        "occurrence_count": m.occurrence_count,
                        "first_detected": _iso(m.first_detected),
                        "last_detected": _iso(m.last_detected),
                        "evidence": [_evidence_dict(e) for e in evidence.get(m.id, [])[:50]],
                    }
                    for m in miscs_by_concept.get(link.concept_id, [])
                ],
                "attempts": attempts,
                "attempts_total": len(attempts),
                "attempts_correct": sum(1 for a in attempts if a["is_correct"]),
            }
        )
    videos.sort(key=lambda v: v["lecture_date"] or "")

    return {
        "canonical_concept_id": canon.id,
        "concept_name": canon.name,
        "status": rollup_status([m.status for m in miscs]) if miscs else "no_issue",
        "mastery": compute_mastery(all_results_newest_first),
        "video_count": len(videos),
        "videos": videos,
    }


# --------------------------------------------- 3. progress grouped by concept
@router.get("/progress")
def progress_by_concept(
    include_all: bool = Query(False, description="Also list concepts that never caused a misconception"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user.id
    link_unlinked_concepts(db, uid)

    link_rows = (
        db.query(CanonicalConceptLink, CanonicalConcept)
        .join(CanonicalConcept, CanonicalConcept.id == CanonicalConceptLink.canonical_concept_id)
        .filter(CanonicalConcept.user_id == uid)
        .all()
    )
    canon_by_id: Dict[int, CanonicalConcept] = {}
    links_by_canon: Dict[int, List[CanonicalConceptLink]] = defaultdict(list)
    canon_of_concept: Dict[int, int] = {}
    for link, canon in link_rows:
        canon_by_id[canon.id] = canon
        links_by_canon[canon.id].append(link)
        canon_of_concept[link.concept_id] = canon.id

    lecture_ids = list({l.lecture_id for l, _ in link_rows})
    lectures = {l.id: l for l in db.query(Lecture).filter(Lecture.id.in_(lecture_ids)).all()} if lecture_ids else {}

    miscs_by_canon: Dict[int, List[Misconception]] = defaultdict(list)
    for m in db.query(Misconception).filter(Misconception.user_id == uid).all():
        cid = canon_of_concept.get(m.concept_id)
        if cid is not None:
            miscs_by_canon[cid].append(m)

    # newest attempt first, so compute_mastery can weight recent ones more
    attempts_by_canon: Dict[int, List[tuple]] = defaultdict(list)
    attempt_rows = (
        db.query(CheckpointAttempt.is_correct, CheckpointAttempt.created_at, Checkpoint.concept_id)
        .join(Checkpoint, Checkpoint.id == CheckpointAttempt.checkpoint_id)
        .filter(CheckpointAttempt.user_id == uid)
        .order_by(CheckpointAttempt.created_at.desc(), CheckpointAttempt.id.desc())
        .all()
    )
    for is_correct, created_at, concept_id in attempt_rows:
        cid = canon_of_concept.get(concept_id)
        if cid is not None:
            attempts_by_canon[cid].append((bool(is_correct), created_at))

    items = []
    for canon_id, canon in canon_by_id.items():
        miscs = miscs_by_canon.get(canon_id, [])
        attempts = attempts_by_canon.get(canon_id, [])
        if not miscs and not include_all:
            continue

        if miscs:
            status = rollup_status([m.status for m in miscs])
        elif attempts:
            status = "no_issue"
        else:
            status = "not_started"

        videos: Dict[int, dict] = {}
        for link in links_by_canon[canon_id]:
            lec = lectures.get(link.lecture_id)
            if lec is None or lec.id in videos:
                continue
            in_lecture = [m for m in miscs if m.lecture_id == lec.id]
            videos[lec.id] = {
                "lecture_id": lec.id,
                "title": lec.title,
                "date": _iso(lec.created_at),
                "had_problem": bool(in_lecture),
                "status": rollup_status([m.status for m in in_lecture]) if in_lecture else "no_issue",
            }
        video_list = sorted(videos.values(), key=lambda v: v["date"] or "")

        stamps = [_iso(c) for _, c in attempts if c] + [_iso(m.last_detected) for m in miscs if m.last_detected]
        items.append(
            {
                "canonical_concept_id": canon_id,
                "concept_name": canon.name,
                "status": status,
                "mastery": compute_mastery([ok for ok, _ in attempts]),
                "attempts_total": len(attempts),
                "attempts_correct": sum(1 for ok, _ in attempts if ok),
                "video_count": len(video_list),
                "problem_video_count": sum(1 for v in video_list if v["had_problem"]),
                "videos": video_list,
                "last_activity": max(stamps) if stamps else None,
            }
        )

    items.sort(
        key=lambda i: (
            STATUS_ORDER.get(i["status"], 9),
            i["mastery"] if i["mastery"] is not None else 101,
            i["concept_name"],
        )
    )
    summary = {
        "total": len(items),
        "needs_attention": sum(1 for i in items if i["status"] == "needs_attention"),
        "improving": sum(1 for i in items if i["status"] == "improving"),
        "resolved": sum(1 for i in items if i["status"] == "resolved"),
    }
    return {"summary": summary, "concepts": items}