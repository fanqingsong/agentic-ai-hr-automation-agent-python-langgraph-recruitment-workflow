# ============================================================================
# MongoDB read-only query helpers for the HR explorer Agent.
#
# Returns truncated, JSON-friendly summaries so tool results fit in LLM
# context. Never exposes write operations.
# ============================================================================

import logging
from typing import Any, Dict, List, Optional

from bson import ObjectId

from backend.core.mongodb import get_mongo_db

logger = logging.getLogger(__name__)

_SUMMARY_MAX = 800
_TEXT_MAX = 400


def _truncate(text: Optional[str], limit: int = _TEXT_MAX) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _candidate_summary(doc: dict) -> Dict[str, Any]:
    extracted = doc.get("extracted_cv_data") or {}
    personal = extracted.get("personal_info") or {}
    skills = extracted.get("skills") or {}
    experience = extracted.get("experience") or []
    education = extracted.get("education") or []

    return {
        "candidate_id": str(doc.get("_id", "")),
        "name": doc.get("candidate_name") or personal.get("name", ""),
        "email": doc.get("candidate_email") or personal.get("email", ""),
        "summary": _truncate(doc.get("summary"), _SUMMARY_MAX),
        "skills": {
            "technical_skills": (skills.get("technical_skills") or [])[:20],
            "tools": (skills.get("tools") or [])[:15],
            "soft_skills": (skills.get("soft_skills") or [])[:10],
        },
        "experience": [
            {
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "duration": exp.get("duration", ""),
                "description": _truncate(exp.get("description"), 220),
            }
            for exp in experience[:5]
        ],
        "education": [
            {
                "degree": edu.get("degree", ""),
                "institution": edu.get("institution", ""),
                "year": edu.get("year", ""),
            }
            for edu in education[:3]
        ],
        "timestamp": doc.get("timestamp", ""),
    }


def _job_summary(doc: dict) -> Dict[str, Any]:
    ja = doc.get("jobApplication") or doc.get("job_application") or {}
    job_skills = doc.get("job_skills") or {}
    description = doc.get("job_description") or ja.get("description", "")
    return {
        "job_id": str(doc.get("_id", "")),
        "title": doc.get("job_title") or ja.get("title", ""),
        "description": _truncate(description, _SUMMARY_MAX),
        "tech_skills": (job_skills.get("tech_skills") or [])[:25],
        "soft_skills": (job_skills.get("soft_skills") or [])[:15],
        "hr_email": doc.get("hr_email") or (doc.get("hr") or {}).get("email", ""),
        "created_at": doc.get("createdAt") or doc.get("created_at", ""),
    }


async def get_candidate(candidate_id: str) -> Dict[str, Any]:
    """Fetch one candidate by id. Returns {error: ...} on failure."""
    try:
        if not ObjectId.is_valid(candidate_id):
            return {"error": f"Invalid candidate_id: {candidate_id}"}
        db = get_mongo_db()
        doc = await db.candidates.find_one({"_id": ObjectId(candidate_id)})
        if not doc:
            return {"error": f"Candidate not found: {candidate_id}"}
        return _candidate_summary(doc)
    except Exception as e:
        logger.warning("get_candidate failed: %s", e)
        return {"error": str(e)}


async def list_candidates(
    name_contains: Optional[str] = None,
    skill_contains: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """List candidates with optional name/skill substring filters."""
    try:
        limit = max(1, min(int(limit or 10), 25))
        db = get_mongo_db()
        query: Dict[str, Any] = {}
        if name_contains:
            query["candidate_name"] = {"$regex": name_contains, "$options": "i"}
        if skill_contains:
            query["$or"] = [
                {"extracted_cv_data.skills.technical_skills": {"$regex": skill_contains, "$options": "i"}},
                {"extracted_cv_data.skills.tools": {"$regex": skill_contains, "$options": "i"}},
            ]
        cursor = db.candidates.find(query).sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return {"total_returned": len(docs), "candidates": [_candidate_summary(d) for d in docs]}
    except Exception as e:
        logger.warning("list_candidates failed: %s", e)
        return {"error": str(e)}


async def get_job(job_id: str) -> Dict[str, Any]:
    """Fetch one job by id."""
    try:
        if not ObjectId.is_valid(job_id):
            return {"error": f"Invalid job_id: {job_id}"}
        db = get_mongo_db()
        doc = await db.hr_job_posts.find_one({"_id": ObjectId(job_id)})
        if not doc:
            return {"error": f"Job not found: {job_id}"}
        return _job_summary(doc)
    except Exception as e:
        logger.warning("get_job failed: %s", e)
        return {"error": str(e)}


async def list_jobs(title_contains: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """List jobs with optional title substring filter."""
    try:
        limit = max(1, min(int(limit or 10), 25))
        db = get_mongo_db()
        query: Dict[str, Any] = {}
        if title_contains:
            query["$or"] = [
                {"job_title": {"$regex": title_contains, "$options": "i"}},
                {"jobApplication.title": {"$regex": title_contains, "$options": "i"}},
            ]
        cursor = db.hr_job_posts.find(query).sort("createdAt", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return {"total_returned": len(docs), "jobs": [_job_summary(d) for d in docs]}
    except Exception as e:
        logger.warning("list_jobs failed: %s", e)
        return {"error": str(e)}


async def get_evaluations(
    candidate_id: Optional[str] = None,
    job_id: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 15,
) -> Dict[str, Any]:
    """List evaluation docs from candidate_evaluations."""
    try:
        if not candidate_id and not job_id:
            return {"error": "Provide candidate_id and/or job_id"}
        limit = max(1, min(int(limit or 15), 30))
        db = get_mongo_db()
        query: Dict[str, Any] = {}
        if candidate_id:
            query["candidate_id"] = candidate_id
        if job_id:
            query["job_id"] = job_id
        if min_score is not None:
            query["score"] = {"$gte": int(min_score)}

        cursor = db.candidate_evaluations.find(query).sort("score", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        items = []
        for d in docs:
            evaluation = d.get("evaluation") or {}
            items.append({
                "candidate_id": d.get("candidate_id"),
                "job_id": d.get("job_id"),
                "score": d.get("score"),
                "tag": d.get("tag", ""),
                "reasoning": _truncate(evaluation.get("reasoning"), 500),
                "strengths": (evaluation.get("strengths") or [])[:5],
                "gaps": (evaluation.get("gaps") or [])[:5],
                "skills_match": d.get("skills_match") or {},
                "timestamp": d.get("timestamp", ""),
            })
        return {"total_returned": len(items), "evaluations": items}
    except Exception as e:
        logger.warning("get_evaluations failed: %s", e)
        return {"error": str(e)}
