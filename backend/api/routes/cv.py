# ============================================================================
# CV processing route (single upload)
# ============================================================================

import asyncio
import logging
import os
import shutil
import tempfile
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import Annotated

from backend.core.dependencies import get_optional_user
from backend.models.user import UserModel

logger = logging.getLogger(__name__)


def _save_upload_to_path(upload_file, dest_path: str) -> None:
    """Write uploaded file to disk (sync; run via asyncio.to_thread)."""
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(upload_file, buffer)


def get_cv_router(db: Any):
    router = APIRouter(tags=["CV"])

    @router.post("/cv/process")
    async def process_cv_submission(
        candidate_name: str = Form(...),
        candidate_email: str = Form(...),
        cv_file: UploadFile = File(...),
        current_user: Annotated[Optional[UserModel], Depends(get_optional_user)] = None,
    ):
        try:
            if not cv_file.filename or not cv_file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file format. Please upload PDF, DOC, or DOCX file."
                )

            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, cv_file.filename or "upload.pdf")

            await asyncio.to_thread(_save_upload_to_path, cv_file.file, temp_file_path)

            logger.info(f"Processing CV for {candidate_name} ({candidate_email})")

            from backend.services.hr.automation import process_cv_upload

            candidate_data = {
                "name": candidate_name,
                "email": candidate_email,
                "cv_file_path": temp_file_path,
            }
            user_id = str(current_user.id) if current_user else None
            user_email = current_user.email if current_user else None
            result = await process_cv_upload(
                candidate_data,
                db.candidates,
                user_id=user_id,
                user_email=user_email,
            )

            try:
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            except Exception:
                pass

            resume_id = result.get("candidate_id", "")
            logger.info(f"Successfully processed CV for {candidate_name}, candidate_id={resume_id}")

            return {
                "success": True,
                "message": "CV processed successfully",
                "candidate_id": resume_id,
                "candidate_name": result.get("candidate_name"),
                "candidate_email": result.get("candidate_email"),
                "summary": result.get("summary"),
                "score": None,
                "reasoning": None,
                "cv_link": result.get("cv_link"),
                "timestamp": result.get("timestamp"),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing CV: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
