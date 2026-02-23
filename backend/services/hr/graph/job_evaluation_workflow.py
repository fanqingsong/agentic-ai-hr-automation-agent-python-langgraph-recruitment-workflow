# ============================================================================
# Graph2: Job evaluation workflow (one job + one candidate from DB)
# ============================================================================

from langgraph.graph import StateGraph, END
from langgraph.types import RetryPolicy

from backend.schemas.hr import JobEvaluationState
from backend.services.hr.graph.nodes import (
    extract_job_skills_node,
    evaluate_candidate_node,
    skills_match_node,
    score_decision_node,
)


def create_job_evaluation_workflow():
    """Build and compile the job evaluation graph (no upload, no notifications).

    Graph topology:
      [extract_job_skills_node] -> [evaluate] -> [skills_match_node] -> [score_decision] -> END
    """
    graph = StateGraph(JobEvaluationState)

    retry_once = RetryPolicy(max_attempts=2)
    graph.add_node("extract_job_skills_node", extract_job_skills_node)
    graph.add_node("evaluate", evaluate_candidate_node, retry_policy=retry_once)
    graph.add_node("skills_match_node", skills_match_node)
    graph.add_node("score_decision", score_decision_node)

    graph.set_entry_point("extract_job_skills_node")
    graph.add_edge("extract_job_skills_node", "evaluate")
    graph.add_edge("evaluate", "skills_match_node")
    graph.add_edge("skills_match_node", "score_decision")
    graph.add_edge("score_decision", END)

    return graph.compile()
