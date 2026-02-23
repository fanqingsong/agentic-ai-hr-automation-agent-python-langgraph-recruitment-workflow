# ============================================================================
# Batch processing routes
# ============================================================================

import io
import logging
import tempfile
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Annotated

from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel
from backend.services.hr.batch_processing import BatchProcessor, process_candidates_from_directory
from backend.services.hr.data_export import DataExporter

logger = logging.getLogger(__name__)


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
            cursor = candidates_collection.find({"batch_id": batch_id})
            candidates = await cursor.to_list(length=None)
            if not candidates:
                raise HTTPException(status_code=404, detail="Batch not found")

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
