# ============================================================================
# Candidates API routes (HR: list and detail)
# ============================================================================

import logging
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel

logger = logging.getLogger(__name__)


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
            query = {}
            if job_id:
                query["job_id"] = job_id
            if min_score is not None or max_score is not None:
                score_query = {}
                if min_score is not None:
                    score_query["$gte"] = min_score
                if max_score is not None:
                    score_query["$lte"] = max_score
                query["evaluation_score"] = score_query

            sort_field = "evaluation_score" if sort_by == "score" else "candidate_name" if sort_by == "name" else "timestamp"
            sort_direction = -1 if sort_order == "desc" else 1

            candidates_collection = db.candidates
            total = await candidates_collection.count_documents(query)
            cursor = candidates_collection.find(query).sort(sort_field, sort_direction).skip(offset).limit(limit)
            candidates = await cursor.to_list(length=limit)

            for candidate in candidates:
                if "_id" in candidate:
                    candidate["_id"] = str(candidate["_id"])

            return {"total": total, "limit": limit, "offset": offset, "candidates": candidates}
        except Exception as e:
            logger.error(f"Error fetching candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/candidates/{candidate_id}")
    async def get_candidate_detail(
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
            if "_id" in candidate:
                candidate["_id"] = str(candidate["_id"])
            return candidate
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching candidate detail: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
