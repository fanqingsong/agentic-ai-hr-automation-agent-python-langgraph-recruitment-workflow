# ============================================================================
# BATCH PROCESSING
# ============================================================================

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.hr.automation import (
    process_cv_upload,
    evaluate_job_against_all_candidates,
)
from backend.schemas.hr_api import HRJobPost
from backend.utils.ulid_helper import generate_ulid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batch processing: Graph1 (CV extraction) + Graph2 (job evaluation). Requires db."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(
        self,
        candidates: List[Dict[str, Any]],
        hr_job_post: HRJobPost,
        batch_id: str = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Process multiple candidates: Graph1 (upload+extract+save) then Graph2 (evaluate job vs all). db required."""
        if not batch_id:
            batch_id = generate_ulid()
        if db is None:
            raise ValueError("db is required for batch processing (Graph1 + Graph2)")
        return await self._process_batch_two_graphs(candidates, hr_job_post, batch_id, db)

    async def _process_batch_two_graphs(
        self,
        candidates: List[Dict[str, Any]],
        hr_job_post: HRJobPost,
        batch_id: str,
        db: Any,
    ) -> Dict[str, Any]:
        """Graph1 per candidate (extract + save to DB), then Graph2 for job vs all candidates."""
        batch_start_time = datetime.now()
        logger.info(f"Starting batch {batch_id} with {len(candidates)} candidates (Graph1 + Graph2)")

        candidates_collection = db.candidates
        results = []
        for candidate_data in candidates:
            async with self.semaphore:
                try:
                    result = await process_cv_upload(candidate_data, candidates_collection)
                    cid = result.get("candidate_id", "")
                    results.append({
                        "success": True,
                        "batch_id": batch_id,
                        "candidate_name": result.get("candidate_name"),
                        "candidate_email": result.get("candidate_email"),
                        "candidate_id": cid,
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.error(f"CV upload failed for {candidate_data.get('name')}: {e}")
                    results.append({
                        "success": False,
                        "batch_id": batch_id,
                        "candidate_name": candidate_data.get("name"),
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    })

        successful = sum(1 for r in results if r.get("success"))
        candidate_ids = [r["candidate_id"] for r in results if r.get("success") and r.get("candidate_id")]
        if candidate_ids:
            from bson import ObjectId
            await candidates_collection.update_many(
                {"_id": {"$in": [ObjectId(cid) for cid in candidate_ids if cid]}},
                {"$set": {"batch_id": batch_id}},
            )

        job_id = getattr(hr_job_post, "id", None) or getattr(hr_job_post, "_id", None)
        if job_id is not None:
            job_id = str(job_id)
        elif hasattr(hr_job_post, "model_dump"):
            d = hr_job_post.model_dump()
            job_id = d.get("id") or d.get("_id")
            job_id = str(job_id) if job_id is not None else None

        eval_summary = None
        if job_id:
            eval_summary = await evaluate_job_against_all_candidates(job_id, db, write_evaluations=True)
            scores = [r.get("score") for r in (eval_summary.get("results") or []) if r.get("score") is not None]
        else:
            scores = []

        total_processing_time = (datetime.now() - batch_start_time).total_seconds()
        batch_summary = {
            "batch_id": batch_id,
            "total_candidates": len(candidates),
            "successful": successful,
            "failed": len(candidates) - successful,
            "total_processing_time_seconds": total_processing_time,
            "average_processing_time_seconds": total_processing_time / len(candidates) if candidates else 0,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "highest_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "started_at": batch_start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "results": results,
            "evaluation_summary": eval_summary,
        }
        logger.info(f"Batch {batch_id} completed: {successful}/{len(candidates)} CVs saved, job evaluations written")
        return batch_summary


async def process_candidates_batch(
    candidates: List[Dict[str, Any]],
    hr_job_post: HRJobPost,
    db: Any,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """Convenience function for batch processing (Graph1 + Graph2). db required."""
    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.process_batch(candidates, hr_job_post, db=db)


async def process_candidates_from_directory(
    cv_directory: str,
    hr_job_post: HRJobPost,
    db: Any,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """Process all CVs from a directory (Graph1 + Graph2). db required."""
    cv_dir = Path(cv_directory)

    if not cv_dir.exists():
        raise ValueError(f"Directory not found: {cv_directory}")

    cv_files = list(cv_dir.glob("*.pdf")) + list(cv_dir.glob("*.PDF"))

    if not cv_files:
        raise ValueError(f"No PDF files found in {cv_directory}")

    candidates = []
    for cv_path in cv_files:
        name = cv_path.stem.replace("_", " ").replace("-", " ")
        candidates.append({
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "cv_file_path": str(cv_path),
        })

    logger.info(f"Found {len(candidates)} CV files in {cv_directory}")

    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.process_batch(candidates, hr_job_post, db=db)
