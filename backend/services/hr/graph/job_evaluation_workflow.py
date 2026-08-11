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
    index_evaluation_edge_node,
)


def create_job_evaluation_workflow():
    """Build and compile the job evaluation graph (no upload, no notifications).

    Graph topology:
      [extract_job_skills_node] -> [evaluate] -> [skills_match_node] -> [score_decision]
        -> [index_evaluation_edge] -> END

    The last node writes the (Candidate)-[:EVALUATED_FOR]->(Job) edge into
    Neo4j. This is additive: a failure there is recorded in state["errors"]
    and never blocks the score/decision already computed above.
    """
    graph = StateGraph(JobEvaluationState)

    retry_once = RetryPolicy(max_attempts=2)
    graph.add_node("extract_job_skills_node", extract_job_skills_node)
    graph.add_node("evaluate", evaluate_candidate_node, retry_policy=retry_once)
    graph.add_node("skills_match_node", skills_match_node)
    graph.add_node("score_decision", score_decision_node)
    graph.add_node("index_evaluation_edge", index_evaluation_edge_node)

    graph.set_entry_point("extract_job_skills_node")
    graph.add_edge("extract_job_skills_node", "evaluate")
    graph.add_edge("evaluate", "skills_match_node")
    graph.add_edge("skills_match_node", "score_decision")
    graph.add_edge("score_decision", "index_evaluation_edge")
    graph.add_edge("index_evaluation_edge", END)

    return graph.compile()
