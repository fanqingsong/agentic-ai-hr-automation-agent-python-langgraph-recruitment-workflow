# ============================================================================
# CopilotKit multi-route runtime shim for Vite + FastAPI (no Node BFF).
#
# Modern @copilotkit/react-core expects:
#   GET  {base}/info
#   POST {base}/agent/{agentId}/run     (AG-UI SSE)
#   POST {base}/agent/{agentId}/connect (optional SSE)
#   POST {base}/agent/{agentId}/stop/{threadId}
#
# ag_ui_langgraph.add_langgraph_fastapi_endpoint only mounts POST {base}, so
# the React client falls back to POST {base} with {"method":"info"} and gets
# a FastAPI 422 (RunAgentInput validation). This module adds the missing
# multi-route surface while still using LangGraphAGUIAgent for runs.
#
# Agent graph compilation is deferred via ``get_agent`` so /health and /auth
# can serve immediately after restart (DeepAgents compile is slow).
# ============================================================================

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

HR_EXPLORER_NAME = "hr_explorer"
HR_EXPLORER_DESCRIPTION = (
    "Read-only HR exploration over MongoDB, Qdrant, and Neo4j"
)

GetAgent = Callable[[], LangGraphAGUIAgent]


def _sse_response(agent: LangGraphAGUIAgent, input_data: RunAgentInput, request: Request):
    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)
    request_agent = agent.clone()

    async def event_generator():
        async for event in request_agent.run(input_data):
            encoded = encoder.encode(event)
            if encoded is not None:
                yield encoded

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
    )


def mount_copilotkit_runtime(
    app: FastAPI,
    *,
    get_agent: GetAgent,
    agent_name: str = HR_EXPLORER_NAME,
    agent_description: str = HR_EXPLORER_DESCRIPTION,
    path: str = "/api/copilotkit",
) -> None:
    """Mount CopilotKit-compatible /info + AG-UI agent routes under ``path``.

    ``get_agent`` is called on first agent run (and can be cached by the caller).
    ``/info`` does not compile the graph — it only advertises the agent id.
    """
    base = "/" + path.strip("/")
    agents_catalog: Dict[str, Dict[str, Any]] = {
        agent_name: {
            "description": agent_description,
            "className": "LangGraphAgent",
        }
    }

    def _resolve_agent() -> LangGraphAGUIAgent:
        try:
            return get_agent()
        except Exception as exc:
            logger.exception("Failed to resolve HR explorer agent")
            raise HTTPException(
                status_code=503,
                detail=f"HR explorer agent unavailable: {exc}",
            ) from exc

    def _info_payload() -> Dict[str, Any]:
        return {
            "agents": agents_catalog,
            "audioFileTranscriptionEnabled": False,
            "version": "hr-automation-python-runtime",
        }

    @app.get(f"{base}/info")
    @app.post(f"{base}/info")
    async def copilotkit_info():
        # Shape expected by @copilotkit/core AgentRegistry (agents as a map).
        return _info_payload()

    @app.get(f"{base}/health")
    async def copilotkit_health():
        return {"status": "ok", "agent": {"name": agent_name}}

    @app.post(f"{base}/agent/{{agent_id}}/run")
    async def copilotkit_agent_run(agent_id: str, input_data: RunAgentInput, request: Request):
        if agent_id != agent_name:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        return _sse_response(_resolve_agent(), input_data, request)

    @app.post(f"{base}/agent/{{agent_id}}/connect")
    async def copilotkit_agent_connect(agent_id: str, request: Request):
        """Resume/connect stub: no durable threads in MemorySaver v1."""
        if agent_id != agent_name:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        accept_header = request.headers.get("accept")
        encoder = EventEncoder(accept=accept_header)

        async def empty_stream():
            # Empty SSE keeps the client happy on first load before any run.
            return
            yield b""  # pragma: no cover — keeps this an async generator

        return StreamingResponse(empty_stream(), media_type=encoder.get_content_type())

    @app.post(f"{base}/agent/{{agent_id}}/stop/{{thread_id}}")
    async def copilotkit_agent_stop(agent_id: str, thread_id: str):
        if agent_id != agent_name:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        return JSONResponse({"status": "ok", "threadId": thread_id})

    # Root POST: single-route CopilotKit envelopes OR legacy direct AG-UI RunAgentInput.
    @app.post(base)
    async def copilotkit_root_post(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = None

        if isinstance(payload, dict) and "method" in payload and "threadId" not in payload:
            method = payload.get("method")
            if method == "info":
                return JSONResponse(_info_payload())
            if method == "agent/run":
                agent_id = (payload.get("params") or {}).get("agentId") or agent_name
                if agent_id != agent_name:
                    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
                body = payload.get("body") or {}
                input_data = RunAgentInput.model_validate(body)
                return _sse_response(_resolve_agent(), input_data, request)
            if method == "agent/connect":
                accept_header = request.headers.get("accept")
                encoder = EventEncoder(accept=accept_header)

                async def empty_stream():
                    return
                    yield b""  # pragma: no cover

                return StreamingResponse(empty_stream(), media_type=encoder.get_content_type())
            if method == "agent/stop":
                return JSONResponse({"status": "ok"})
            raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

        input_data = RunAgentInput.model_validate(payload)
        return _sse_response(_resolve_agent(), input_data, request)

    logger.info(
        "CopilotKit multi-route runtime mounted at %s (agent=%s, lazy graph)",
        base,
        agent_name,
    )
