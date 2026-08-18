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

        return {"callbacks": [handler], "metadata": metadata}
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
    page: int = 1,
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch recent traces from the Langfuse public REST API.

    The v4 Python SDK does not expose a trace-fetching helper, so this goes
    straight to ``GET /api/public/traces`` with basic auth (pk/sk).
    """
    if not is_langfuse_enabled():
        return []

    params: Dict[str, Any] = {"limit": max(1, min(limit, 100)), "page": max(1, page)}
    if name:
        params["name"] = name
    if user_id:
        params["userId"] = user_id
    if tags:
        params["tags"] = tags  # repeated query param

    import asyncio

    def _fetch() -> List[Dict[str, Any]]:
        resp = httpx.get(
            f"{Config.LANGFUSE_HOST.rstrip('/')}/api/public/traces",
            params=params,
            auth=(Config.LANGFUSE_PUBLIC_KEY, Config.LANGFUSE_SECRET_KEY),
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    return await asyncio.to_thread(_fetch)
