# ============================================================================
# Sync orchestrator: single entry point that keeps Qdrant (vectors) and
# Neo4j (graph) consistent with MongoDB (the source of truth).
#
# Every function here is a plain async function with no FastAPI/LangGraph
# coupling, so it can be called from:
#   - LangGraph nodes (Graph1 candidate persistence, Graph2 evaluation)
#   - Plain API routes (job creation)
#   - The one-off backfill script
#   - A future Agent tool layer
#
# Failures in either derived store are caught and reported as a list of
# warning strings; callers should log them but never let them fail the
# primary MongoDB write that already succeeded.
# ============================================================================

import logging
from typing import Any, Dict, List, Optional

from backend.services.knowledge import graph_index, vector_index
from backend.services.knowledge.chunking import candidate_to_chunks, job_to_chunks

logger = logging.getLogger(__name__)


async def index_candidate(
    candidate_id: str,
    name: str,
    email: str,
    extracted_cv_data: Optional[Dict[str, Any]],
    summary: str,
) -> Dict[str, List[str]]:
    """Index one candidate into Qdrant (chunks) and Neo4j (entities/relations).

    Returns {"errors": [...]}; an empty list means both stores succeeded.
    """
    errors: List[str] = []
    if not candidate_id:
        return {"errors": ["index_candidate: missing candidate_id"]}

    try:
        chunks = candidate_to_chunks(extracted_cv_data, summary)
        await vector_index.upsert_candidate_vectors(candidate_id, chunks)
    except Exception as e:
        msg = f"Vector index failed for candidate {candidate_id}: {e}"
        logger.warning(msg)
        errors.append(msg)

    try:
        await graph_index.upsert_candidate_graph(candidate_id, name, email, extracted_cv_data)
    except Exception as e:
        msg = f"Graph index failed for candidate {candidate_id}: {e}"
        logger.warning(msg)
        errors.append(msg)

    return {"errors": errors}


async def index_job(
    job_id: str,
    title: str,
    description: str,
    tech_skills: Optional[List[str]] = None,
    soft_skills: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """Index one job into Qdrant (JD chunks) and Neo4j (Job + REQUIRES_SKILL)."""
    errors: List[str] = []
    if not job_id:
        return {"errors": ["index_job: missing job_id"]}

    try:
        chunks = job_to_chunks(description)
        await vector_index.upsert_job_vectors(job_id, chunks)
    except Exception as e:
        msg = f"Vector index failed for job {job_id}: {e}"
        logger.warning(msg)
        errors.append(msg)

    try:
        await graph_index.upsert_job_graph(job_id, title, tech_skills, soft_skills)
    except Exception as e:
        msg = f"Graph index failed for job {job_id}: {e}"
        logger.warning(msg)
        errors.append(msg)

    return {"errors": errors}


async def index_evaluation(candidate_id: str, job_id: str, score: Optional[int], tag: str) -> Dict[str, List[str]]:
    """Index one candidate-job evaluation as an EVALUATED_FOR edge in Neo4j."""
    errors: List[str] = []
    if not candidate_id or not job_id:
        return {"errors": ["index_evaluation: missing candidate_id or job_id"]}

    try:
        await graph_index.upsert_evaluation_edge(candidate_id, job_id, score, tag)
    except Exception as e:
        msg = f"Graph index failed for evaluation {candidate_id}/{job_id}: {e}"
        logger.warning(msg)
        errors.append(msg)

    return {"errors": errors}
