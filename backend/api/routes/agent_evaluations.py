# ============================================================================
# Agent evaluation routes (Langfuse observability / evaluation API)
#
# NOTE: named "agent evaluations" to avoid clashing with the candidate
# evaluation domain (candidate_evaluations collection, /api/candidates/...).
# ============================================================================

import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.config import Config
from backend.core.dependencies import require_manager_or_admin
from backend.core.langfuse_client import (
    fetch_scores_for_traces,
    fetch_traces,
    is_langfuse_enabled,
    ping as ping_langfuse,
)
from backend.models.user import UserModel
from backend.services.evaluation.evaluators import TRACE_EVALUATORS
from backend.services.evaluation.runner import run_batch_evaluation

logger = logging.getLogger(__name__)


class BatchEvaluationRequest(BaseModel):
    """Body for POST /agent-evaluations/run."""

    limit: int = Field(50, ge=1, le=100, description="How many recent traces to evaluate")
    trace_name: Optional[str] = Field(
        None,
        description="Only evaluate traces with this name (e.g. cv-extraction, job-evaluation, hr_explorer)",
    )
    use_llm_judge: bool = Field(
        False,
        description="Also run the LLM-as-judge evaluators (extra LLM cost per trace)",
    )


def get_agent_evaluations_router(db: Any):
    router = APIRouter(tags=["Agent Evaluations"])

    @router.get("/agent-evaluations/status")
    async def get_agent_evaluations_status(
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        """Integration status + which evaluators apply to which trace name."""

        def _browser_ui_url() -> str:
            # Inside docker the backend reaches langfuse via the service name;
            # a browser on the host needs the mapped localhost port instead.
            return Config.LANGFUSE_HOST.rstrip("/").replace(
                "://langfuse-web:", "://localhost:"
            )

        enabled = is_langfuse_enabled()
        reachable = await ping_langfuse() if enabled else False
        return {
            "langfuse_enabled": enabled,
            "langfuse_reachable": reachable,
            "langfuse_host": Config.LANGFUSE_HOST if enabled else None,
            "langfuse_ui_host": _browser_ui_url() if enabled else None,
            "llm_judge_default": Config.LANGFUSE_LLM_JUDGE_ENABLED,
            "trace_evaluators": TRACE_EVALUATORS,
        }

    @router.get("/agent-evaluations/traces")
    async def list_agent_traces(
        limit: int = 50,
        name: Optional[str] = None,
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        """Recent Langfuse traces (light projection for the UI table)."""
        if not is_langfuse_enabled():
            raise HTTPException(
                status_code=503,
                detail="Langfuse is not configured. Set LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST.",
            )
        try:
            traces = await fetch_traces(limit=limit, name=name)
            scores_by_trace = await fetch_scores_for_traces(
                [t["trace_id"] for t in traces if t.get("trace_id")]
            )
        except Exception as e:
            logger.error("Failed to fetch Langfuse traces: %s", e)
            raise HTTPException(status_code=502, detail=f"Langfuse query failed: {e}")

        # Input/output states can be large; the table only needs the scores.
        def _project(t: dict) -> dict:
            return {
                "id": t.get("id"),
                "trace_id": t.get("trace_id"),
                "name": t.get("name"),
                "timestamp": t.get("timestamp"),
                "user_id": t.get("user_id"),
                "session_id": t.get("session_id"),
                "latency": t.get("latency"),
                "total_cost": t.get("total_cost"),
                "tags": t.get("tags") or [],
                "scores": scores_by_trace.get(t.get("trace_id"), []),
            }

        return {"success": True, "count": len(traces), "traces": [_project(t) for t in traces]}

    @router.post("/agent-evaluations/run")
    async def run_agent_evaluations(
        body: BatchEvaluationRequest,
        _: Annotated[UserModel, Depends(require_manager_or_admin)] = None,
    ):
        """Replay evaluators over recent traces and write scores back to Langfuse."""
        if not is_langfuse_enabled():
            raise HTTPException(
                status_code=503,
                detail="Langfuse is not configured. Set LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST.",
            )
        try:
            summary = await run_batch_evaluation(
                limit=body.limit,
                trace_name=body.trace_name,
                use_llm_judge=body.use_llm_judge,
            )
        except Exception as e:
            logger.error("Batch agent evaluation failed: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=f"Evaluation run failed: {e}")
        return summary

    return router
