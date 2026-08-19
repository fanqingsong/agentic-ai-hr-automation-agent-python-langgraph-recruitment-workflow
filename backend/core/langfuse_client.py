# ============================================================================
# LANGFUSE CLIENT (self-hosted v4: LLM/LangGraph tracing + evaluation scores)
#
# Tracing model (langfuse Python SDK v4):
# - A CallbackHandler is attached per invocation via RunnableConfig
#   ``config={"callbacks": [handler], "metadata": {...}}``.
# - Trace attributes come from reserved metadata keys:
#   langfuse_trace_name / langfuse_session_id / langfuse_user_id / langfuse_tags.
# - The resulting trace id is available as ``handler.last_trace_id`` after the
#   run, which lets the evaluation module attach scores to it.
#
# Everything here is best-effort: tracing must never break the business flow.
# ============================================================================

import logging
import threading
from typing import Any, Dict, List, Optional

import httpx

from backend.config import Config

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def is_langfuse_enabled() -> bool:
    """Tracing can be enabled only when the toggle is on and keys are set."""
    return Config.is_langfuse_configured()


def get_langfuse_client():
    """Return the shared Langfuse client singleton (or None when disabled).

    The SDK's default client (``get_client()``) reads credentials from
    LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL env vars, so
    we export our Config values there once and reuse the default client. This
    keeps CallbackHandler, scores and flush on the same client instance.
    """
    global _client
    if not is_langfuse_enabled():
        return None

    if _client is not None:
        return _client

    with _client_lock:
        if _client is None:
            import os

            from langfuse import get_client

            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", Config.LANGFUSE_PUBLIC_KEY)
            os.environ.setdefault("LANGFUSE_SECRET_KEY", Config.LANGFUSE_SECRET_KEY)
            os.environ.setdefault("LANGFUSE_BASE_URL", Config.LANGFUSE_HOST.rstrip("/"))

            try:
                _client = get_client()
                logger.info(
                    "Langfuse tracing enabled (host=%s, project key=%s...)",
                    Config.LANGFUSE_HOST,
                    Config.LANGFUSE_PUBLIC_KEY[:8],
                )
            except Exception as e:
                logger.warning("Langfuse client init failed, tracing disabled: %s", e)
                _client = None
    return _client


def make_trace_config(
    name: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Build a RunnableConfig that traces the invocation as one Langfuse trace.

    Returns None when tracing is disabled — callers then invoke the graph
    without a config (plain ``await app.ainvoke(state)``).

    Langfuse v4 is observations-first: ``run_name`` names the root observation
    (what batch evaluation filters on) while ``langfuse_trace_name`` keeps the
    trace-level name aligned for the UI.
    """
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse.langchain import CallbackHandler

        handler = CallbackHandler()
        metadata: Dict[str, Any] = {"langfuse_trace_name": name}
        if user_id:
            metadata["langfuse_user_id"] = str(user_id)
        if session_id:
            metadata["langfuse_session_id"] = str(session_id)
        if tags:
            metadata["langfuse_tags"] = [str(t) for t in tags]

        return {"run_name": name, "callbacks": [handler], "metadata": metadata}
    except Exception as e:
        logger.warning("Could not create Langfuse trace config for '%s': %s", name, e)
        return None


def get_trace_id(config: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract the trace id produced by a config from make_trace_config."""
    if not config:
        return None
    for cb in config.get("callbacks") or []:
        trace_id = getattr(cb, "last_trace_id", None)
        if trace_id:
            return trace_id
    return None


def score_trace(
    trace_id: str,
    name: str,
    value,
    *,
    data_type: str = "NUMERIC",
    comment: Optional[str] = None,
) -> bool:
    """Best-effort score creation attached to a trace.

    ``score_id`` is a stable idempotency key so re-running an evaluator on the
    same trace replaces the previous score instead of duplicating it.
    """
    client = get_langfuse_client()
    if client is None or not trace_id:
        return False
    try:
        client.create_score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type=data_type,  # type: ignore[arg-type]
            comment=comment,
            score_id=f"{trace_id}-{name}",
        )
        return True
    except Exception as e:
        logger.warning("Langfuse score '%s' on trace %s failed: %s", name, trace_id, e)
        return False


async def ping() -> bool:
    """Best-effort connectivity check for /health (server public health API)."""
    if not is_langfuse_enabled():
        return False
    import asyncio

    return await asyncio.wait_for(
        asyncio.to_thread(_ping_sync),
        timeout=3.0,
    )


def _ping_sync() -> bool:
    for path in ("/api/public/health", "/public/health"):
        try:
            resp = httpx.get(
                f"{Config.LANGFUSE_HOST.rstrip('/')}{path}",
                timeout=2.0,
            )
            if resp.status_code < 500:
                return True
        except Exception:
            continue
    return False


async def fetch_traces(
    *,
    limit: int = 50,
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch recent workflow runs from the Langfuse Observations API v2.

    Langfuse v4 self-hosting runs in "events_only" mode where the legacy
    ``GET /api/public/traces`` is removed. A workflow *run* is represented by
    its root observation (one per traced graph/agent invocation), so we query
    root observations and expose them with trace-style keys. ``output`` is the
    final LangGraph state (JSON-decoded when possible) used by batch evaluation.
    """
    client = get_langfuse_client()
    if client is None:
        return []

    import asyncio
    from datetime import datetime, timedelta, timezone

    from_start = datetime.now(timezone.utc) - timedelta(days=max(1, days))

    def _fetch() -> List[Dict[str, Any]]:
        resp = client.api.observations.get_many(
            is_root_observation=True,
            name=name,
            user_id=user_id,
            from_start_time=from_start,
            limit=max(1, min(limit, 1000)),
            fields="core,basic,io,metrics,trace_context,usage",
        )
        return [_project_observation(o) for o in resp.data]

    return await asyncio.to_thread(_fetch)


def _decode_io(value: Any) -> Any:
    """Observations v2 returns input/output as raw JSON strings."""
    if isinstance(value, str):
        try:
            import json

            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _project_observation(o: Any) -> Dict[str, Any]:
    return {
        "id": o.id,
        "trace_id": o.trace_id,
        "name": o.name,
        "timestamp": o.start_time.isoformat() if o.start_time else None,
        "user_id": getattr(o, "user_id", None),
        "session_id": getattr(o, "session_id", None),
        "latency": getattr(o, "latency", None),
        "total_cost": getattr(o, "total_cost", None),
        "tags": list(getattr(o, "tags", None) or []),
        "input": _decode_io(getattr(o, "input", None)),
        "output": _decode_io(getattr(o, "output", None)),
    }


async def fetch_scores_for_traces(trace_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch the scores attached to each trace (parallel per-trace queries).

    Scores API v3 has a ``trace_id`` filter but does not return trace linkage
    on list responses, so we query per trace and group in-process.
    """
    client = get_langfuse_client()
    if client is None or not trace_ids:
        return {}

    import asyncio

    def _fetch_one(trace_id: str) -> List[Dict[str, Any]]:
        resp = client.api.scores_v3.get_many_v3(trace_id=trace_id, limit=50)
        return [
            {
                "name": s.name,
                "value": getattr(s, "value", None),
                "data_type": str(getattr(s, "data_type", "")),
                "comment": getattr(s, "comment", None),
            }
            for s in resp.data
        ]

    results = await asyncio.gather(
        *(asyncio.to_thread(_fetch_one, t) for t in set(trace_ids)),
        return_exceptions=True,
    )
    scores: Dict[str, List[Dict[str, Any]]] = {}
    for trace_id, res in zip(set(trace_ids), results):
        if isinstance(res, Exception):
            logger.warning("Score fetch failed for trace %s: %s", trace_id, res)
        else:
            scores[trace_id] = res
    return scores
