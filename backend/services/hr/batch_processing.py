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
        self._dedup_lock = asyncio.Lock()

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


    async def import_batch(
        self,
        candidates: List[Dict[str, Any]],
        batch_id: str = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Import-only batch: Graph1 per candidate (upload+extract+save) + tag batch_id.

        Does NOT run job evaluation (Graph2). Candidates are imported into the pool
        decoupled from any job; scoring against a JD is done later on demand.

        Dedup: if a candidate dict includes `file_hash` (SHA-256 of the CV file's content),
        it is checked against previously imported candidates before running Graph1. An
        exact content match is skipped (no re-extraction, no re-upload cost) and reported
        as a duplicate rather than a success/failure. This lets HR repeatedly point the
        importer at the same root folder (e.g. one that grows new dated subfolders over
        time) without re-importing files already in the pool.

        `source_folder` (the immediate parent folder name, e.g. a date folder) is persisted
        on the saved candidate document when provided.
        """
        if db is None:
            raise ValueError("db is required for batch import (Graph1)")
        if not batch_id:
            batch_id = generate_ulid()

        batch_start_time = datetime.now()
        logger.info(f"Starting import batch {batch_id} with {len(candidates)} candidates (Graph1 only)")

        candidates_collection = db.candidates
        seen_hashes_in_batch: set[str] = set()

        async def import_one(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
            async with self.semaphore:
                file_hash = candidate_data.get("file_hash")
                source_folder = candidate_data.get("source_folder") or ""
                try:
                    async with self._dedup_lock:
                        if file_hash and file_hash in seen_hashes_in_batch:
                            return {
                                "success": False,
                                "duplicate": True,
                                "batch_id": batch_id,
                                "candidate_name": candidate_data.get("name"),
                                "source_folder": source_folder,
                                "relative_path": candidate_data.get("relative_path"),
                                "message": "Duplicate file in this upload batch; skipped.",
                                "timestamp": datetime.now().isoformat(),
                            }

                        existing = await self._find_duplicate(candidates_collection, file_hash)
                        if existing is not None:
                            return {
                                "success": False,
                                "duplicate": True,
                                "batch_id": batch_id,
                                "candidate_name": candidate_data.get("name"),
                                "source_folder": source_folder,
                                "relative_path": candidate_data.get("relative_path"),
                                "existing_candidate_id": str(existing.get("_id", "")),
                                "existing_candidate_name": existing.get("candidate_name"),
                                "message": "Duplicate file content (same hash) already imported; skipped.",
                                "timestamp": datetime.now().isoformat(),
                            }

                        if file_hash:
                            seen_hashes_in_batch.add(file_hash)

                    result = await process_cv_upload(candidate_data, candidates_collection)
                    cid = result.get("candidate_id", "")
                    await self._backfill_candidate_identity(candidates_collection, cid, result)
                    await self._set_source_metadata(candidates_collection, cid, file_hash, source_folder)
                    return {
                        "success": True,
                        "batch_id": batch_id,
                        "candidate_name": result.get("candidate_name"),
                        "candidate_email": result.get("candidate_email"),
                        "candidate_id": cid,
                        "source_folder": source_folder,
                        "timestamp": datetime.now().isoformat(),
                    }
                except Exception as e:
                    logger.error(f"CV import failed for {candidate_data.get('name')}: {e}")
                    return {
                        "success": False,
                        "batch_id": batch_id,
                        "candidate_name": candidate_data.get("name"),
                        "source_folder": source_folder,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }

        results = list(await asyncio.gather(*(import_one(c) for c in candidates)))

        successful = sum(1 for r in results if r.get("success"))
        duplicates = sum(1 for r in results if r.get("duplicate"))
        candidate_ids = [r["candidate_id"] for r in results if r.get("success") and r.get("candidate_id")]
        if candidate_ids:
            from bson import ObjectId
            await candidates_collection.update_many(
                {"_id": {"$in": [ObjectId(cid) for cid in candidate_ids if cid]}},
                {"$set": {"batch_id": batch_id}},
            )

        duplicate_candidate_ids = [
            r["existing_candidate_id"]
            for r in results
            if r.get("duplicate") and r.get("existing_candidate_id")
        ]
        await self._save_batch_import_record(
            db,
            batch_id=batch_id,
            candidate_ids=candidate_ids,
            duplicate_candidate_ids=duplicate_candidate_ids,
            summary={
                "total_candidates": len(candidates),
                "successful": successful,
                "duplicates": duplicates,
                "failed": len(candidates) - successful - duplicates,
            },
        )

        total_processing_time = (datetime.now() - batch_start_time).total_seconds()
        logger.info(
            f"Import batch {batch_id} completed: {successful}/{len(candidates)} CVs saved, "
            f"{duplicates} duplicate(s) skipped"
        )
        return {
            "batch_id": batch_id,
            "total_candidates": len(candidates),
            "successful": successful,
            "duplicates": duplicates,
            "failed": len(candidates) - successful - duplicates,
            "total_processing_time_seconds": total_processing_time,
            "average_score": None,
            "started_at": batch_start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "results": results,
        }

    @staticmethod
    async def _save_batch_import_record(
        db: Any,
        batch_id: str,
        candidate_ids: List[str],
        duplicate_candidate_ids: List[str],
        summary: Dict[str, Any],
    ) -> None:
        """Persist batch metadata so export works even when all uploads were duplicates."""
        try:
            await db.batch_imports.update_one(
                {"batch_id": batch_id},
                {
                    "$set": {
                        "batch_id": batch_id,
                        "candidate_ids": candidate_ids,
                        "duplicate_candidate_ids": duplicate_candidate_ids,
                        "summary": summary,
                        "completed_at": datetime.now().isoformat(),
                    },
                    "$setOnInsert": {"created_at": datetime.now().isoformat()},
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Failed to save batch import record for {batch_id}: {e}")

    @staticmethod
    async def _find_duplicate(candidates_collection: Any, file_hash: Optional[str]) -> Optional[Dict[str, Any]]:
        """Look up an existing candidate with the same CV file content hash, if any."""
        if not file_hash:
            return None
        try:
            return await candidates_collection.find_one(
                {"file_hash": file_hash},
                {"candidate_name": 1, "candidate_email": 1, "source_folder": 1},
            )
        except Exception as e:
            logger.warning(f"Duplicate lookup failed for hash {file_hash[:12]}...: {e}")
            return None

    @staticmethod
    async def _set_source_metadata(
        candidates_collection: Any,
        candidate_id: str,
        file_hash: Optional[str],
        source_folder: str,
    ) -> None:
        """Persist the CV content hash (dedup key) and source folder (e.g. date folder)."""
        if not candidate_id:
            return
        updates: Dict[str, Any] = {}
        if file_hash:
            updates["file_hash"] = file_hash
        if source_folder:
            updates["source_folder"] = source_folder
        if not updates:
            return
        from bson import ObjectId
        try:
            await candidates_collection.update_one(
                {"_id": ObjectId(candidate_id)},
                {"$set": updates},
            )
        except Exception as e:
            logger.warning(f"Failed to set source metadata for {candidate_id}: {e}")

    @staticmethod
    async def _backfill_candidate_identity(
        candidates_collection: Any,
        candidate_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Update saved candidate doc's name/email from extracted personal_info when the
        original (filename-derived / placeholder) values are missing or clearly worse."""
        if not candidate_id:
            return
        personal = (result.get("extracted_cv_data") or {}).get("personal_info") or {}
        extracted_name = (personal.get("name") or "").strip()
        extracted_email = (personal.get("email") or "").strip()

        updates: Dict[str, Any] = {}
        current_email = (result.get("candidate_email") or "").strip()
        # Prefer a real extracted email over a synthesized placeholder (@example.com) or empty
        if extracted_email and "@" in extracted_email and (
            not current_email or current_email.endswith("@example.com")
        ):
            updates["candidate_email"] = extracted_email
        current_name = (result.get("candidate_name") or "").strip()
        if extracted_name and (not current_name or extracted_name.lower() != "unknown candidate"):
            # Keep filename-derived name only if extraction found nothing usable
            if extracted_name.lower() != "john doe":  # avoid mock fallback name
                updates["candidate_name"] = extracted_name

        if updates:
            from bson import ObjectId
            try:
                await candidates_collection.update_one(
                    {"_id": ObjectId(candidate_id)},
                    {"$set": updates},
                )
            except Exception as e:
                logger.warning(f"Failed to backfill identity for {candidate_id}: {e}")


async def process_candidates_batch(
    candidates: List[Dict[str, Any]],
    hr_job_post: HRJobPost,
    db: Any,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """Convenience function for batch processing (Graph1 + Graph2). db required."""
    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.process_batch(candidates, hr_job_post, db=db)


async def import_candidates_from_uploads(
    candidates: List[Dict[str, Any]],
    db: Any,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """Convenience function for import-only batch (Graph1, no job binding). db required.

    Each candidate dict should contain: name, email, cv_file_path. Optional: file_hash
    (SHA-256 of the CV content, used to skip re-importing duplicates) and source_folder
    (immediate parent folder name, e.g. a date folder, persisted on the candidate doc).
    """
    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.import_batch(candidates, db=db)


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
