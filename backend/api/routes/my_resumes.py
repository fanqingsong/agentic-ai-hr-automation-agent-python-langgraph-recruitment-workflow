# ============================================================================
# My Resumes API (job seeker: list, detail, download, job-recommendations)
# ============================================================================

import logging
from datetime import timedelta
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Annotated

from backend.api.routes.common import json_safe, normalize_job_doc
from backend.core.dependencies import get_current_active_user
from backend.models.user import UserModel

logger = logging.getLogger(__name__)

# Exclude from list/detail response (internal or job-specific)
MY_RESUMES_EXCLUDE = ("cv_link", "cv_object_name", "local_cv_path", "user_id", "user_email", "evaluation_score", "evaluation")


def get_my_resumes_router(db: Any):
    """Router for /api/my-resumes (list, get, download, job-recommendations). Register first so subpaths match."""
    router = APIRouter(tags=["My Resumes"])

    # ---- More specific paths first ----

    @router.get("/my-resumes/{resume_id}/download")
    async def download_my_resume(
        resume_id: str,
        current_user: Annotated[UserModel, Depends(get_current_active_user)] = None,
    ):
        if not ObjectId.is_valid(resume_id):
            raise HTTPException(status_code=400, detail="Invalid resume id")
        candidates_collection = db.candidates
        doc = await candidates_collection.find_one({"_id": ObjectId(resume_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Resume not found")
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not allowed to download this resume")
        if not doc_user_id and doc.get("candidate_email") != current_user.email:
            raise HTTPException(status_code=403, detail="Not allowed to download this resume")

        object_name = doc.get("cv_object_name")
        if not object_name:
            raise HTTPException(status_code=404, detail="CV file not stored for this resume. CVs are stored in MinIO.")

        from backend.services.storage import get_storage
        storage = get_storage()
        file_bytes = storage.download_file(object_name)
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

    @router.get("/my-resumes/{resume_id}/job-recommendations")
    async def get_my_resume_job_recommendations(
        resume_id: str,
        current_user: Annotated[UserModel, Depends(get_current_active_user)] = None,
        refresh: bool = Query(False, description="Run job evaluation workflow for all jobs and then return rankings"),
    ):
        try:
            if not ObjectId.is_valid(resume_id):
                raise HTTPException(status_code=400, detail="Invalid resume id")
            candidates_collection = db.candidates
            doc = await candidates_collection.find_one({"_id": ObjectId(resume_id)})
            if not doc:
                raise HTTPException(status_code=404, detail="Resume not found")
            doc_user_id = doc.get("user_id")
            if doc_user_id and doc_user_id != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not allowed to view this resume")
            if not doc_user_id and doc.get("candidate_email") != current_user.email:
                raise HTTPException(status_code=403, detail="Not allowed to view this resume")

            evaluations_collection = getattr(db, "candidate_evaluations", None)
            jobs_collection = db.hr_job_posts

            if refresh:
                from backend.services.hr.automation import evaluate_candidate_against_all_jobs
                result = await evaluate_candidate_against_all_jobs(resume_id, db, write_evaluations=True)
                if not result.get("success"):
                    raise HTTPException(status_code=400, detail=result.get("error", "Evaluation failed"))
                rankings = result.get("rankings", [])
            else:
                if evaluations_collection is None:
                    rankings = []
                else:
                    ev_cursor = evaluations_collection.find({"candidate_id": resume_id}).sort("score", -1)
                    ev_docs = await ev_cursor.to_list(length=100)
                    rankings = [
                        {"job_id": e.get("job_id"), "score": e.get("score"), "evaluation": e.get("evaluation", {}), "tag": e.get("tag", "")}
                        for e in ev_docs
                    ]

            job_ids = [r.get("job_id") for r in rankings if r.get("job_id")]
            job_map = {}
            if job_ids:
                for jid in job_ids:
                    if not ObjectId.is_valid(jid):
                        continue
                    job_doc = await jobs_collection.find_one({"_id": ObjectId(jid)})
                    if job_doc:
                        job_map[jid] = job_doc

            items = []
            for rank, r in enumerate(rankings, start=1):
                jid = r.get("job_id")
                job_doc = job_map.get(jid) if jid else None
                job_out = normalize_job_doc(job_doc) if job_doc else {"_id": jid, "job_title": "Unknown job"}
                items.append({
                    "rank": rank,
                    "job": job_out,
                    "score": r.get("score"),
                    "reasoning": (r.get("evaluation") or {}).get("reasoning"),
                    "tag": r.get("tag"),
                })
            return {"total": len(items), "rankings": items}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching job recommendations: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/my-resumes/{resume_id}")
    async def get_my_resume(
        resume_id: str,
        current_user: Annotated[UserModel, Depends(get_current_active_user)] = None,
    ):
        if not ObjectId.is_valid(resume_id):
            raise HTTPException(status_code=400, detail="Invalid resume id")
        candidates_collection = db.candidates
        doc = await candidates_collection.find_one({"_id": ObjectId(resume_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Resume not found")
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not allowed to view this resume")
        if not doc_user_id and doc.get("candidate_email") != current_user.email:
            raise HTTPException(status_code=403, detail="Not allowed to view this resume")

        download_url = None
        object_name = doc.get("cv_object_name")
        if object_name:
            try:
                from backend.services.storage import get_storage
                storage = get_storage()
                download_url = storage.get_file_url(object_name, expires=timedelta(hours=1))
            except Exception as e:
                logger.warning(f"Could not generate CV download URL: {e}")
        doc["download_url"] = download_url
        for k in ("cv_object_name", "local_cv_path", "user_id", "user_email", "evaluation_score", "evaluation"):
            doc.pop(k, None)
        return json_safe(doc)

    @router.get("/my-resumes")
    async def list_my_resumes(
        current_user: Annotated[UserModel, Depends(get_current_active_user)] = None,
        limit: int = Query(50, ge=1, le=100),
        skip: int = Query(0, ge=0),
    ):
        try:
            candidates_collection = db.candidates
            query = {
                "$or": [
                    {"user_id": str(current_user.id)},
                    {"user_id": {"$exists": False}, "candidate_email": current_user.email},
                    {"user_id": None, "candidate_email": current_user.email},
                ]
            }
            cursor = candidates_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
            raw_items = await cursor.to_list(length=limit)

            items = []
            for doc in raw_items:
                out = {k: v for k, v in doc.items() if k not in MY_RESUMES_EXCLUDE}
                items.append(json_safe(out))
            return {"total": len(items), "resumes": items}
        except Exception as e:
            logger.error(f"Error listing my resumes: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
