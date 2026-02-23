# ============================================================================
# Jobs API routes (CRUD, evaluate-all)
# ============================================================================

import logging
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from backend.api.routes.common import json_safe, normalize_job_doc, CreateJobRequest
from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel
from backend.utils.ulid_helper import generate_ulid

logger = logging.getLogger(__name__)


def get_jobs_router(db: Any):
    router = APIRouter(tags=["Jobs"])

    @router.get("/jobs")
    async def get_jobs(
        limit: int = Query(50, ge=1, le=100),
        active_only: bool = Query(False),
    ):
        try:
            query = {}
            if active_only:
                query["active"] = True
            jobs_collection = db.hr_job_posts
            cursor = jobs_collection.find(query).sort("createdAt", -1).limit(limit)
            jobs = await cursor.to_list(length=limit)
            normalized = [normalize_job_doc(j) for j in jobs]
            return {"total": len(normalized), "jobs": normalized}
        except Exception as e:
            logger.error(f"Error fetching jobs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        try:
            if not job_id:
                raise HTTPException(status_code=400, detail="Job id required")
            jobs_collection = db.hr_job_posts
            if ObjectId.is_valid(job_id):
                query = {"_id": ObjectId(job_id)}
            else:
                query = {"ulid": job_id}
            doc = await jobs_collection.find_one(query)
            if not doc:
                raise HTTPException(status_code=404, detail="Job not found")
            return normalize_job_doc(doc)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error fetching job %s: %s", job_id, e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/jobs/{job_id}/candidate-recommendations")
    async def get_job_candidate_recommendations(
        job_id: str,
        refresh: bool = Query(False, description="Run job evaluation for all candidates then return rankings"),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        """Return candidates ranked by evaluation score for this job (from job evaluation workflow)."""
        try:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=400, detail="Invalid job id")
            jobs_collection = db.hr_job_posts
            job_doc = await jobs_collection.find_one({"_id": ObjectId(job_id)})
            if job_doc is None:
                raise HTTPException(status_code=404, detail="Job not found")

            evaluations_collection = getattr(db, "candidate_evaluations", None)
            candidates_collection = db.candidates

            if refresh:
                from backend.services.hr.automation import evaluate_job_against_all_candidates
                result = await evaluate_job_against_all_candidates(job_id, db, write_evaluations=True)
                if not result.get("success"):
                    raise HTTPException(status_code=400, detail=result.get("error", "Evaluation failed"))

            rankings = []
            if evaluations_collection is not None:
                ev_cursor = evaluations_collection.find({"job_id": job_id}).sort("score", -1)
                ev_docs = await ev_cursor.to_list(length=200)
                for ev in ev_docs:
                    rankings.append({
                        "candidate_id": ev.get("candidate_id"),
                        "score": ev.get("score"),
                        "evaluation": ev.get("evaluation", {}),
                        "tag": ev.get("tag", ""),
                    })

            candidate_ids = [r.get("candidate_id") for r in rankings if r.get("candidate_id")]
            candidate_map = {}
            if candidate_ids:
                for cid in candidate_ids:
                    if not ObjectId.is_valid(cid):
                        continue
                    cand = await candidates_collection.find_one({"_id": ObjectId(cid)})
                    if cand:
                        candidate_map[cid] = {
                            "_id": str(cand.get("_id", cid)),
                            "candidate_name": cand.get("candidate_name", ""),
                            "candidate_email": cand.get("candidate_email", ""),
                            "summary": cand.get("summary", ""),
                        }
            items = []
            for rank, r in enumerate(rankings, start=1):
                cid = r.get("candidate_id")
                cand = candidate_map.get(cid) if cid else None
                items.append({
                    "rank": rank,
                    "candidate": cand or {"_id": cid, "candidate_name": "Unknown", "candidate_email": "", "summary": ""},
                    "score": r.get("score"),
                    "reasoning": (r.get("evaluation") or {}).get("reasoning"),
                    "tag": r.get("tag"),
                })
            return {"total": len(items), "rankings": items}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching job candidate recommendations: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/jobs/{job_id}/evaluate-all")
    async def evaluate_job_against_all(
        job_id: str,
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=400, detail="Invalid job id")
            from backend.services.hr.automation import evaluate_job_against_all_candidates
            result = await evaluate_job_against_all_candidates(job_id, db, write_evaluations=True)
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error", "Evaluation failed"))
            return {
                "success": True,
                "job_id": job_id,
                "evaluated": result.get("evaluated", 0),
                "results": result.get("results", []),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error evaluating job against all candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/jobs")
    async def create_job(
        body: CreateJobRequest,
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            jobs_collection = db.hr_job_posts
            now = datetime.now().isoformat()
            ulid_str = generate_ulid()
            hr_name = (body.hr_name or "").strip() or "HR"
            hr_email = (body.hr_email or "").strip()
            title = (body.title or "").strip() or "Untitled"
            desc = (body.description or "").strip()
            doc = {
                "ulid": ulid_str,
                "jobApplication": {
                    "title": title,
                    "description": desc,
                    "description_html": desc,
                },
                "hr": {"name": hr_name, "email": hr_email},
                "job_title": title,
                "job_description": desc,
                "hr_email": hr_email,
                "createdAt": now,
                "created_at": now,
            }
            result = await jobs_collection.insert_one(doc)
            inserted_id = getattr(result, "inserted_id", None)
            if inserted_id is not None:
                doc["_id"] = str(inserted_id)
            return json_safe(doc)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error creating job: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return router
