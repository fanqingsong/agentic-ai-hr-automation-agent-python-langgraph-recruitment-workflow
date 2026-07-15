# ============================================================================
# Batch processing routes
# ============================================================================

import asyncio
import hashlib
import io
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Annotated

from backend.config import Config
from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel
from backend.services.hr.batch_processing import (
    BatchProcessor,
    import_candidates_from_uploads,
    process_candidates_from_directory,
)
from backend.services.hr.data_export import DataExporter

ALLOWED_CV_EXTENSIONS = (".pdf", ".doc", ".docx")
HASH_CHUNK_SIZE = 1024 * 1024  # 1 MB
BATCH_EXPORT_MAX_ROWS = 5000

logger = logging.getLogger(__name__)


def _save_upload_with_hash(upload: UploadFile, dest_path: str) -> str:
    """Stream the upload to disk while computing its SHA-256 hash (content-based dedup key)."""
    hasher = hashlib.sha256()
    with open(dest_path, "wb") as buffer:
        while True:
            chunk = upload.file.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            buffer.write(chunk)
    return hasher.hexdigest()


def _parent_folder_from_relative_path(relative_path: str) -> str:
    """Return the immediate parent folder name from a browser-supplied relative path.

    E.g. "2026-07-10/张三.pdf" -> "2026-07-10"; "2026-07-10/sub/李四.pdf" -> "sub";
    a bare filename with no folder -> "" (uploaded directly, not inside a subfolder).
    """
    if not relative_path:
        return ""
    normalized = relative_path.replace("\\", "/").strip("/")
    parts = [p for p in normalized.split("/") if p]
    if len(parts) >= 2:
        return parts[-2]
    return ""


class BatchProcessRequest(BaseModel):
    job_id: str
    candidates: List[Dict[str, Any]]
    max_concurrent: int = Field(5, ge=1, le=20)


def get_batch_router(db: Any):
    router = APIRouter(tags=["Batch"])

    @router.post("/batch/process")
    async def process_batch_candidates(
        body: BatchProcessRequest,
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            job_id = body.job_id
            candidates = body.candidates
            max_concurrent = body.max_concurrent
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=400, detail="Invalid job id")
            jobs_collection = db.hr_job_posts
            job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
            if not job:
                raise HTTPException(status_code=404, detail="Job posting not found")

            from backend.schemas.hr_api import HRJobPost
            hr_job_post = HRJobPost(**job)
            processor = BatchProcessor(max_concurrent=max_concurrent)
            result = await processor.process_batch(candidates, hr_job_post, db=db)

            return {
                "success": True,
                "batch_id": result.get("batch_id"),
                "summary": {
                    "total": result.get("total_candidates"),
                    "successful": result.get("successful"),
                    "failed": result.get("failed"),
                    "average_score": result.get("average_score"),
                },
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/batch/upload")
    async def upload_batch_cvs(
        files: List[UploadFile] = File(...),
        # Parallel array to `files` (same order): each entry is the file's path relative to
        # the folder the user picked/dropped, e.g. "2026-07-10/张三.pdf". Used to (a) derive
        # the source folder (typically a date folder) and (b) dedupe display. Optional: a
        # plain multi-file selection (no folder) will send fewer/empty entries.
        relative_paths: List[str] = Form(default=[]),
        max_concurrent: int = Form(5, ge=1, le=20),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        """Multi-file CV import (browser upload). Runs Graph1 only (import into candidate
        pool), decoupled from any job. Score against a JD later via job recommendations.

        Deduplication: each file's SHA-256 content hash is checked against previously
        imported candidates (backend/services/hr/batch_processing.py); exact re-uploads
        (e.g. re-scanning the same root folder after new date subfolders were added) are
        skipped without re-running CV extraction. The immediate parent folder name (e.g. a
        date folder) is recorded on the candidate document as `source_folder`.
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        temp_dir = tempfile.mkdtemp(prefix="batch_upload_")
        candidates: List[Dict[str, Any]] = []
        skipped: List[str] = []
        try:
            for idx, upload in enumerate(files):
                filename = upload.filename or ""
                if not filename.lower().endswith(ALLOWED_CV_EXTENSIONS):
                    skipped.append(filename or "(unnamed)")
                    continue

                safe_name = os.path.basename(filename)
                # Prefix with index so duplicate base names (e.g. from different subfolders)
                # don't overwrite each other on disk.
                dest_path = os.path.join(temp_dir, f"{idx}_{safe_name}")
                file_hash = await asyncio.to_thread(_save_upload_with_hash, upload, dest_path)

                relative_path: Optional[str] = relative_paths[idx] if idx < len(relative_paths) else ""
                source_folder = _parent_folder_from_relative_path(relative_path or filename)

                stem = Path(safe_name).stem.replace("_", " ").replace("-", " ").strip()
                display_name = stem or "Candidate"
                candidates.append({
                    "name": display_name,
                    "email": f"{display_name.lower().replace(' ', '.')}@example.com",
                    "cv_file_path": dest_path,
                    "file_hash": file_hash,
                    "source_folder": source_folder,
                    "relative_path": relative_path or filename,
                })

            if not candidates:
                raise HTTPException(
                    status_code=400,
                    detail="No valid CV files. Allowed formats: PDF, DOC, DOCX.",
                )

            result = await import_candidates_from_uploads(
                candidates=candidates,
                db=db,
                max_concurrent=max_concurrent,
            )

            duplicate_entries = [
                {
                    "candidate_name": r.get("candidate_name"),
                    "source_folder": r.get("source_folder"),
                    "relative_path": r.get("relative_path"),
                    "existing_candidate_id": r.get("existing_candidate_id"),
                    "existing_candidate_name": r.get("existing_candidate_name"),
                }
                for r in result.get("results", [])
                if r.get("duplicate")
            ]

            return {
                "success": True,
                "batch_id": result.get("batch_id"),
                "summary": {
                    "total": result.get("total_candidates"),
                    "successful": result.get("successful"),
                    "duplicates": result.get("duplicates", 0),
                    "failed": result.get("failed"),
                    "skipped": len(skipped),
                },
                "skipped_files": skipped,
                "duplicate_files": duplicate_entries,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading batch CVs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @router.post("/batch/process-directory")
    async def process_directory_batch(
        cv_directory: str = Form(...),
        job_id: str = Form(...),
        max_concurrent: int = Form(5, ge=1, le=20),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=400, detail="Invalid job id")

            # Confine directory processing to an allowed base directory to prevent
            # reading arbitrary server paths (path traversal) via the form field.
            allowed_root = Path(Config.BATCH_ALLOWED_DIR).resolve()
            try:
                requested = Path(cv_directory).resolve()
                requested.relative_to(allowed_root)
            except (ValueError, OSError):
                raise HTTPException(
                    status_code=400,
                    detail=f"cv_directory must be inside the allowed directory: {allowed_root}",
                )
            cv_directory = str(requested)

            jobs_collection = db.hr_job_posts
            job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
            if not job:
                raise HTTPException(status_code=404, detail="Job posting not found")

            from backend.schemas.hr_api import HRJobPost
            hr_job_post = HRJobPost(**job)
            result = await process_candidates_from_directory(
                cv_directory=cv_directory,
                hr_job_post=hr_job_post,
                db=db,
                max_concurrent=max_concurrent,
            )

            return {
                "success": True,
                "batch_id": result.get("batch_id"),
                "summary": {
                    "total": result.get("total_candidates"),
                    "successful": result.get("successful"),
                    "failed": result.get("failed"),
                    "average_score": result.get("average_score"),
                },
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing directory batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/batch/{batch_id}/export")
    async def export_batch_results(
        batch_id: str,
        format: str = Query("csv", pattern="^(csv|xlsx)$"),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            candidates_collection = db.candidates
            candidates: List[Dict[str, Any]] = []

            batch_meta = await db.batch_imports.find_one({"batch_id": batch_id})
            if batch_meta:
                export_ids = [
                    cid
                    for cid in (
                        batch_meta.get("candidate_ids", [])
                        + batch_meta.get("duplicate_candidate_ids", [])
                    )
                    if cid and ObjectId.is_valid(cid)
                ]
                if export_ids:
                    cursor = candidates_collection.find(
                        {"_id": {"$in": [ObjectId(cid) for cid in export_ids]}}
                    ).limit(BATCH_EXPORT_MAX_ROWS)
                    candidates = await cursor.to_list(length=BATCH_EXPORT_MAX_ROWS)

            if not candidates:
                cursor = candidates_collection.find({"batch_id": batch_id}).limit(BATCH_EXPORT_MAX_ROWS)
                candidates = await cursor.to_list(length=BATCH_EXPORT_MAX_ROWS)

            if not candidates:
                raise HTTPException(
                    status_code=404,
                    detail="Batch not found or has no exportable candidates.",
                )

            exporter = DataExporter()

            if format == "csv":
                csv_data = exporter.export_to_csv(candidates, output_path=None)
                return StreamingResponse(
                    io.StringIO(csv_data),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}.csv"},
                )
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp_path = tmp.name
                exporter.export_to_excel(candidates, tmp_path)
                return FileResponse(
                    tmp_path,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}.xlsx"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exporting batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
