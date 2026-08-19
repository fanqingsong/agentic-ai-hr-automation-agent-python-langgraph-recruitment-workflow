# ============================================================================
# E2E smoke test for the Langfuse integration (run against a live self-hosted
# stack; no LLM call needed — traces a pure RunnableLambda).
#
#   uv run python tests/smoke_langfuse_e2e.py
# ============================================================================

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.runnables import RunnableLambda

from backend.core.langfuse_client import (
    fetch_scores_for_traces,
    fetch_traces,
    get_trace_id,
    make_trace_config,
    ping,
    score_trace,
)
from backend.services.evaluation.runner import evaluate_state


async def main() -> int:
    ok = await ping()
    print(f"1. ping langfuse: {'OK' if ok else 'FAIL'}")
    if not ok:
        return 1

    config = make_trace_config(
        "cv-extraction",
        user_id="smoke@test",
        session_id="candidate:smoke@test",
        tags=["smoke", "graph1"],
    )
    print(f"2. trace config built: {'OK' if config else 'FAIL'}")
    if not config:
        return 1

    chain = RunnableLambda(lambda state: {**state, "summary": "smoke summary"})
    await chain.ainvoke({"input": "x"}, config=config)

    trace_id = get_trace_id(config)
    print(f"3. traced run completed: trace_id={trace_id}")
    if not trace_id:
        return 1

    # Async ingestion (worker -> ClickHouse) takes a few seconds; retry briefly.
    found = None
    traces = []
    for _ in range(6):
        await asyncio.sleep(4)
        traces = await fetch_traces(limit=5, name="cv-extraction")
        found = next((t for t in traces if t.get("trace_id") == trace_id), None)
        if found:
            break
    print(f"4. fetch_traces (Observations API v2) found our run: {'OK' if found else 'FAIL'}")
    if not found:
        print("   available:", [(t.get("name"), t.get("trace_id")) for t in traces])
        return 1

    print(
        f"   name={found.get('name')} session={found.get('session_id')} "
        f"tags={found.get('tags')} user={found.get('user_id')}"
    )

    # Online-style evaluation on a synthetic final state.
    synthetic_state = {
        "extracted_cv_data": {
            "personal_info": {"name": "Smoke", "email": "smoke@test"},
            "experience": [{"title": "Dev"}],
            "education": [],
            "skills": {"technical_skills": ["python"]},
        },
        "summary": "Smoke test engineer with python experience, sufficiently long summary text.",
        "errors": [],
    }
    results = await evaluate_state("cv-extraction", synthetic_state, trace_id)
    print("5. evaluate_state results:")
    for r in results:
        print(f"   - {r.name}: {r.value} ({r.comment})")
    if not results:
        return 1

    # Scores are ingested asynchronously; retry briefly.
    scores: list = []
    for _ in range(6):
        await asyncio.sleep(5)
        scores = (await fetch_scores_for_traces([trace_id])).get(trace_id, [])
        if scores:
            break
    score_names = sorted(s.get("name") for s in scores)
    print(f"6. scores attached to trace: {score_names}")
    if not score_names:
        return 1

    # Direct score API sanity (idempotent overwrite of one score).
    direct = score_trace(trace_id, "smoke_direct", 1.0, comment="direct score")
    print(f"7. direct create_score: {'OK' if direct else 'FAIL'}")
    return 0 if direct else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
