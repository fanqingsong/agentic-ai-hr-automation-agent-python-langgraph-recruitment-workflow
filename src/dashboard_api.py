# ============================================================================
# HR DASHBOARD API
# ============================================================================

"""
HR Dashboard API endpoints for analytics and data management
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
import io
import logging

logger = logging.getLogger(__name__)

# Import from existing modules
from src.data_export import DataExporter, export_candidates_to_csv, export_candidates_to_excel
from src.batch_processing import BatchProcessor, process_candidates_batch, process_candidates_from_directory

# Pydantic models for Dashboard API
from pydantic import BaseModel, Field


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics model"""
    total_candidates: int
    successful_evaluations: int
    failed_evaluations: int
    average_score: float
    highest_score: int
    lowest_score: int
    high_scorers_count: int
    low_scorers_count: int
    recent_candidates: List[Dict[str, Any]]
    top_candidates: List[Dict[str, Any]]


class CandidateFilter(BaseModel):
    """Filter model for candidate queries"""
    job_id: Optional[str] = None
    min_score: Optional[int] = Field(None, ge=0, le=100)
    max_score: Optional[int] = Field(None, ge=0, le=100)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    decision: Optional[str] = None


class BatchProcessingRequest(BaseModel):
    """Request model for batch processing"""
    job_id: str
    max_concurrent: int = Field(5, ge=1, le=20)


class BatchFromDirectoryRequest(BaseModel):
    """Request model for batch processing from directory"""
    job_id: str
    cv_directory: str
    max_concurrent: int = Field(5, ge=1, le=20)


# ============================================================================
# DASHBOARD API ENDPOINTS
# ============================================================================

def register_dashboard_routes(app: FastAPI, db):
    """
    Register dashboard API routes with FastAPI app

    Args:
        app: FastAPI application instance
        db: MongoDB database instance
    """

    @app.get("/api/dashboard/stats", response_model=DashboardStats)
    async def get_dashboard_stats(
        job_id: Optional[str] = Query(None, description="Filter by job ID"),
        days: Optional[int] = Query(30, description="Number of days to look back")
    ):
        """
        Get dashboard statistics

        Returns comprehensive statistics about candidate evaluations
        """
        try:
            # Calculate date range
            date_from = datetime.now() - timedelta(days=days)

            # Build query
            query = {"timestamp": {"$gte": date_from.isoformat()}}
            if job_id:
                query["job_id"] = job_id

            # Fetch candidates from MongoDB
            candidates_collection = db.candidates
            cursor = candidates_collection.find(query).sort("timestamp", -1)

            all_candidates = await cursor.to_list(length=None)

            if not all_candidates:
                return DashboardStats(
                    total_candidates=0,
                    successful_evaluations=0,
                    failed_evaluations=0,
                    average_score=0.0,
                    highest_score=0,
                    lowest_score=0,
                    high_scorers_count=0,
                    low_scorers_count=0,
                    recent_candidates=[],
                    top_candidates=[]
                )

            # Calculate statistics
            total = len(all_candidates)
            successful = [c for c in all_candidates if c.get("evaluation_score") is not None]
            failed = total - len(successful)

            scores = [c.get("evaluation_score", 0) for c in successful]
            high_scorers = [s for s in scores if s >= 70]
            low_scorers = [s for s in scores if s < 50]

            # Sort by score for top candidates
            top_candidates = sorted(successful, key=lambda x: x.get("evaluation_score", 0), reverse=True)[:10]

            return DashboardStats(
                total_candidates=total,
                successful_evaluations=len(successful),
                failed_evaluations=failed,
                average_score=sum(scores) / len(scores) if scores else 0.0,
                highest_score=max(scores) if scores else 0,
                lowest_score=min(scores) if scores else 0,
                high_scorers_count=len(high_scorers),
                low_scorers_count=len(low_scorers),
                recent_candidates=all_candidates[:10],  # Most recent 10
                top_candidates=[
                    {
                        "name": c.get("candidate_name"),
                        "email": c.get("candidate_email"),
                        "score": c.get("evaluation_score"),
                        "job_title": c.get("job_title"),
                        "timestamp": c.get("timestamp")
                    }
                    for c in top_candidates
                ]
            )

        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/candidates")
    async def get_candidates(
        job_id: Optional[str] = Query(None),
        min_score: Optional[int] = Query(None, ge=0, le=100),
        max_score: Optional[int] = Query(None, ge=0, le=100),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        sort_by: str = Query("timestamp", regex="^(timestamp|score|name)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$")
    ):
        """
        Get paginated list of candidates with filtering and sorting
        """
        try:
            # Build query
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

            # Determine sort field and direction
            sort_field = "evaluation_score" if sort_by == "score" else "candidate_name" if sort_by == "name" else "timestamp"
            sort_direction = -1 if sort_order == "desc" else 1

            # Fetch candidates
            candidates_collection = db.candidates
            total = await candidates_collection.count_documents(query)

            cursor = candidates_collection.find(query).sort(sort_field, sort_direction).skip(offset).limit(limit)
            candidates = await cursor.to_list(length=limit)

            # Convert ObjectId to string
            for candidate in candidates:
                if "_id" in candidate:
                    candidate["_id"] = str(candidate["_id"])

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "candidates": candidates
            }

        except Exception as e:
            logger.error(f"Error fetching candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/candidates/{candidate_id}")
    async def get_candidate_detail(candidate_id: str):
        """
        Get detailed information for a specific candidate
        """
        try:
            candidates_collection = db.candidates

            # Try to convert to ObjectId
            try:
                object_id = ObjectId(candidate_id)
                query = {"_id": object_id}
            except:
                # If not valid ObjectId, search by ulid or other field
                query = {"ulid": candidate_id}

            candidate = await candidates_collection.find_one(query)

            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")

            # Convert ObjectId
            if "_id" in candidate:
                candidate["_id"] = str(candidate["_id"])

            return candidate

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching candidate detail: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/jobs")
    async def get_jobs(
        limit: int = Query(50, ge=1, le=100),
        active_only: bool = Query(False)
    ):
        """
        Get list of job postings
        """
        try:
            query = {}
            if active_only:
                query["active"] = True

            jobs_collection = db.hr_job_posts
            cursor = jobs_collection.find(query).sort("createdAt", -1).limit(limit)
            jobs = await cursor.to_list(length=limit)

            # Convert ObjectId
            for job in jobs:
                if "_id" in job:
                    job["_id"] = str(job["_id"])

            return {
                "total": len(jobs),
                "jobs": jobs
            }

        except Exception as e:
            logger.error(f"Error fetching jobs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/analytics/score-distribution")
    async def get_score_distribution(
        job_id: Optional[str] = Query(None)
    ):
        """
        Get score distribution analytics
        """
        try:
            query = {}
            if job_id:
                query["job_id"] = job_id

            candidates_collection = db.candidates

            # Aggregation pipeline for score distribution
            pipeline = [
                {"$match": query},
                {
                    "$bucket": {
                        "groupBy": "$evaluation_score",
                        "boundaries": [0, 50, 60, 70, 80, 90, 100],
                        "default": "other",
                        "output": {
                            "count": {"$sum": 1},
                            "candidates": {"$push": "$$ROOT"}
                        }
                    }
                }
            ]

            result = await candidates_collection.aggregate(pipeline).to_list(None)

            # Format response
            distribution = []
            ranges = ["0-49", "50-59", "60-69", "70-79", "80-89", "90-100"]

            for i, bucket in enumerate(result):
                distribution.append({
                    "range": ranges[i],
                    "count": bucket.get("count", 0),
                    "percentage": 0  # Will be calculated
                })

            total = sum(d["count"] for d in distribution)

            for d in distribution:
                if total > 0:
                    d["percentage"] = round((d["count"] / total) * 100, 2)

            return {
                "total": total,
                "distribution": distribution
            }

        except Exception as e:
            logger.error(f"Error fetching score distribution: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/export/candidates")
    async def export_candidates_data(
        job_id: Optional[str] = Form(None),
        format: str = Form("csv", regex="^(csv|xlsx)$"),
        min_score: Optional[int] = Form(None),
        max_score: Optional[int] = Form(None)
    ):
        """
        Export candidates data to CSV or Excel

        Returns downloadable file
        """
        try:
            # Build query
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

            # Fetch candidates
            candidates_collection = db.candidates
            cursor = candidates_collection.find(query).sort("timestamp", -1)
            candidates = await cursor.to_list(length=None)

            if not candidates:
                raise HTTPException(status_code=404, detail="No candidates found matching criteria")

            # Convert ObjectId to string
            for candidate in candidates:
                if "_id" in candidate:
                    candidate["_id"] = str(candidate["_id"])

            # Export data
            exporter = DataExporter()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if format == "csv":
                filename = f"candidates_export_{timestamp}.csv"

                csv_data = exporter.export_to_csv(candidates, output_path=None)

                return StreamingResponse(
                    io.StringIO(csv_data),
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )

            else:  # xlsx
                filename = f"candidates_export_{timestamp}.xlsx"

                # Save to temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp_path = tmp.name

                exporter.export_to_excel(candidates, tmp_path)

                return FileResponse(
                    tmp_path,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exporting candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/batch/process")
    async def process_batch_candidates(
        candidates: List[Dict[str, Any]],
        job_id: str = Form(...),
        max_concurrent: int = Form(5, ge=1, le=20)
    ):
        """
        Process multiple candidates in batch

        Accepts a list of candidate data and processes them concurrently
        """
        try:
            # Fetch job posting
            jobs_collection = db.hr_job_posts
            job = await jobs_collection.find_one({"_id": ObjectId(job_id)})

            if not job:
                raise HTTPException(status_code=404, detail="Job posting not found")

            # Convert to HRJobPost model
            from src.fastapi_api import HRJobPost, JobApplication, HRUser

            hr_job_post = HRJobPost(**job)

            # Process batch
            processor = BatchProcessor(max_concurrent=max_concurrent)
            result = await processor.process_batch(candidates, hr_job_post)

            # Save results to database
            candidates_collection = db.candidates
            for candidate_result in result.get("results", []):
                if candidate_result.get("success"):
                    candidate_data = candidate_result.get("result", {})
                    candidate_data["batch_id"] = result.get("batch_id")
                    await candidates_collection.insert_one(candidate_data)

            return {
                "success": True,
                "batch_id": result.get("batch_id"),
                "summary": {
                    "total": result.get("total_candidates"),
                    "successful": result.get("successful"),
                    "failed": result.get("failed"),
                    "average_score": result.get("average_score")
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/batch/process-directory")
    async def process_directory_batch(
        cv_directory: str = Form(...),
        job_id: str = Form(...),
        max_concurrent: int = Form(5, ge=1, le=20)
    ):
        """
        Process all CVs from a directory in batch
        """
        try:
            # Fetch job posting
            jobs_collection = db.hr_job_posts
            job = await jobs_collection.find_one({"_id": ObjectId(job_id)})

            if not job:
                raise HTTPException(status_code=404, detail="Job posting not found")

            # Convert to HRJobPost model
            from src.fastapi_api import HRJobPost

            hr_job_post = HRJobPost(**job)

            # Process all CVs from directory
            result = await process_candidates_from_directory(
                cv_directory=cv_directory,
                hr_job_post=hr_job_post,
                max_concurrent=max_concurrent
            )

            # Save results to database
            candidates_collection = db.candidates
            for candidate_result in result.get("results", []):
                if candidate_result.get("success"):
                    candidate_data = candidate_result.get("result", {})
                    candidate_data["batch_id"] = result.get("batch_id")
                    await candidates_collection.insert_one(candidate_data)

            return {
                "success": True,
                "batch_id": result.get("batch_id"),
                "summary": {
                    "total": result.get("total_candidates"),
                    "successful": result.get("successful"),
                    "failed": result.get("failed"),
                    "average_score": result.get("average_score")
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing directory batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/batch/{batch_id}/export")
    async def export_batch_results(
        batch_id: str,
        format: str = Query("csv", regex="^(csv|xlsx)$")
    ):
        """
        Export batch processing results
        """
        try:
            # Fetch batch results
            candidates_collection = db.candidates
            cursor = candidates_collection.find({"batch_id": batch_id})
            candidates = await cursor.to_list(length=None)

            if not candidates:
                raise HTTPException(status_code=404, detail="Batch not found")

            # Create batch result structure
            batch_result = {
                "batch_id": batch_id,
                "results": candidates
            }

            # Export
            exporter = DataExporter()

            if format == "csv":
                csv_data = exporter.export_to_csv(candidates, output_path=None)

                return StreamingResponse(
                    io.StringIO(csv_data),
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=batch_{batch_id}.csv"
                    }
                )

            else:  # xlsx
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp_path = tmp.name

                exporter.export_to_excel(candidates, tmp_path)

                return FileResponse(
                    tmp_path,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f"attachment; filename=batch_{batch_id}.xlsx"
                    }
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exporting batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    logger.info("✅ Dashboard API routes registered successfully")
