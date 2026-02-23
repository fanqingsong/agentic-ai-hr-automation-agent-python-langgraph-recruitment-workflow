# ============================================================================
# Export candidates (CSV / Excel)
# ============================================================================

import io
import logging
import tempfile
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import Annotated

from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel
from backend.services.hr.data_export import DataExporter

logger = logging.getLogger(__name__)


def get_export_router(db: Any):
    router = APIRouter(tags=["Export"])

    @router.post("/export/candidates")
    async def export_candidates_data(
        job_id: Optional[str] = Form(None),
        format: str = Form("csv", pattern="^(csv|xlsx)$"),
        min_score: Optional[int] = Form(None),
        max_score: Optional[int] = Form(None),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            candidates = []
            if job_id and getattr(db, "candidate_evaluations", None):
                score_query = {}
                if min_score is not None:
                    score_query["$gte"] = min_score
                if max_score is not None:
                    score_query["$lte"] = max_score
                evals_query = {"job_id": job_id}
                if score_query:
                    evals_query["score"] = score_query
                evals_cursor = db.candidate_evaluations.find(evals_query).sort("timestamp", -1)
                evals = await evals_cursor.to_list(length=None)
                candidates_collection = db.candidates
                for ev in evals:
                    cid = ev.get("candidate_id")
                    cand = await candidates_collection.find_one({"_id": ObjectId(cid)}) if cid and ObjectId.is_valid(cid) else None
                    row = {
                        "_id": cid,
                        "candidate_name": (cand or {}).get("candidate_name", ""),
                        "candidate_email": (cand or {}).get("candidate_email", ""),
                        "summary": (cand or {}).get("summary", ""),
                        "evaluation_score": ev.get("score"),
                        "evaluation": ev.get("evaluation", {}),
                        "skills_match": ev.get("skills_match", {}),
                        "tag": ev.get("tag", ""),
                        "timestamp": ev.get("timestamp", ""),
                    }
                    candidates.append(row)
            else:
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
                candidates_collection = db.candidates
                cursor = candidates_collection.find(query).sort("timestamp", -1)
                candidates = await cursor.to_list(length=None)

            if not candidates:
                raise HTTPException(status_code=404, detail="No candidates found matching criteria")

            for candidate in candidates:
                if "_id" in candidate:
                    candidate["_id"] = str(candidate["_id"])

            exporter = DataExporter()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if format == "csv":
                filename = f"candidates_export_{timestamp}.csv"
                csv_data = exporter.export_to_csv(candidates, output_path=None)
                return StreamingResponse(
                    io.StringIO(csv_data),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )
            else:
                filename = f"candidates_export_{timestamp}.xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp_path = tmp.name
                exporter.export_to_excel(candidates, tmp_path)
                return FileResponse(
                    tmp_path,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exporting candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
