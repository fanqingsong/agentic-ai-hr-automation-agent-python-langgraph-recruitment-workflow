# ============================================================================
# Agent evaluation: heuristic (deterministic, zero-cost) evaluators.
#
# Each evaluator maps a workflow final state (the LangGraph state dict that is
# also captured as the trace output in Langfuse) to a 0..1 score plus a short
# comment. They run automatically after every traced workflow run and can be
# replayed in batch over historical traces.
# ============================================================================

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

# Canonical Langfuse trace names (set via langfuse_trace_name metadata).
TRACE_CV_EXTRACTION = "cv-extraction"
TRACE_JOB_EVALUATION = "job-evaluation"
TRACE_HR_EXPLORER = "hr_explorer"


@dataclass
class EvaluatorResult:
    """Outcome of one evaluator; value is normalized to 0..1."""

    name: str
    value: float
    comment: str = ""


# ----------------------------------------------------------------------------
# CV extraction workflow (Graph 1)
# ----------------------------------------------------------------------------

def extraction_completeness(state: Dict[str, Any]) -> EvaluatorResult:
    """How complete the extracted CV structure is (5 weighted fields)."""
    data = state.get("extracted_cv_data") or {}
    checks = [
        bool((data.get("personal_info") or {}).get("name")),
        bool((data.get("personal_info") or {}).get("email")),
        isinstance(data.get("experience"), list) and len(data["experience"]) > 0,
        isinstance(data.get("education"), list) and len(data["education"]) > 0,
        bool(((data.get("skills") or {}).get("technical_skills") or [])),
    ]
    hits = sum(checks)
    missing = [n for n, ok in zip(
        ["name", "email", "experience", "education", "skills"], checks) if not ok]
    comment = "complete" if not missing else f"missing: {', '.join(missing)}"
    return EvaluatorResult("extraction_completeness", round(hits / len(checks), 3), comment)


def summary_quality(state: Dict[str, Any]) -> EvaluatorResult:
    """Summary is a real summary, not one of the code's fallback templates."""
    summary = (state.get("summary") or "").strip()
    if not summary:
        return EvaluatorResult("summary_quality", 0.0, "empty summary")
    if summary == "No CV data available":
        return EvaluatorResult("summary_quality", 0.0, "fallback placeholder summary")
    if summary.startswith("Summary for "):
        return EvaluatorResult("summary_quality", 0.2, "template fallback summary")
    if len(summary) < 50:
        return EvaluatorResult("summary_quality", 0.3, f"very short ({len(summary)} chars)")
    if len(summary) > 3000:
        return EvaluatorResult("summary_quality", 0.7, f"very long ({len(summary)} chars)")
    return EvaluatorResult("summary_quality", 1.0, f"{len(summary)} chars")


# ----------------------------------------------------------------------------
# Job evaluation workflow (Graph 2)
# ----------------------------------------------------------------------------

def evaluation_plausibility(state: Dict[str, Any]) -> EvaluatorResult:
    """Evaluation score is in range, tag matches the score band, reasoning/lists exist."""
    evaluation = state.get("evaluation") or {}
    score = state.get("evaluation_score")
    tag = state.get("tag") or ""

    value = 0.0
    notes: List[str] = []

    if isinstance(score, (int, float)) and 1 <= score <= 100:
        value += 0.4
    else:
        notes.append(f"score out of range: {score}")

    expected_tag = (
        "high_potential" if (score or 0) >= 70
        else "moderate" if (score or 0) >= 50
        else "low_potential"
    )
    if tag == expected_tag:
        value += 0.3
    else:
        notes.append(f"tag '{tag}' inconsistent with score {score} (expected '{expected_tag}')")

    reasoning = evaluation.get("reasoning") or ""
    if len(reasoning) > 20 and "Evaluation failed" not in reasoning and "Insufficient data" not in reasoning:
        value += 0.2
    else:
        notes.append("no substantive reasoning")

    if isinstance(evaluation.get("strengths"), list) and isinstance(evaluation.get("gaps"), list):
        value += 0.1
    else:
        notes.append("strengths/gaps lists missing")

    return EvaluatorResult("evaluation_plausibility", round(value, 3), "; ".join(notes) or "plausible")


def skills_match_coverage(state: Dict[str, Any]) -> EvaluatorResult:
    """Share of required job skills the candidate matched."""
    match = state.get("skills_match") or {}
    strong = len(match.get("strong") or [])
    missing = len(match.get("missing") or [])
    total = strong + missing
    if total == 0:
        return EvaluatorResult("skills_match_coverage", 0.5, "no skills-match data")
    ratio = strong / total
    return EvaluatorResult(
        "skills_match_coverage",
        round(ratio, 3),
        f"{strong}/{total} required skills matched",
    )


# ----------------------------------------------------------------------------
# Any workflow
# ----------------------------------------------------------------------------

def workflow_success(state: Dict[str, Any]) -> EvaluatorResult:
    """BOOLEAN: did the workflow complete without recorded errors."""
    errors = state.get("errors") or []
    if errors:
        return EvaluatorResult("workflow_success", 0.0, f"{len(errors)} error(s): {str(errors[0])[:200]}")
    return EvaluatorResult("workflow_success", 1.0, "no errors")


# ----------------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------------

EvaluatorFn = Callable[[Dict[str, Any]], EvaluatorResult]

HEURISTIC_EVALUATORS: Dict[str, EvaluatorFn] = {
    "extraction_completeness": extraction_completeness,
    "summary_quality": summary_quality,
    "evaluation_plausibility": evaluation_plausibility,
    "skills_match_coverage": skills_match_coverage,
    "workflow_success": workflow_success,
}

# Which heuristic evaluators apply to which trace name.
TRACE_EVALUATORS: Dict[str, List[str]] = {
    TRACE_CV_EXTRACTION: ["extraction_completeness", "summary_quality", "workflow_success"],
    TRACE_JOB_EVALUATION: ["evaluation_plausibility", "skills_match_coverage", "workflow_success"],
    TRACE_HR_EXPLORER: [],  # chat agent: only LLM-judge evaluation applies (see llm_judge.py)
}


def run_heuristics(trace_name: str, state: Dict[str, Any]) -> List[EvaluatorResult]:
    """Run the registered heuristic evaluators for one trace/workflow."""
    results = []
    for evaluator_name in TRACE_EVALUATORS.get(trace_name, []):
        fn = HEURISTIC_EVALUATORS.get(evaluator_name)
        if fn is None:
            continue
        try:
            results.append(fn(state))
        except Exception as e:
            logger.warning("Evaluator '%s' failed: %s", evaluator_name, e)
    return results
