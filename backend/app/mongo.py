"""
app/mongo.py
------------
MongoDB Atlas client, collection design, indexes, and helper functions
for Misconception Lifecycle + Disguise Test using Motor (async).
"""

import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None


def get_mongo_client() -> Optional[AsyncIOMotorClient]:
    global client
    if client is None and settings.MONGODB_URL and settings.MONGODB_URL.strip():
        client = AsyncIOMotorClient(settings.MONGODB_URL.strip(), serverSelectionTimeoutMS=2000)
    return client


def get_mongo_db() -> Optional[AsyncIOMotorDatabase]:
    global db
    if db is None:
        c = get_mongo_client()
        if c is not None:
            db = c[settings.MONGODB_DB_NAME]
    return db


def _to_object_id(id_val: Any) -> Any:
    if isinstance(id_val, str) and ObjectId.is_valid(id_val):
        return ObjectId(id_val)
    return id_val


def format_misconception_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Formats MongoDB document for API responses, ensuring string ID and default fields."""
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Default fallbacks
    d["status"] = d.get("status") or "open"
    d["relapse_count"] = int(d.get("relapse_count", 0))
    d["attempts"] = list(d.get("attempts") or [])
    return d


# ── Indexes ───────────────────────────────────────────────────────────────────

async def init_misconceptions_indexes() -> None:
    """Creates indexes on (student_id, status) and recheck_due."""
    database = get_mongo_db()
    if database is None:
        return
    try:
        col = database.misconceptions
        # Compound index on student_id and status
        await col.create_index([("student_id", 1), ("status", 1)])
        # Single field index on recheck_due for recheck querying
        await col.create_index([("recheck_due", 1)])
        print("[MongoDB] Indexes on 'misconceptions' collection verified.")
    except Exception as e:
        print(f"[MongoDB] Index creation warning: {e}")


# ── CRUD & Lifecycle Helpers ──────────────────────────────────────────────────

async def get_active_misconception(student_id: int, concept: str) -> Optional[Dict[str, Any]]:
    """Finds an active (not resolved) misconception for a student and concept."""
    database = get_mongo_db()
    if database is None:
        return None
    doc = await database.misconceptions.find_one({
        "student_id": student_id,
        "concept": concept,
        "status": {"$ne": "resolved"}
    })
    return format_misconception_doc(doc)


async def get_misconception_by_id(misconception_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a misconception by its document ID."""
    database = get_mongo_db()
    if database is None:
        return None
    oid = _to_object_id(misconception_id)
    doc = await database.misconceptions.find_one({"$or": [{"_id": oid}, {"id": misconception_id}]})
    return format_misconception_doc(doc)


async def create_or_get_misconception(
    student_id: int,
    lecture_id: int,
    concept: str,
    original_question: str,
    segment_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Creates a new misconception document or retrieves the active one.
    Avoids duplicate active records for the same student + concept.
    """
    database = get_mongo_db()
    if database is None:
        raise RuntimeError("MongoDB is not configured. Check MONGODB_URL.")

    existing = await get_active_misconception(student_id, concept)
    if existing:
        return existing

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_doc = {
        "student_id": int(student_id),
        "lecture_id": int(lecture_id),
        "segment_id": segment_id,
        "concept": concept,
        "original_question": original_question,
        "status": "open",
        "improving_at": None,
        "recheck_due": None,
        "relapse_count": 0,
        "created_at": now_iso,
        "disguise": None,
        "attempts": []
    }
    result = await database.misconceptions.insert_one(new_doc)
    new_doc["id"] = str(result.inserted_id)
    new_doc.pop("_id", None)
    return new_doc


async def record_misconception_attempt(
    misconception_id: str,
    question: str,
    student_answer: str,
    is_correct: bool,
    context_type: str = "checkpoint",
    explanation: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Appends an attempt entry to the misconception's attempts history without overwriting previous attempts.
    """
    database = get_mongo_db()
    if database is None:
        return None
    oid = _to_object_id(misconception_id)
    attempt_entry = {
        "question": question,
        "student_answer": student_answer,
        "is_correct": is_correct,
        "context_type": context_type,
        "explanation": explanation,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    await database.misconceptions.update_one(
        {"$or": [{"_id": oid}, {"id": misconception_id}]},
        {"$push": {"attempts": attempt_entry}}
    )
    return await get_misconception_by_id(misconception_id)


async def mark_misconception_open(misconception_id: str) -> Optional[Dict[str, Any]]:
    """Sets status back to 'open' upon incorrect answer."""
    database = get_mongo_db()
    if database is None:
        return None
    oid = _to_object_id(misconception_id)
    await database.misconceptions.update_one(
        {"$or": [{"_id": oid}, {"id": misconception_id}]},
        {"$set": {"status": "open"}}
    )
    return await get_misconception_by_id(misconception_id)


async def mark_misconception_improving(misconception_id: str) -> Optional[Dict[str, Any]]:
    """
    Sets status to 'improving', improving_at = today, and recheck_due = today + 2 days.
    Never marks resolved.
    """
    database = get_mongo_db()
    if database is None:
        return None
    today = datetime.date.today().isoformat()
    due = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    oid = _to_object_id(misconception_id)

    await database.misconceptions.update_one(
        {"$or": [{"_id": oid}, {"id": misconception_id}]},
        {"$set": {
            "status": "improving",
            "improving_at": today,
            "recheck_due": due
        }}
    )
    return await get_misconception_by_id(misconception_id)


async def mark_misconception_resolved(misconception_id: str) -> Optional[Dict[str, Any]]:
    """Sets status to 'resolved' upon passing the Disguise Test."""
    database = get_mongo_db()
    if database is None:
        return None
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    oid = _to_object_id(misconception_id)
    await database.misconceptions.update_one(
        {"$or": [{"_id": oid}, {"id": misconception_id}]},
        {"$set": {
            "status": "resolved",
            "resolved_at": now_iso
        }}
    )
    return await get_misconception_by_id(misconception_id)


async def mark_misconception_relapse(misconception_id: str) -> Optional[Dict[str, Any]]:
    """Sets status back to 'open' and increments relapse_count by 1."""
    database = get_mongo_db()
    if database is None:
        return None
    oid = _to_object_id(misconception_id)
    await database.misconceptions.update_one(
        {"$or": [{"_id": oid}, {"id": misconception_id}]},
        {
            "$set": {"status": "open"},
            "$inc": {"relapse_count": 1}
        }
    )
    return await get_misconception_by_id(misconception_id)


async def save_disguise_to_misconception(misconception_id: str, disguise_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Stores the generated disguise test inside the misconception document."""
    database = get_mongo_db()
    if database is None:
        return None
    oid = _to_object_id(misconception_id)
    await database.misconceptions.update_one(
        {"$or": [{"_id": oid}, {"id": misconception_id}]},
        {"$set": {"disguise": disguise_obj}}
    )
    return await get_misconception_by_id(misconception_id)


async def get_due_rechecks_list(student_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetches misconceptions where status == 'improving' and recheck_due <= today."""
    database = get_mongo_db()
    if database is None:
        return []
    today = datetime.date.today().isoformat()
    query: Dict[str, Any] = {
        "status": "improving",
        "recheck_due": {"$lte": today}
    }
    if student_id is not None:
        query["student_id"] = int(student_id)

    cursor = database.misconceptions.find(query).sort("recheck_due", 1)
    results = []
    async for doc in cursor:
        results.append(format_misconception_doc(doc))
    return results


async def get_misconceptions_report_data(lecture_id: Optional[int] = None, student_id: Optional[int] = None) -> Dict[str, Any]:
    """Generates counts (open, improving, resolved) and lists relapse cases."""
    database = get_mongo_db()
    if database is None:
        return {
            "status_counts": {"open": 0, "improving": 0, "resolved": 0},
            "relapses": []
        }

    match_stage: Dict[str, Any] = {}
    if lecture_id is not None:
        match_stage["lecture_id"] = int(lecture_id)
    if student_id is not None:
        match_stage["student_id"] = int(student_id)

    cursor = database.misconceptions.find(match_stage)
    open_count = 0
    improving_count = 0
    resolved_count = 0
    relapses = []

    async for raw_doc in cursor:
        doc = format_misconception_doc(raw_doc)
        st = doc.get("status", "open")
        if st == "improving":
            improving_count += 1
        elif st == "resolved":
            resolved_count += 1
        else:
            open_count += 1

        if doc.get("relapse_count", 0) > 0:
            relapses.append({
                "misconception_id": doc["id"],
                "concept": doc.get("concept"),
                "status": doc.get("status"),
                "relapse_count": doc.get("relapse_count"),
                "label": "memorized, not understood",
                "original_question": doc.get("original_question"),
                "explanation": (doc.get("disguise") or {}).get("explanation")
            })

    return {
        "status_counts": {
            "open": open_count,
            "improving": improving_count,
            "resolved": resolved_count
        },
        "relapses": relapses
    }
