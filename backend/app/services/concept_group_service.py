"""
Links every lecture's Concept row to a student-level CanonicalConcept.

It is safe to call as often as you like: it only touches concepts that have no
link yet, and it never edits or deletes existing rows.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.all_models import Concept, Lecture
from app.models.concept_groups import CanonicalConcept, CanonicalConceptLink

# Names that are at least this similar are treated as the same concept
# ("Binary Search" / "Binary Searching"). Raise it to merge less, lower it to merge more.
FUZZY_THRESHOLD = 0.9


def normalize_name(name: Optional[str]) -> str:
    raw = (name or "").strip()
    s = unicodedata.normalize("NFKD", raw).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s or raw.lower()


def _digits(s: str):
    return tuple(sorted(re.findall(r"\d+", s)))


def find_match(normalized: str, known: Dict[str, "CanonicalConcept"]):
    """Return the existing canonical concept this name belongs to, or None."""
    if normalized in known:
        return known[normalized]

    plural_key = normalized.rstrip("s")
    best, best_ratio = None, 0.0
    for key, canon in known.items():
        # "Sorting 1" and "Sorting 2" must never merge
        if _digits(key) != _digits(normalized):
            continue
        if key.rstrip("s") == plural_key:
            return canon
        ratio = SequenceMatcher(None, key, normalized).ratio()
        if ratio > best_ratio:
            best, best_ratio = canon, ratio
    if best is not None and best_ratio >= FUZZY_THRESHOLD:
        return best
    return None


def link_unlinked_concepts(db: Session, user_id: Optional[int] = None) -> int:
    """Create links for concepts that have none. Returns how many were linked."""
    q = (
        db.query(Concept.id, Concept.title, Lecture.id, Lecture.user_id)
        .join(Lecture, Lecture.id == Concept.lecture_id)
        .outerjoin(CanonicalConceptLink, CanonicalConceptLink.concept_id == Concept.id)
        .filter(CanonicalConceptLink.id.is_(None))
    )
    if user_id is not None:
        q = q.filter(Lecture.user_id == user_id)
    rows = q.order_by(Lecture.id, Concept.id).all()
    if not rows:
        return 0

    known_by_user: Dict[int, Dict[str, CanonicalConcept]] = {}
    linked = 0
    try:
        for concept_id, title, lecture_id, owner_id in rows:
            known = known_by_user.get(owner_id)
            if known is None:
                existing = db.query(CanonicalConcept).filter(CanonicalConcept.user_id == owner_id).all()
                known = {c.normalized_name: c for c in existing}
                known_by_user[owner_id] = known

            norm = normalize_name(title) or "untitled concept"
            canon = find_match(norm, known)
            if canon is None:
                canon = CanonicalConcept(
                    user_id=owner_id,
                    name=(title or "Untitled concept").strip(),
                    normalized_name=norm,
                )
                db.add(canon)
                db.flush()  # get canon.id (autoflush is off in this project)
                known[norm] = canon

            db.add(
                CanonicalConceptLink(
                    canonical_concept_id=canon.id,
                    concept_id=concept_id,
                    lecture_id=lecture_id,
                )
            )
            linked += 1
        db.commit()
    except Exception as e:
        # e.g. two requests linking at the same moment; the next call will pick up the rest
        db.rollback()
        print(f"[ConceptGroups] linking skipped: {e}")
        return 0
    return linked