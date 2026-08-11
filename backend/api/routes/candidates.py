# ============================================================================
# Candidates API routes (HR: list and detail)
# ============================================================================

import asyncio
import logging
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Annotated

from backend.api.routes.common import fetch_docs_by_ids, json_safe, normalize_job_doc
from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel

logger = logging.getLogger(__name__)


def _score_range_query(min_score: Optional[int], max_score: Optional[int]) -> Dict[str, int]:
    score_query: Dict[str, int] = {}
    if min_score is not None:
        score_query["$gte"] = min_score
    if max_score is not None:
        score_query["$lte"] = max_score
    return score_query


def _candidate_lookup_stage() -> Dict[str, Any]:
    return {
        "$lookup": {
            "from": "candidates",
            "let": {"cid": "$candidate_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$cid"]}}},
            ],
            "as": "candidate",
        }
    }


def _best_eval_lookup_stage() -> Dict[str, Any]:
    return {
        "$lookup": {
            "from": "candidate_evaluations",
            "let": {"cid": {"$toString": "$_id"}},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$candidate_id", "$$cid"]}}},
                {"$sort": {"score": -1}},
                {"$limit": 1},
            ],
            "as": "best_eval",
        }
    }


async def _attach_job_titles(candidates: List[dict], db: Any) -> List[dict]:
    job_ids = {c.get("job_id") for c in candidates if c.get("job_id")}
    if not job_ids:
        return candidates
    job_map = await fetch_docs_by_ids(db.hr_job_posts, list(job_ids))
    for candidate in candidates:
        jid = candidate.get("job_id")
        if jid and jid in job_map:
            candidate["job_title"] = normalize_job_doc(job_map[jid]).get("job_title", "")
    return candidates


async def _list_candidates_for_job(
    db: Any,
    job_id: str,
    min_score: Optional[int],
    max_score: Optional[int],
    sort_by: str,
    sort_order: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    evaluations_collection = db.candidate_evaluations
    match_stage: Dict[str, Any] = {"job_id": job_id}
    score_q = _score_range_query(min_score, max_score)
    if score_q:
        match_stage["score"] = score_q

    sort_dir = 1 if sort_order == "asc" else -1
    pipeline: List[Dict[str, Any]] = [
        {"$match": match_stage},
        _candidate_lookup_stage(),
        {"$unwind": {"path": "$candidate", "preserveNullAndEmptyArrays": True}},
    ]

    if sort_by == "name":
        pipeline.append({"$sort": {"candidate.candidate_name": sort_dir, "score": -1}})
    elif sort_by == "score":
        pipeline.append({"$sort": {"score": sort_dir, "candidate.candidate_name": 1}})
    else:
        pipeline.append({"$sort": {"candidate.timestamp": sort_dir, "score": -1}})

    pipeline.append(
        {
            "$facet": {
                "meta": [{"$count": "total"}],
                "data": [{"$skip": offset}, {"$limit": limit}],
            }
        }
    )

    rows = await (await evaluations_collection.aggregate(pipeline)).to_list(length=1)
    facet = rows[0] if rows else {"meta": [], "data": []}
    total = facet["meta"][0]["total"] if facet.get("meta") else 0
    data = facet.get("data") or []

    job_doc = await db.hr_job_posts.find_one({"_id": ObjectId(job_id)}) if ObjectId.is_valid(job_id) else None
    job_title = normalize_job_doc(job_doc).get("job_title", "") if job_doc else ""

    candidates: List[dict] = []
    for row in data:
        cand = row.get("candidate") or {}
        cid = row.get("candidate_id") or str(cand.get("_id", ""))
        candidates.append(
            {
                "_id": cid,
                "candidate_name": cand.get("candidate_name"),
                "candidate_email": cand.get("candidate_email"),
                "source_folder": cand.get("source_folder"),
                "evaluation_score": row.get("score"),
                "job_id": job_id,
                "job_title": job_title,
                "timestamp": cand.get("timestamp") or row.get("timestamp"),
            }
        )

    return {"total": total, "limit": limit, "offset": offset, "candidates": candidates}


async def _list_all_candidates_with_best_eval(
    db: Any,
    min_score: Optional[int],
    max_score: Optional[int],
    sort_by: str,
    sort_order: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    candidates_collection = db.candidates
    score_q = _score_range_query(min_score, max_score)
    sort_dir = 1 if sort_order == "asc" else -1

    pipeline: List[Dict[str, Any]] = [
        _best_eval_lookup_stage(),
        {
            "$addFields": {
                "evaluation_score": {"$arrayElemAt": ["$best_eval.score", 0]},
                "job_id": {"$arrayElemAt": ["$best_eval.job_id", 0]},
            }
        },
    ]

    if score_q:
        pipeline.append({"$match": {"evaluation_score": score_q}})

    if sort_by == "score":
        pipeline.append({"$sort": {"evaluation_score": sort_dir, "timestamp": -1}})
    elif sort_by == "name":
        pipeline.append({"$sort": {"candidate_name": sort_dir, "timestamp": -1}})
    else:
        pipeline.append({"$sort": {"timestamp": sort_dir}})

    pipeline.append(
        {
            "$facet": {
                "meta": [{"$count": "total"}],
                "data": [{"$skip": offset}, {"$limit": limit}],
            }
        }
    )

    rows = await (await candidates_collection.aggregate(pipeline)).to_list(length=1)
    facet = rows[0] if rows else {"meta": [], "data": []}
    total = facet["meta"][0]["total"] if facet.get("meta") else 0
    data = facet.get("data") or []

    candidates: List[dict] = []
    for doc in data:
        out = json_safe(doc)
        out.pop("best_eval", None)
        candidates.append(out)

    candidates = await _attach_job_titles(candidates, db)
    return {"total": total, "limit": limit, "offset": offset, "candidates": candidates}


async def _enrich_candidate_detail(candidate: dict, db: Any, job_id: Optional[str] = None) -> dict:
    evaluations_collection = getattr(db, "candidate_evaluations", None)
    if evaluations_collection is None:
        return candidate

    cid = str(candidate.get("_id", ""))
    if job_id:
        evaluation = await evaluations_collection.find_one({"candidate_id": cid, "job_id": job_id})
    else:
        cursor = evaluations_collection.find({"candidate_id": cid}).sort("score", -1).limit(1)
        evals = await cursor.to_list(length=1)
        evaluation = evals[0] if evals else None

    if not evaluation:
        return candidate

    candidate["evaluation_score"] = evaluation.get("score")
    candidate["evaluation"] = evaluation.get("evaluation", {})
    candidate["skills_match"] = evaluation.get("skills_match", {})
    candidate["job_id"] = evaluation.get("job_id")
    candidate["tag"] = evaluation.get("tag")

    jid = evaluation.get("job_id")
    if jid and ObjectId.is_valid(jid):
        job_doc = await db.hr_job_posts.find_one({"_id": ObjectId(jid)})
        if job_doc:
            candidate["job_title"] = normalize_job_doc(job_doc).get("job_title", "")

    return candidate


def get_candidates_router(db: Any):
    router = APIRouter(tags=["Candidates"])

    @router.get("/candidates")
    async def get_candidates(
        job_id: Optional[str] = Query(None),
        min_score: Optional[int] = Query(None, ge=0, le=100),
        max_score: Optional[int] = Query(None, ge=0, le=100),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        sort_by: str = Query("timestamp", pattern="^(timestamp|score|name)$"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$"),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            evaluations_collection = getattr(db, "candidate_evaluations", None)

            if job_id and evaluations_collection is not None:
                return await _list_candidates_for_job(
                    db, job_id, min_score, max_score, sort_by, sort_order, limit, offset
                )

            if evaluations_collection is not None:
                return await _list_all_candidates_with_best_eval(
                    db, min_score, max_score, sort_by, sort_order, limit, offset
                )

            # Fallback when candidate_evaluations collection is unavailable.
            query: Dict[str, Any] = {}
            if job_id:
                query["job_id"] = job_id
            score_q = _score_range_query(min_score, max_score)
            if score_q:
                query["evaluation_score"] = score_q

            sort_field = (
                "evaluation_score"
                if sort_by == "score"
                else "candidate_name"
                if sort_by == "name"
                else "timestamp"
            )
            sort_direction = -1 if sort_order == "desc" else 1

            candidates_collection = db.candidates
            total = await candidates_collection.count_documents(query)
            cursor = (
                candidates_collection.find(query)
                .sort(sort_field, sort_direction)
                .skip(offset)
                .limit(limit)
            )
            candidates = await cursor.to_list(length=limit)

            for candidate in candidates:
                if "_id" in candidate:
                    candidate["_id"] = str(candidate["_id"])

            return {"total": total, "limit": limit, "offset": offset, "candidates": candidates}
        except Exception as e:
            logger.error(f"Error fetching candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/candidates/{candidate_id}/download")
    async def download_candidate_cv(
        candidate_id: str,
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            candidates_collection = db.candidates
            try:
                object_id = ObjectId(candidate_id)
                query = {"_id": object_id}
            except Exception:
                query = {"ulid": candidate_id}

            candidate = await candidates_collection.find_one(query)
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")

            object_name = candidate.get("cv_object_name")
            if not object_name:
                raise HTTPException(
                    status_code=404,
                    detail="CV file not stored for this candidate. CVs are stored in MinIO.",
                )

            from backend.services.storage import get_storage
            storage = get_storage()
            file_bytes = await asyncio.to_thread(storage.download_file, object_name)
            filename = object_name.split("/")[-1] if "/" in object_name else "resume.pdf"
            if not filename.lower().endswith(".pdf"):
                filename = "resume.pdf"
            return Response(
                content=file_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(len(file_bytes)),
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading candidate CV: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/candidates/{candidate_id}")
    async def get_candidate_detail(
        candidate_id: str,
        job_id: Optional[str] = Query(None, description="Return evaluation for this job; default is best score"),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            candidates_collection = db.candidates
            try:
                object_id = ObjectId(candidate_id)
                query = {"_id": object_id}
            except Exception:
                query = {"ulid": candidate_id}

            candidate = await candidates_collection.find_one(query)
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            if "_id" in candidate:
                candidate["_id"] = str(candidate["_id"])
            candidate = await _enrich_candidate_detail(candidate, db, job_id=job_id)
            return json_safe(candidate)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching candidate detail: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
