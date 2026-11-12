"""
prerequisite_link_service.py
-----------------------------
Automatically detects concept-level prerequisite links between lectures
using the Groq LLM.  Links are stored in the MongoDB `prerequisite_links`
collection.  Missing data or LLM failures are logged and silently skipped
— existing features are never broken.
"""

import json
import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.all_models import Lecture, Concept
from app.mongo import get_mongo_db


# ── Root-cause lookup ─────────────────────────────────────────────────────────

async def find_root_causes_for_misconceptions(
    student_id: int,
    misconception_concept_names: List[str],
    unresolved_concept_names: set,
) -> Dict[str, Dict[str, Any]]:
    """
    For each misconception concept, check prerequisite_links to see if it
    depends on another concept that also has an unresolved misconception.
    Returns: { concept_name: {"root_cause_concept": ..., "from_lecture_id": ..., ...} }
    """
    db = get_mongo_db()
    if db is None:
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    try:
        # Fetch all links for this student where concept is in our list
        cursor = db.prerequisite_links.find({
            "student_id": student_id,
            "concept": {"$in": misconception_concept_names},
        })
        async for link in cursor:
            concept = link.get("concept", "")
            depends_on = link.get("depends_on", "")
            from_lid = link.get("from_lecture_id")
            # Check if the depends_on concept is also unresolved
            if depends_on.lower() in unresolved_concept_names:
                # Only keep the highest-confidence root cause per concept
                existing = result.get(concept)
                if existing and existing.get("confidence", 0) >= link.get("confidence", 0):
                    continue
                result[concept] = {
                    "root_cause_concept": depends_on,
                    "from_lecture_id": from_lid,
                    "confidence": link.get("confidence", 0),
                }
    except Exception as e:
        print(f"[PrereqLinks] Root-cause lookup error: {e}")

    return result


# ── Groq client (lazy import so the app still boots if groq isn't installed) ──

def _get_groq_client():
    try:
        from groq import Groq
        key = settings.GROQ_API_KEY
        if not key:
            return None
        return Groq(api_key=key)
    except Exception:
        return None


# ── MongoDB helpers ───────────────────────────────────────────────────────────

async def save_prerequisite_links(links: List[Dict[str, Any]]) -> None:
    """Insert a batch of link documents into prerequisite_links collection."""
    db = get_mongo_db()
    if db is None or not links:
        return
    try:
        await db.prerequisite_links.insert_many(links)
    except Exception as e:
        print(f"[PrereqLinks] MongoDB insert error: {e}")


async def get_links_for_lecture(student_id: int, new_lecture_id: int) -> List[Dict[str, Any]]:
    """Return all auto-detected prerequisite links for a given lecture."""
    db = get_mongo_db()
    if db is None:
        return []
    try:
        cursor = db.prerequisite_links.find(
            {"student_id": student_id, "new_lecture_id": new_lecture_id}
        )
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        print(f"[PrereqLinks] MongoDB fetch error: {e}")
        return []


async def get_all_links_for_student(student_id: int) -> List[Dict[str, Any]]:
    """Return all prerequisite links for a student (all lectures)."""
    db = get_mongo_db()
    if db is None:
        return []
    try:
        cursor = db.prerequisite_links.find({"student_id": student_id})
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        print(f"[PrereqLinks] MongoDB fetch-all error: {e}")
        return []


async def delete_links_for_lecture(student_id: int, new_lecture_id: int) -> None:
    """Remove stale links when a lecture is reprocessed."""
    db = get_mongo_db()
    if db is None:
        return
    try:
        await db.prerequisite_links.delete_many(
            {"student_id": student_id, "new_lecture_id": new_lecture_id}
        )
    except Exception as e:
        print(f"[PrereqLinks] MongoDB delete error: {e}")


# ── Core auto-link logic ──────────────────────────────────────────────────────

async def auto_detect_prerequisite_links(
    student_id: int,
    new_lecture: Lecture,
    db: Session,
) -> int:
    """
    Called after a lecture finishes processing.
    Compares new_lecture's concepts against all earlier lectures' concepts.
    Returns the number of links saved (0 on any failure).
    """
    # Gather new lecture concept titles
    new_concepts: List[str] = [c.title for c in new_lecture.concepts if c.title]
    if not new_concepts:
        return 0

    # Gather all earlier lectures' concepts for this student
    earlier_lectures = (
        db.query(Lecture)
        .filter(
            Lecture.user_id == student_id,
            Lecture.id != new_lecture.id,
            Lecture.status == "ready",
        )
        .order_by(Lecture.created_at.asc())
        .all()
    )
    if not earlier_lectures:
        return 0

    # Build a mapping: lecture_id → list of concept titles
    earlier_concepts_map: Dict[int, List[str]] = {}
    for lec in earlier_lectures:
        titles = [c.title for c in lec.concepts if c.title]
        if titles:
            earlier_concepts_map[lec.id] = titles

    if not earlier_concepts_map:
        return 0

    # Build prompt payload
    earlier_payload = [
        {"lecture_id": lid, "concepts": titles}
        for lid, titles in earlier_concepts_map.items()
    ]

    prompt = (
        "You are a learning-graph expert. Given a NEW lecture's concepts and "
        "concepts from earlier lectures, identify prerequisite relationships.\n\n"
        f"NEW LECTURE (id={new_lecture.id}):\n"
        f"{json.dumps(new_concepts)}\n\n"
        "EARLIER LECTURES:\n"
        f"{json.dumps(earlier_payload)}\n\n"
        "Return ONLY a JSON array. Each element:\n"
        '{"concept": "<name from new lecture>", '
        '"depends_on": "<name from earlier lecture>", '
        '"from_lecture_id": <int>, '
        '"confidence": <0.0-1.0>}\n'
        "Only include pairs with confidence >= 0.6. "
        "If no strong links exist, return []."
    )

    client = _get_groq_client()
    if client is None:
        print("[PrereqLinks] Groq not available — skipping auto-link.")
        return 0

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        print(f"[PrereqLinks] Groq call failed: {e}")
        return 0

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed: List[Dict[str, Any]] = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON array")
    except Exception as e:
        print(f"[PrereqLinks] JSON parse error: {e} | raw={raw[:200]}")
        return 0

    # Filter to confidence >= 0.6 and valid from_lecture_id
    valid_lecture_ids = set(earlier_concepts_map.keys())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    docs = []
    for item in parsed:
        try:
            confidence = float(item.get("confidence", 0))
            from_lid = int(item.get("from_lecture_id", 0))
            concept = str(item.get("concept", "")).strip()
            depends_on = str(item.get("depends_on", "")).strip()
            if confidence < 0.6 or from_lid not in valid_lecture_ids:
                continue
            if not concept or not depends_on:
                continue
            docs.append({
                "student_id": student_id,
                "new_lecture_id": new_lecture.id,
                "new_lecture_title": new_lecture.title,
                "concept": concept,
                "depends_on": depends_on,
                "from_lecture_id": from_lid,
                "confidence": confidence,
                "created_at": now_iso,
            })
        except Exception:
            continue

    if not docs:
        return 0

    # Remove stale links for this lecture before saving new ones
    await delete_links_for_lecture(student_id, new_lecture.id)
    await save_prerequisite_links(docs)
    print(f"[PrereqLinks] Saved {len(docs)} links for lecture {new_lecture.id}.")
    return len(docs)

