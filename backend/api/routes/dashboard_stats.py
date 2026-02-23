# ============================================================================
# Dashboard stats and analytics routes
# ============================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from backend.api.routes.common import json_safe, DashboardStats
from backend.core.dependencies import require_manager_or_admin
from backend.models.user import UserModel

logger = logging.getLogger(__name__)


def get_dashboard_stats_router(db: Any):
    router = APIRouter(tags=["Dashboard"])

    @router.get("/dashboard/stats", response_model=DashboardStats)
    async def get_dashboard_stats(
        job_id: Optional[str] = Query(None, description="Filter by job ID"),
        days: int = Query(30, description="Number of days to look back"),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            date_from = datetime.now() - timedelta(days=days)
            query = {"timestamp": {"$gte": date_from.isoformat()}}
            if job_id:
                query["job_id"] = job_id

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
                    top_candidates=[],
                )

            total = len(all_candidates)
            successful = [c for c in all_candidates if c.get("evaluation_score") is not None]
            failed = total - len(successful)
            scores = [c.get("evaluation_score", 0) for c in successful]
            high_scorers = [s for s in scores if s >= 70]
            low_scorers = [s for s in scores if s < 50]
            top_candidates = sorted(successful, key=lambda x: x.get("evaluation_score", 0), reverse=True)[:10]

            recent_safe = [json_safe(c) for c in all_candidates[:10]]
            top_safe = [
                json_safe({
                    "name": c.get("candidate_name"),
                    "email": c.get("candidate_email"),
                    "score": c.get("evaluation_score"),
                    "job_title": c.get("job_title"),
                    "timestamp": c.get("timestamp"),
                })
                for c in top_candidates
            ]

            return DashboardStats(
                total_candidates=total,
                successful_evaluations=len(successful),
                failed_evaluations=failed,
                average_score=sum(scores) / len(scores) if scores else 0.0,
                highest_score=max(scores) if scores else 0,
                lowest_score=min(scores) if scores else 0,
                high_scorers_count=len(high_scorers),
                low_scorers_count=len(low_scorers),
                recent_candidates=recent_safe,
                top_candidates=top_safe,
            )
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/analytics/score-distribution")
    async def get_score_distribution(
        job_id: Optional[str] = Query(None),
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        try:
            distribution = []
            ranges = ["0-49", "50-59", "60-69", "70-79", "80-89", "90-100"]
            total = 0

            if job_id and getattr(db, "candidate_evaluations", None):
                evals_collection = db.candidate_evaluations
                pipeline = [
                    {"$match": {"job_id": job_id}},
                    {
                        "$bucket": {
                            "groupBy": "$score",
                            "boundaries": [0, 50, 60, 70, 80, 90, 100],
                            "default": "other",
                            "output": {"count": {"$sum": 1}},
                        }
                    },
                ]
                result = await evals_collection.aggregate(pipeline).to_list(None)
                for i, bucket in enumerate(result):
                    distribution.append({
                        "range": ranges[i] if i < len(ranges) else "other",
                        "count": bucket.get("count", 0),
                        "percentage": 0,
                    })
                total = sum(d["count"] for d in distribution)
            else:
                query = {}
                if job_id:
                    query["job_id"] = job_id
                candidates_collection = db.candidates
                pipeline = [
                    {"$match": query},
                    {
                        "$bucket": {
                            "groupBy": "$evaluation_score",
                            "boundaries": [0, 50, 60, 70, 80, 90, 100],
                            "default": "other",
                            "output": {"count": {"$sum": 1}},
                        }
                    },
                ]
                result = await candidates_collection.aggregate(pipeline).to_list(None)
                for i, bucket in enumerate(result):
                    distribution.append({
                        "range": ranges[i] if i < len(ranges) else "other",
                        "count": bucket.get("count", 0),
                        "percentage": 0,
                    })
                total = sum(d["count"] for d in distribution)

            for d in distribution:
                if total > 0:
                    d["percentage"] = round((d["count"] / total) * 100, 2)

            return {"total": total, "distribution": distribution}
        except Exception as e:
            logger.error(f"Error fetching score distribution: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
