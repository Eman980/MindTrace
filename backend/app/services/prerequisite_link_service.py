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
import asyncio
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

def _extract_concept_summary(c: Concept) -> Dict[str, Any]:
    info: Dict[str, Any] = {"title": c.title}
    if c.description:
        info["description"] = c.description[:300].strip()
    core_c = getattr(c, "core_concepts", None)
    if core_c:
        info["key_topics"] = core_c[:5]
    if c.transcript_text:
        info["content_sample"] = c.transcript_text[:350].strip()
    return info


async def auto_detect_prerequisite_links(
    student_id: int,
    new_lecture: Lecture,
    db: Session,
) -> int:
    """
    Called after a lecture's concepts are generated.
    Analyzes new_lecture's concepts and taught content against all other lectures
    belonging to this student using semantic pedagogy rules.
    Detects bidirectional dependencies:
    1. new_lecture depends on an existing lecture.
    2. an existing lecture depends on new_lecture (reverse link).
    Saves the detected prerequisite relationships to SQLite and MongoDB.
    """
    try:
        db.refresh(new_lecture)
    except Exception:
        pass

    new_concept_summaries = [_extract_concept_summary(c) for c in new_lecture.concepts if c.title]
    if not new_concept_summaries:
        return 0

    # Gather library lectures for this student (exclude self and failed ones)
    library_lectures = (
        db.query(Lecture)
        .filter(
            Lecture.user_id == student_id,
            Lecture.id != new_lecture.id,
            Lecture.status != "failed",
        )
        .order_by(Lecture.created_at.asc())
        .all()
    )
    if not library_lectures:
        return 0

    earlier_payload = []
    for lec in library_lectures:
        c_summaries = [_extract_concept_summary(c) for c in lec.concepts if c.title]
        if c_summaries:
            earlier_payload.append({
                "lecture_id": lec.id,
                "title": lec.title,
                "course_code": lec.course_code,
                "concepts": c_summaries
            })

    if not earlier_payload:
        return 0

    target_payload = {
        "lecture_id": new_lecture.id,
        "title": new_lecture.title,
        "course_code": new_lecture.course_code,
        "concepts": new_concept_summaries
    }

    print(f"[PrereqLinks] Analyzing lecture {new_lecture.id} ('{new_lecture.title}') with {len(new_concept_summaries)} concepts against {len(earlier_payload)} library lectures.")

    prompt = (
        "You are an expert computer science curriculum and pedagogy analysis engine.\n"
        "Analyze the provided lectures and identify true prerequisite relationships based on the actual "
        "concepts and content taught in each lecture.\n\n"
        "PEDAGOGICAL RULES:\n"
        "1. Lecture A is a PREREQUISITE for Lecture B if Lecture B teaches advanced concepts that directly build "
        "upon or require mastery of foundational concepts taught in Lecture A.\n"
        "   Examples:\n"
        "   - 'Recursion' requires 'Functions' (parameters, return values, call stack).\n"
        "   - 'Dijkstra's Algorithm' / 'Bellman-Ford' requires 'Graph Traversals' (BFS/DFS, adjacency).\n"
        "   - 'Dynamic Programming' requires 'Recursion' or 'Array Structures'.\n"
        "2. Do NOT link lectures that merely belong to the same course or are independent side-by-side topics.\n"
        "3. Match based on the actual concept descriptions and content taught, NOT superficial title keywords.\n"
        "4. A lecture must NEVER be its own prerequisite.\n\n"
        f"NEW LECTURE (Target):\n{json.dumps(target_payload, indent=2)}\n\n"
        f"OTHER LECTURES IN STUDENT LIBRARY:\n{json.dumps(earlier_payload, indent=2)}\n\n"
        "Determine:\n"
        "A. Does NEW LECTURE depend on an existing lecture in the library as its prerequisite?\n"
        "B. Does an existing lecture in the library depend on NEW LECTURE as its prerequisite?\n\n"
        "Return ONLY a valid JSON array of objects. Format:\n"
        '[\n'
        '  {\n'
        '    "lecture_id": <int id of the lecture that depends on the prerequisite>,\n'
        '    "concept": "<name of advanced concept>",\n'
        '    "prerequisite_lecture_id": <int id of foundational prerequisite lecture>,\n'
        '    "depends_on": "<name of foundational prerequisite concept>",\n'
        '    "confidence": <float: 0.0 to 1.0>\n'
        '  }\n'
        ']\n'
        "Include ONLY strong, pedagogically valid pairs with confidence >= 0.70.\n"
        "If no true prerequisite relationship exists, return []."
    )

    client = _get_groq_client()
    if client is None:
        print("[PrereqLinks] Groq not available — skipping auto-link.")
        return 0

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a computer science pedagogy engine. Output valid JSON arrays only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or ""
        print(f"[PrereqLinks] LLM raw response for lecture {new_lecture.id} ('{new_lecture.title}'): {raw[:500]}")
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

    valid_lecture_ids = {lec["lecture_id"] for lec in earlier_payload} | {new_lecture.id}
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    docs = []
    target_prereqs = []
    other_prereqs: Dict[int, List[Dict[str, Any]]] = {}

    for item in parsed:
        try:
            confidence = float(item.get("confidence", 0))
            if confidence < 0.70:
                continue

            lec_id = int(item.get("lecture_id") or new_lecture.id)
            prereq_id = int(item.get("prerequisite_lecture_id") or item.get("from_lecture_id") or 0)
            concept = str(item.get("concept", "")).strip()
            depends_on = str(item.get("depends_on", "")).strip()

            if lec_id == prereq_id:
                continue
            if lec_id not in valid_lecture_ids or prereq_id not in valid_lecture_ids:
                continue

            if lec_id == new_lecture.id:
                target_prereqs.append({"prerequisite_lecture_id": prereq_id, "confidence": confidence})
                docs.append({
                    "student_id": student_id,
                    "new_lecture_id": new_lecture.id,
                    "new_lecture_title": new_lecture.title,
                    "concept": concept or "Advanced concept",
                    "depends_on": depends_on or "Foundational concept",
                    "from_lecture_id": prereq_id,
                    "confidence": confidence,
                    "created_at": now_iso,
                })
            elif prereq_id == new_lecture.id:
                if lec_id not in other_prereqs:
                    other_prereqs[lec_id] = []
                other_prereqs[lec_id].append({"confidence": confidence})
        except Exception:
            continue

    if docs:
        try:
            await delete_links_for_lecture(student_id, new_lecture.id)
            await save_prerequisite_links(docs)
            print(f"[PrereqLinks] Saved {len(docs)} links for lecture {new_lecture.id}.")
        except Exception as _doc_err:
            print(f"[PrereqLinks] Non-fatal document save warning: {_doc_err}")

    # ── Write lecture-level prerequisite back to SQLite ───────────────────────
    try:
        updated_any = False
        # 1. Update new_lecture with highest confidence prerequisite
        if target_prereqs:
            best_target = max(target_prereqs, key=lambda x: x["confidence"])
            best_lid = best_target["prerequisite_lecture_id"]
            if best_lid and best_lid != new_lecture.id:
                new_lecture.prerequisite_lecture_id = best_lid
                updated_any = True
                print(f"[PrereqLinks] Set lecture {new_lecture.id} ('{new_lecture.title}').prerequisite_lecture_id = {best_lid}")

        # 2. Update any other lecture in the library that depends on new_lecture
        for other_lid, conf_list in other_prereqs.items():
            other_lec = db.query(Lecture).filter(Lecture.id == other_lid, Lecture.user_id == student_id).first()
            if other_lec and other_lec.prerequisite_lecture_id != new_lecture.id:
                other_lec.prerequisite_lecture_id = new_lecture.id
                updated_any = True
                print(f"[PrereqLinks] Reverse-linked lecture {other_lec.id} ('{other_lec.title}').prerequisite_lecture_id = {new_lecture.id}")

        if updated_any:
            db.commit()
            db.refresh(new_lecture)
    except Exception as _db_err:
        print(f"[PrereqLinks] Could not write prerequisite_lecture_id: {_db_err}")

    return len(docs) + len(other_prereqs)

