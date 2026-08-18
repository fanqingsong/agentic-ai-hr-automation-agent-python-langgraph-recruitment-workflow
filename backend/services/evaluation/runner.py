# ============================================================================
# Agent evaluation runner.
#
# Online mode: called right after each traced workflow run; writes heuristic
# scores to the just-created Langfuse trace (zero extra LLM cost).
#
# Batch mode: fetches recent traces from the Langfuse REST API and replays the
# evaluators over them — heuristics always, LLM-as-judge on demand. Used by
# POST /api/agent-evaluations/run.
# ============================================================================

import logging
from typing import Any, Dict, List, Optional

from backend.config import Config
from backend.core.langfuse_client import fetch_traces, score_trace
from backend.services.evaluation.evaluators import (
    TRACE_CV_EXTRACTION,
    TRACE_EVALUATORS,
    TRACE_HR_EXPLORER,
    TRACE_JOB_EVALUATION,
    EvaluatorResult,
    run_heuristics,
)
from backend.services.evaluation.llm_judge import (
    extract_agent_qa,
    judge_agent_response,
    judge_candidate_evaluation,
)

logger = logging.getLogger(__name__)


def _write_score(trace_id: str, result: EvaluatorResult) -> bool:
    """Persist one evaluator result as a Langfuse score (idempotent)."""
    data_type = "BOOLEAN" if result.name == "workflow_success" else "NUMERIC"
    return score_trace(
        trace_id,
        result.name,
        float(result.value),
        data_type=data_type,  # type: ignore[arg-type]
        comment=result.comment or None,
    )


async def evaluate_state(
    trace_name: str,
    state: Dict[str, Any],
    trace_id: Optional[str],
    *,
    use_llm_judge: Optional[bool] = None,
) -> List[EvaluatorResult]:
    """Run all evaluators applicable to one workflow run and score the trace.

    Heuristics always run (they are pure functions). The LLM judge runs when
    ``use_llm_judge`` (or the LANGFUSE_LLM_JUDGE_ENABLED default) is on and the
    workflow has a judge (job evaluation; hr_explorer response).
    """
    results = run_heuristics(trace_name, state)

    judge_on = Config.LANGFUSE_LLM_JUDGE_ENABLED if use_llm_judge is None else use_llm_judge
    if judge_on:
        if trace_name == TRACE_JOB_EVALUATION:
            results.append(await judge_candidate_evaluation(
                summary=state.get("summary", ""),
                job_description=state.get("job_description", ""),
                evaluation=state.get("evaluation") or {},
            ))
        # (hr_explorer judge only applies to fetched traces; the agent streams
        # incrementally, so its QA pair is extracted in batch mode.)

    if trace_id:
        for res in results:
            _write_score(trace_id, res)
    return results


def _state_from_trace(trace: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """LangGraph traces store the final state as the root run output."""
    output = trace.get("output")
    return output if isinstance(output, dict) else None


async def run_batch_evaluation(
    *,
    limit: int = 50,
    trace_name: Optional[str] = None,
    use_llm_judge: bool = False,
) -> Dict[str, Any]:
    """Replay evaluators over the most recent Langfuse traces.

    Returns a summary dict; every produced score is also written back to the
    corresponding trace so it shows up in the Langfuse UI.
    """
    traces = await fetch_traces(limit=limit, name=trace_name)

    evaluated = 0
    skipped = 0
    llm_judged = 0
    score_writes = 0
    per_trace: List[Dict[str, Any]] = []

    for trace in traces:
        tid = trace.get("id")
        name = trace.get("name") or ""
        state = _state_from_trace(trace)

        results: List[EvaluatorResult] = []
        reason = None
        if name not in TRACE_EVALUATORS:
            reason = f"no evaluators for trace '{name}'"
            skipped += 1
        elif not isinstance(state, dict):
            reason = "trace has no state output"
            skipped += 1
        else:
            results = run_heuristics(name, state)
            if use_llm_judge and name == TRACE_JOB_EVALUATION:
                results.append(await judge_candidate_evaluation(
                    summary=state.get("summary", ""),
                    job_description=state.get("job_description", ""),
                    evaluation=state.get("evaluation") or {},
                ))
                llm_judged += 1
            if use_llm_judge and name == TRACE_HR_EXPLORER:
                question, answer = extract_agent_qa(trace.get("input"), state)
                if answer:
                    results.append(await judge_agent_response(question, answer))
                    llm_judged += 1
            evaluated += 1

        if tid:
            for res in results:
                if _write_score(tid, res):
                    score_writes += 1

        per_trace.append({
            "trace_id": tid,
            "trace_name": name,
            "timestamp": trace.get("timestamp"),
            "scores": [
                {"name": r.name, "value": r.value, "comment": r.comment}
                for r in results
            ],
            "skipped_reason": reason,
        })

    return {
        "success": True,
        "fetched": len(traces),
        "evaluated": evaluated,
        "skipped": skipped,
        "llm_judged": llm_judged,
        "scores_written": score_writes,
        "use_llm_judge": use_llm_judge,
        "filter_trace_name": trace_name,
        "traces": per_trace,
    }
