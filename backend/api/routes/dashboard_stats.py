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

            # Compute stats in the database instead of loading every matching document.
            pipeline = [
                {"$match": query},
                {
                    "$facet": {
                        "counts": [
                            {
                                "$group": {
                                    "_id": None,
                                    "total": {"$sum": 1},
                                    "successful": {
                                        "$sum": {
                                            "$cond": [
                                                {
                                                    "$ne": [
                                                        {"$ifNull": ["$evaluation_score", "MISSING"]},
                                                        "MISSING",
                                                    ]
                                                },
                                                1,
                                                0,
                                            ]
                                        }
                                    },
                                }
                            }
                        ],
                        "score_stats": [
                            {
                                "$match": {
                                    "evaluation_score": {"$exists": True, "$ne": None}
                                }
                            },
                            {
                                "$group": {
                                    "_id": None,
                                    "avg": {"$avg": "$evaluation_score"},
                                    "max": {"$max": "$evaluation_score"},
                                    "min": {"$min": "$evaluation_score"},
                                    "high": {
                                        "$sum": {
                                            "$cond": [{"$gte": ["$evaluation_score", 70]}, 1, 0]
                                        }
                                    },
                                    "low": {
                                        "$sum": {
                                            "$cond": [{"$lt": ["$evaluation_score", 50]}, 1, 0]
                                        }
                                    },
                                }
                            },
                        ],
                        "recent": [
                            {"$sort": {"timestamp": -1}},
                            {"$limit": 10},
                        ],
                        "top": [
                            {
                                "$match": {
                                    "evaluation_score": {"$exists": True, "$ne": None}
                                }
                            },
                            {"$sort": {"evaluation_score": -1}},
                            {"$limit": 10},
                        ],
                    }
                },
            ]
            agg_result = await (await candidates_collection.aggregate(pipeline)).to_list(length=1)
            facet = (agg_result[0] if agg_result else {}) or {}

            counts = (facet.get("counts") or [{}])[0]
            score_stats = (facet.get("score_stats") or [{}])[0]
            recent_docs = facet.get("recent") or []
            top_docs = facet.get("top") or []

            total = counts.get("total", 0)
            if total == 0:
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

            successful_count = counts.get("successful", 0)
            failed = total - successful_count

            recent_safe = [json_safe(c) for c in recent_docs]
            top_safe = [
                json_safe({
                    "name": c.get("candidate_name"),
                    "email": c.get("candidate_email"),
                    "score": c.get("evaluation_score"),
                    "job_title": c.get("job_title"),
                    "timestamp": c.get("timestamp"),
                })
                for c in top_docs
            ]

            return DashboardStats(
                total_candidates=total,
                successful_evaluations=successful_count,
                failed_evaluations=failed,
                average_score=float(score_stats.get("avg") or 0.0),
                highest_score=int(score_stats.get("max") or 0),
                lowest_score=int(score_stats.get("min") or 0),
                high_scorers_count=int(score_stats.get("high") or 0),
                low_scorers_count=int(score_stats.get("low") or 0),
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
                result = await (await evals_collection.aggregate(pipeline)).to_list(None)
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
                result = await (await candidates_collection.aggregate(pipeline)).to_list(None)
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
