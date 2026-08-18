# ============================================================================
# Unit tests for the heuristic agent evaluators (pure functions, no LLM).
# Run: uv run pytest tests/test_evaluators.py -v
# ============================================================================

import pytest

from backend.services.evaluation.evaluators import (
    HEURISTIC_EVALUATORS,
    TRACE_CV_EXTRACTION,
    TRACE_EVALUATORS,
    TRACE_HR_EXPLORER,
    TRACE_JOB_EVALUATION,
    evaluation_plausibility,
    extraction_completeness,
    run_heuristics,
    skills_match_coverage,
    summary_quality,
    workflow_success,
)


def _full_cv_state():
    return {
        "extracted_cv_data": {
            "personal_info": {"name": "Alice", "email": "alice@example.com"},
            "experience": [{"title": "Engineer", "company": "Acme"}],
            "education": [{"degree": "BSc"}],
            "skills": {"technical_skills": ["Python"], "tools": []},
        },
        "summary": "Alice is a Python engineer with 5 years of experience at Acme building data platforms.",
        "errors": [],
    }


def _full_eval_state():
    return {
        "evaluation": {
            "score": 82,
            "reasoning": "Strong overlap on Python and data engineering; led similar projects.",
            "strengths": ["Python"],
            "gaps": ["Kubernetes"],
            "decision": "hire",
        },
        "evaluation_score": 82,
        "tag": "high_potential",
        "skills_match": {"strong": ["python", "sql"], "partial": [], "missing": ["kubernetes"]},
        "errors": [],
    }


# ---------------------------------------------------------------------------
# extraction_completeness
# ---------------------------------------------------------------------------

def test_extraction_completeness_full():
    result = extraction_completeness(_full_cv_state())
    assert result.value == 1.0
    assert result.comment == "complete"


def test_extraction_completeness_empty():
    result = extraction_completeness({"extracted_cv_data": {}})
    assert result.value == 0.0
    assert "email" in result.comment


def test_extraction_completeness_partial():
    state = _full_cv_state()
    state["extracted_cv_data"]["education"] = []
    state["extracted_cv_data"].pop("skills")
    result = extraction_completeness(state)
    assert result.value == pytest.approx(3 / 5)


# ---------------------------------------------------------------------------
# summary_quality
# ---------------------------------------------------------------------------

def test_summary_quality_good():
    assert summary_quality(_full_cv_state()).value == 1.0


def test_summary_quality_fallback_markers():
    assert summary_quality({"summary": "No CV data available"}).value == 0.0
    assert summary_quality({"summary": "Summary for Alice"}).value == 0.2
    assert summary_quality({"summary": ""}).value == 0.0


def test_summary_quality_lengths():
    assert summary_quality({"summary": "short text"}).value == 0.3
    assert summary_quality({"summary": "x" * 4000}).value == 0.7


# ---------------------------------------------------------------------------
# evaluation_plausibility
# ---------------------------------------------------------------------------

def test_evaluation_plausibility_consistent():
    assert evaluation_plausibility(_full_eval_state()).value == 1.0


def test_evaluation_plausibility_tag_mismatch():
    state = _full_eval_state()
    state["tag"] = "moderate"  # score 82 should be high_potential
    result = evaluation_plausibility(state)
    assert result.value == pytest.approx(0.7)
    assert "inconsistent" in result.comment


@pytest.mark.parametrize("score,expected_tag", [
    (82, "high_potential"),
    (70, "high_potential"),
    (69, "moderate"),
    (50, "moderate"),
    (49, "low_potential"),
])
def test_evaluation_plausibility_tag_bands(score, expected_tag):
    state = _full_eval_state()
    state["evaluation_score"] = score
    state["tag"] = expected_tag
    assert evaluation_plausibility(state).value == 1.0


def test_evaluation_plausibility_error_reasoning():
    state = _full_eval_state()
    state["evaluation"]["reasoning"] = "Evaluation failed: boom"
    result = evaluation_plausibility(state)
    assert result.value == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# skills_match_coverage
# ---------------------------------------------------------------------------

def test_skills_match_coverage_ratio():
    result = skills_match_coverage(_full_eval_state())
    assert result.value == pytest.approx(2 / 3, abs=0.001)
    assert "2/3" in result.comment


def test_skills_match_coverage_no_data():
    assert skills_match_coverage({}).value == 0.5


# ---------------------------------------------------------------------------
# workflow_success
# ---------------------------------------------------------------------------

def test_workflow_success_ok():
    assert workflow_success({"errors": []}).value == 1.0


def test_workflow_success_errors():
    result = workflow_success({"errors": ["LLM timeout"]})
    assert result.value == 0.0
    assert "LLM timeout" in result.comment


# ---------------------------------------------------------------------------
# registry / runner
# ---------------------------------------------------------------------------

def test_registry_maps_traces_to_evaluators():
    assert set(TRACE_EVALUATORS[TRACE_CV_EXTRACTION]) == {
        "extraction_completeness", "summary_quality", "workflow_success"}
    assert set(TRACE_EVALUATORS[TRACE_JOB_EVALUATION]) == {
        "evaluation_plausibility", "skills_match_coverage", "workflow_success"}
    assert TRACE_EVALUATORS[TRACE_HR_EXPLORER] == []
    for names in TRACE_EVALUATORS.values():
        for n in names:
            assert n in HEURISTIC_EVALUATORS


def test_run_heuristics_per_trace():
    cv = run_heuristics(TRACE_CV_EXTRACTION, _full_cv_state())
    assert [r.name for r in cv] == TRACE_EVALUATORS[TRACE_CV_EXTRACTION]
    assert all(r.value == 1.0 for r in cv)

    ev = run_heuristics(TRACE_JOB_EVALUATION, _full_eval_state())
    assert len(ev) == 3

    # Unknown trace names get no evaluators; errors never raise.
    assert run_heuristics("unknown", {}) == []
    assert run_heuristics(TRACE_CV_EXTRACTION, None) == []
