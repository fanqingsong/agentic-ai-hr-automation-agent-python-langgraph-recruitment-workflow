# ============================================================================
# AI-Powered HR Automation – entrypoints (graph and nodes live in graph/ and nodes/)
# ============================================================================

from datetime import datetime
from typing import Any, Optional

from backend.services.hr.graph import (
    create_cv_extraction_workflow,
    create_job_evaluation_workflow,
)


async def process_cv_upload(
    candidate_data: dict,
    candidates_collection: Any,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
) -> dict:
    """Run Graph1 only: upload CV -> extract -> summary -> save to MongoDB. No job/evaluation."""
    if not candidate_data.get("cv_file_path"):
        raise ValueError("cv_file_path must be provided")

    initial_state = {
        "candidate_name": candidate_data.get("name", ""),
        "candidate_email": candidate_data.get("email", ""),
        "cv_file_path": candidate_data.get("cv_file_path", ""),
        "cv_file_url": "",
        "cv_object_name": "",
        "cv_link": "",
        "extracted_cv_data": {},
        "summary": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "errors": [],
        "messages": [],
        "_candidates_collection": candidates_collection,
    }
    if user_id is not None:
        initial_state["user_id"] = user_id
    if user_email is not None:
        initial_state["user_email"] = user_email

    app = create_cv_extraction_workflow()
    final_state = await app.ainvoke(initial_state)
    return final_state


def _job_doc_to_state(job_doc: dict) -> dict:
    """Extract job fields from MongoDB job document."""
    ja = job_doc.get("jobApplication") or job_doc.get("job_application") or {}
    hr = job_doc.get("hr") or {}
    job_id = job_doc.get("_id")
    job_id = str(job_id) if job_id is not None else ""
    return {
        "job_id": job_id,
        "job_title": job_doc.get("job_title") or ja.get("title", ""),
        "job_description": job_doc.get("job_description") or ja.get("description", ""),
        "job_description_html": ja.get("description_html", ""),
        "hr_email": job_doc.get("hr_email") or hr.get("email", ""),
    }


def _candidate_doc_to_state(candidate_doc: dict) -> dict:
    """Extract candidate fields from MongoDB candidate document."""
    cid = candidate_doc.get("_id")
    cid = str(cid) if cid is not None else ""
    return {
        "candidate_id": cid,
        "candidate_name": candidate_doc.get("candidate_name", ""),
        "candidate_email": candidate_doc.get("candidate_email", ""),
        "summary": candidate_doc.get("summary", ""),
        "extracted_cv_data": candidate_doc.get("extracted_cv_data", {}),
        "cv_link": candidate_doc.get("cv_link", ""),
    }


async def evaluate_job_against_candidate(job_doc: dict, candidate_doc: dict) -> dict:
    """Run Graph2 for one job + one candidate (from DB). Does not write to DB."""
    initial_state = {
        **_job_doc_to_state(job_doc),
        **_candidate_doc_to_state(candidate_doc),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "errors": [],
        "messages": [],
    }
    app = create_job_evaluation_workflow()
    return await app.ainvoke(initial_state)


async def evaluate_job_against_all_candidates(
    job_id: str,
    db: Any,
    *,
    write_evaluations: bool = True,
) -> dict:
    """Load job and all candidates with extracted_cv_data/summary, run Graph2 for each, write to candidate_evaluations."""
    from bson import ObjectId

    jobs_collection = db.hr_job_posts
    candidates_collection = db.candidates
    evaluations_collection = getattr(db, "candidate_evaluations", None)
    if write_evaluations and evaluations_collection is None:
        evaluations_collection = db.candidate_evaluations

    job_doc = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    if not job_doc:
        return {"success": False, "error": f"Job {job_id} not found", "evaluated": 0}

    query = {"$or": [{"extracted_cv_data": {"$exists": True, "$ne": {}}}, {"summary": {"$exists": True, "$ne": ""}}]}
    cursor = candidates_collection.find(query)
    candidates = await cursor.to_list(length=None)

    results = []
    for candidate_doc in candidates:
        try:
            state = await evaluate_job_against_candidate(job_doc, candidate_doc)
            candidate_id = state.get("candidate_id") or str(candidate_doc.get("_id", ""))
            eval_doc = {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "score": state.get("evaluation_score"),
                "evaluation": state.get("evaluation", {}),
                "skills_match": state.get("skills_match", {}),
                "tag": state.get("tag", ""),
                "timestamp": state.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            }
            if write_evaluations and evaluations_collection is not None:
                await evaluations_collection.update_one(
                    {"candidate_id": candidate_id, "job_id": job_id},
                    {"$set": eval_doc},
                    upsert=True,
                )
            results.append({"candidate_id": candidate_id, "score": state.get("evaluation_score"), "tag": state.get("tag")})
        except Exception as e:
            results.append({"candidate_id": str(candidate_doc.get("_id", "")), "error": str(e)})

    return {
        "success": True,
        "job_id": job_id,
        "evaluated": len(results),
        "results": results,
    }


async def evaluate_candidate_against_all_jobs(
    candidate_id: str,
    db: Any,
    *,
    write_evaluations: bool = True,
    job_limit: int = 50,
) -> dict:
    """Load one candidate and all jobs, run Graph2 (job evaluation workflow) for each job,
    write to candidate_evaluations, return ranked list of jobs by score (desc).
    """
    from bson import ObjectId

    candidates_collection = db.candidates
    jobs_collection = db.hr_job_posts
    evaluations_collection = getattr(db, "candidate_evaluations", None)
    if write_evaluations and evaluations_collection is None:
        evaluations_collection = db.candidate_evaluations

    if not ObjectId.is_valid(candidate_id):
        return {"success": False, "error": "Invalid candidate id", "rankings": []}

    candidate_doc = await candidates_collection.find_one({"_id": ObjectId(candidate_id)})
    if not candidate_doc:
        return {"success": False, "error": "Candidate not found", "rankings": []}
    if not candidate_doc.get("summary") and not candidate_doc.get("extracted_cv_data"):
        return {"success": False, "error": "Candidate has no summary or extracted_cv_data for evaluation", "rankings": []}

    cursor = jobs_collection.find({}).sort("createdAt", -1).limit(job_limit)
    job_docs = await cursor.to_list(length=job_limit)

    rankings = []
    for job_doc in job_docs:
        jid = str(job_doc.get("_id", ""))
        try:
            state = await evaluate_job_against_candidate(job_doc, candidate_doc)
            score = state.get("evaluation_score")
            evaluation = state.get("evaluation", {})
            eval_doc = {
                "candidate_id": candidate_id,
                "job_id": jid,
                "score": score,
                "evaluation": evaluation,
                "skills_match": state.get("skills_match", {}),
                "tag": state.get("tag", ""),
                "timestamp": state.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            }
            if write_evaluations and evaluations_collection is not None:
                await evaluations_collection.update_one(
                    {"candidate_id": candidate_id, "job_id": jid},
                    {"$set": eval_doc},
                    upsert=True,
                )
            rankings.append({
                "job_id": jid,
                "score": score,
                "evaluation": evaluation,
                "tag": state.get("tag", ""),
            })
        except Exception as e:
            rankings.append({"job_id": jid, "score": None, "error": str(e)})

    rankings.sort(key=lambda x: (x.get("score") is None, -(x.get("score") or 0)))

    return {
        "success": True,
        "candidate_id": candidate_id,
        "evaluated": len(rankings),
        "rankings": rankings,
    }
