"""
New tables that group per-lecture concepts into ONE student-level concept.

Nothing in all_models.py is changed. The existing Concept / Misconception /
Checkpoint tables keep working exactly as before; these two tables sit on top.

  CanonicalConcept      one row per student per topic   (e.g. "Binary Search")
  CanonicalConceptLink  connects each lecture's Concept row to that topic
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.all_models import utcnow  # also makes sure the old tables are registered


class CanonicalConcept(Base):
    __tablename__ = "canonical_concepts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    links = relationship(
        "CanonicalConceptLink",
        back_populates="canonical_concept",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_canonical_user_name"),
    )


class CanonicalConceptLink(Base):
    __tablename__ = "canonical_concept_links"

    id = Column(Integer, primary_key=True, index=True)
    canonical_concept_id = Column(
        Integer, ForeignKey("canonical_concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Each per-lecture concept can be linked only once
    concept_id = Column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    lecture_id = Column(
        Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), default=utcnow)

    canonical_concept = relationship("CanonicalConcept", back_populates="links")