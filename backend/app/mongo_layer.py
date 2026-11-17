"""
MongoDB async data‑access layer for MindTrace.
Provides minimal helper functions for the collections that the
backend currently uses: users, lectures, misconceptions, prerequisite_links.
All helpers return plain Python dicts with string "id" fields for the API.
Indexes are created on the most common lookup fields.
"""

import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

# ---------------------------------------------------------------------------
# Client / DB singletons (lazy init)
# ---------------------------------------------------------------------------
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Return a cached AsyncIOMotorClient or create one.
    The function never raises – it returns ``None`` only if the URL is missing.
    """
    global _client
    if _client is None:
        if not settings.MONGODB_URL:
            raise RuntimeError("MONGODB_URL is not configured")
        _client = AsyncIOMotorClient(settings.MONGODB_URL.strip(), serverSelectionTimeoutMS=2000)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the configured database instance.
    The database name comes from ``settings.MONGODB_DB_NAME``.
    """
    global _db
    if _db is None:
        _db = get_mongo_client()[settings.MONGODB_DB_NAME]
    return _db


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _to_object_id(val: Any) -> Any:
    """Convert a string that looks like an ObjectId to an ObjectId.
    Leaves other values untouched.
    """
    if isinstance(val, str) and ObjectId.is_valid(val):
        return ObjectId(val)
    return val

def _format_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Replace ``_id`` with string ``id`` and ensure defaults.
    Used for all collections that are exposed via the API.
    """
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# ---------------------------------------------------------------------------
# Users collection
# ---------------------------------------------------------------------------
async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    oid = _to_object_id(user_id)
    doc = await db.users.find_one({"$or": [{"_id": oid}, {"id": user_id}]})
    return _format_doc(doc)

async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new user document and return it with ``id``.
    ``user_data`` should already contain the fields expected by the API.
    """
    db = get_mongo_db()
    result = await db.users.insert_one(user_data)
    user_data["id"] = str(result.inserted_id)
    return user_data

# ---------------------------------------------------------------------------
# Lectures collection (embedded concepts, segments, checkpoints)
# ---------------------------------------------------------------------------
async def get_lecture_by_id(lecture_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    oid = _to_object_id(lecture_id)
    doc = await db.lectures.find_one({"$or": [{"_id": oid}, {"id": lecture_id}]})
    return _format_doc(doc)

async def create_lecture(lecture: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a lecture document.
    Nested structures (segments, concepts, checkpoints) are stored as‑is.
    """
    db = get_mongo_db()
    result = await db.lectures.insert_one(lecture)
    lecture["id"] = str(result.inserted_id)
    return lecture

async def update_lecture(lecture_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    oid = _to_object_id(lecture_id)
    await db.lectures.update_one({"$or": [{"_id": oid}, {"id": lecture_id}]}, {"$set": updates})
    return await get_lecture_by_id(lecture_id)

# ---------------------------------------------------------------------------
# Misconceptions collection – thin wrappers around existing helpers
# ---------------------------------------------------------------------------
from .mongo import (
    create_or_get_misconception as _create_or_get_misconception,
    get_active_misconception as _get_active_misconception,
    get_misconception_by_id as _get_misconception_by_id,
    record_misconception_attempt as _record_misconception_attempt,
    mark_misconception_improving as _mark_misconception_improving,
    mark_misconception_open as _mark_misconception_open,
)

async def get_active_misconception(student_id: int, concept: str) -> Optional[Dict[str, Any]]:
    return await _get_active_misconception(student_id, concept)

async def get_misconception_by_id(mis_id: str) -> Optional[Dict[str, Any]]:
    return await _get_misconception_by_id(mis_id)

async def create_or_get_misconception(student_id: int, lecture_id: int, concept: str, original_question: str, segment_id: Optional[int] = None) -> Dict[str, Any]:
    return await _create_or_get_misconception(student_id, lecture_id, concept, original_question, segment_id)

async def record_misconception_attempt(mis_id: str, question: str, student_answer: str, is_correct: bool, context_type: str = "checkpoint", explanation: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return await _record_misconception_attempt(mis_id, question, student_answer, is_correct, context_type, explanation)

async def mark_misconception_improving(mis_id: str) -> Optional[Dict[str, Any]]:
    return await _mark_misconception_improving(mis_id)

async def mark_misconception_open(mis_id: str) -> Optional[Dict[str, Any]]:
    return await _mark_misconception_open(mis_id)

# ---------------------------------------------------------------------------
# Prerequisite links collection
# ---------------------------------------------------------------------------
async def add_prerequisite_link(lecture_id: str, prerequisite_lecture_id: str) -> Dict[str, Any]:
    db = get_mongo_db()
    doc = {
        "lecture_id": lecture_id,
        "prerequisite_lecture_id": prerequisite_lecture_id,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    result = await db.prerequisite_links.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return doc

async def get_links_for_lecture(lecture_id: str) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    cursor = db.prerequisite_links.find({"lecture_id": lecture_id})
    return [_format_doc(doc) async for doc in cursor]

# ---------------------------------------------------------------------------
# Index creation (run once on startup)
# ---------------------------------------------------------------------------
async def init_all_indexes() -> None:
    db = get_mongo_db()
    # Users – unique email / username if present (example)
    try:
        await db.users.create_index([("email", 1)], unique=True, sparse=True)
    except Exception:
        pass
    # Lectures – index on owner/user id if stored
    try:
        await db.lectures.create_index([("owner_id", 1)])
    except Exception:
        pass
    # Prerequisite links – frequent lookup by lecture_id
    try:
        await db.prerequisite_links.create_index([("lecture_id", 1)])
    except Exception:
        pass
    # Misconceptions – already have helper in app.mongo
    # Call that helper to ensure its indexes are present
    from .mongo import init_misconceptions_indexes
    await init_misconceptions_indexes()

# End of file

