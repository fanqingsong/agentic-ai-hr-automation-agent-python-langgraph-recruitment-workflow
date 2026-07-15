# ============================================================================
# Shared utilities and schemas for dashboard API routes
# ============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


def json_safe(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat() if v else None
        elif isinstance(v, dict):
            out[k] = json_safe(v)
        elif isinstance(v, list):
            out[k] = [json_safe(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


async def fetch_docs_by_ids(collection, ids: list) -> dict:
    """Fetch multiple MongoDB documents by _id in a single query.

    Returns a dict keyed by stringified _id for O(1) lookup when enriching
    list endpoints that would otherwise N+1 loop with find_one per id.
    """
    valid_oids = [ObjectId(cid) for cid in ids if cid and ObjectId.is_valid(str(cid))]
    if not valid_oids:
        return {}
    cursor = collection.find({"_id": {"$in": valid_oids}})
    docs = await cursor.to_list(length=len(valid_oids))
    return {str(doc["_id"]): doc for doc in docs}


def normalize_job_doc(doc: dict) -> dict:
    """Ensure job document has job_title, job_description, hr_email, createdAt for API response."""
    try:
        out = dict(doc) if doc else {}
        if "_id" in out:
            out["_id"] = str(out["_id"])
        ja = out.get("jobApplication")
        if isinstance(ja, dict):
            if "job_title" not in out:
                out["job_title"] = ja.get("title", "") or ""
            if "job_description" not in out:
                out["job_description"] = ja.get("description") or ja.get("description_html", "") or ""
        hr = out.get("hr")
        if isinstance(hr, dict) and "hr_email" not in out:
            out["hr_email"] = hr.get("email", "") or ""
        if "createdAt" not in out:
            out["createdAt"] = out.get("created_at")
        return json_safe(out)
    except Exception:
        return json_safe(doc or {})


# ---------------------------------------------------------------------------
# Pydantic models for Dashboard API
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_candidates: int
    successful_evaluations: int
    failed_evaluations: int
    average_score: float
    highest_score: int
    lowest_score: int
    high_scorers_count: int
    low_scorers_count: int
    recent_candidates: List[Dict[str, Any]]
    top_candidates: List[Dict[str, Any]]


class CreateJobRequest(BaseModel):
    title: str
    description: str = ""
    hr_name: str = "HR"
    hr_email: str = ""
