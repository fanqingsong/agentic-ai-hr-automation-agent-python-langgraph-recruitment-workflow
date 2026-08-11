# ============================================================================
# Knowledge index nodes: sync Qdrant + Neo4j after MongoDB writes.
#
# These nodes run *after* the MongoDB write in each graph, so a failure here
# never blocks the primary persistence step that already succeeded. Any
# errors are appended to state["errors"] for visibility but do not raise.
# ============================================================================

import logging
from typing import Any, Dict

from backend.services.knowledge import sync

logger = logging.getLogger(__name__)


async def index_candidate_knowledge_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Graph1 node: index the just-saved candidate into Qdrant + Neo4j."""
    candidate_id = state.get("candidate_id")
    if not candidate_id:
        # save_candidate_to_mongodb failed upstream; nothing to index.
        return state

    try:
        result = await sync.index_candidate(
            candidate_id=candidate_id,
            name=state.get("candidate_name", ""),
            email=state.get("candidate_email", ""),
            extracted_cv_data=state.get("extracted_cv_data", {}),
            summary=state.get("summary", ""),
        )
        for err in result.get("errors", []):
            state.setdefault("errors", []).append(err)
    except Exception as e:
        error_msg = f"Knowledge index error for candidate {candidate_id}: {str(e)}"
        logger.warning(error_msg)
        state.setdefault("errors", []).append(error_msg)

    return state


async def index_evaluation_edge_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Graph2 node: write the (Candidate)-[:EVALUATED_FOR]->(Job) edge into Neo4j."""
    candidate_id = state.get("candidate_id")
    job_id = state.get("job_id")
    if not candidate_id or not job_id:
        return state

    try:
        result = await sync.index_evaluation(
            candidate_id=candidate_id,
            job_id=job_id,
            score=state.get("evaluation_score"),
            tag=state.get("tag", ""),
        )
        for err in result.get("errors", []):
            state.setdefault("errors", []).append(err)
    except Exception as e:
        error_msg = f"Knowledge index error for evaluation {candidate_id}/{job_id}: {str(e)}"
        logger.warning(error_msg)
        state.setdefault("errors", []).append(error_msg)

    return state
