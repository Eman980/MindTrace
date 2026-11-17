import re
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base, SessionLocal
from app.models.all_models import Concept, Lecture, utcnow


class CanonicalConcept(Base):
    __tablename__ = "mt_canonical_concepts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)   # normalized title, e.g. "binary search"
    name = Column(String(255), nullable=False)              # display name
    created_at = Column(DateTime(timezone=True), default=utcnow)

    links = relationship("CanonicalConceptLink", back_populates="canonical", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_mt_canonical_user_key"),
    )


class CanonicalConceptLink(Base):
    __tablename__ = "mt_canonical_concept_links"

    id = Column(Integer, primary_key=True, index=True)
    canonical_id = Column(Integer, ForeignKey("mt_canonical_concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    canonical = relationship("CanonicalConcept", back_populates="links")


def make_key(title: str) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    return key or "untitled"


def sync_links(db, user_id=None) -> int:
    """Link every unlinked Concept to a CanonicalConcept. Safe to run any number of times."""
    q = (
        db.query(Concept, Lecture.user_id)
        .join(Lecture, Concept.lecture_id == Lecture.id)
        .outerjoin(CanonicalConceptLink, CanonicalConceptLink.concept_id == Concept.id)
        .filter(CanonicalConceptLink.id.is_(None))
    )
    if user_id is not None:
        q = q.filter(Lecture.user_id == user_id)

    rows = q.all()
    if not rows:
        return 0

    cache = {}
    for concept, uid in rows:
        key = make_key(concept.title)
        canon = cache.get((uid, key))
        if canon is None:
            canon = db.query(CanonicalConcept).filter_by(user_id=uid, key=key).first()
            if canon is None:
                canon = CanonicalConcept(user_id=uid, key=key, name=(concept.title or "Untitled").strip())
                db.add(canon)
                db.flush()
            cache[(uid, key)] = canon
        db.add(CanonicalConceptLink(canonical_id=canon.id, concept_id=concept.id))

    db.commit()
    return len(rows)


def run_startup_link():
    """Called from lifespan. Never crashes startup."""
    db = SessionLocal()
    try:
        n = sync_links(db)
        print(f"[Canonical] linked {n} concepts")
    except Exception as e:
        db.rollback()
        print(f"[Canonical] link warning: {e}")
    finally:
        db.close()