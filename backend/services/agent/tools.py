# ============================================================================
# Read-only tools for the HR explorer Deep Agent.
# Wraps MongoDB / Qdrant / Neo4j query helpers and returns JSON strings.
# ============================================================================

import json
from typing import Any, Optional

from backend.config import Config
from backend.services.knowledge import graph_query, mongo_query, vector_index


def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


async def lookup_candidate(candidate_id: str) -> str:
    """Look up one candidate by MongoDB candidate_id and return a truncated profile summary."""
    return _dumps(await mongo_query.get_candidate(candidate_id))


async def lookup_job(job_id: str) -> str:
    """Look up one job by MongoDB job_id and return a truncated job summary."""
    return _dumps(await mongo_query.get_job(job_id))


async def list_candidates_filtered(
    name_contains: str = "",
    skill_contains: str = "",
    limit: int = 10,
) -> str:
    """List candidates from MongoDB with optional name or skill substring filters."""
    return _dumps(
        await mongo_query.list_candidates(
            name_contains=name_contains or None,
            skill_contains=skill_contains or None,
            limit=limit,
        )
    )


async def list_jobs_filtered(title_contains: str = "", limit: int = 10) -> str:
    """List jobs from MongoDB with an optional title substring filter."""
    return _dumps(await mongo_query.list_jobs(title_contains=title_contains or None, limit=limit))


async def get_candidate_job_evaluation(
    candidate_id: str = "",
    job_id: str = "",
    min_score: int = 0,
    limit: int = 15,
) -> str:
    """Fetch evaluation records from candidate_evaluations for a candidate and/or job."""
    return _dumps(
        await mongo_query.get_evaluations(
            candidate_id=candidate_id or None,
            job_id=job_id or None,
            min_score=min_score or None,
            limit=limit,
        )
    )


async def semantic_search_candidates(query: str, top_k: int = 8) -> str:
    """Semantically search candidate CV chunks in Qdrant (summary/experience/skills)."""
    try:
        hits = await vector_index.search(
            Config.QDRANT_COLLECTION_CANDIDATES,
            query_text=query,
            top_k=max(1, min(int(top_k or 8), 20)),
        )
        compact = [
            {
                "score": round(float(h.get("score") or 0), 4),
                "candidate_id": (h.get("payload") or {}).get("candidate_id"),
                "chunk_type": (h.get("payload") or {}).get("chunk_type"),
                "text": ((h.get("payload") or {}).get("text") or "")[:400],
            }
            for h in hits
        ]
        return _dumps({"query": query, "total_returned": len(compact), "hits": compact})
    except Exception as e:
        return _dumps({"error": f"Qdrant candidate search failed: {e}"})


async def semantic_search_jobs(query: str, top_k: int = 8) -> str:
    """Semantically search job description chunks in Qdrant."""
    try:
        hits = await vector_index.search(
            Config.QDRANT_COLLECTION_JOBS,
            query_text=query,
            top_k=max(1, min(int(top_k or 8), 20)),
        )
        compact = [
            {
                "score": round(float(h.get("score") or 0), 4),
                "job_id": (h.get("payload") or {}).get("job_id"),
                "chunk_type": (h.get("payload") or {}).get("chunk_type"),
                "text": ((h.get("payload") or {}).get("text") or "")[:400],
            }
            for h in hits
        ]
        return _dumps({"query": query, "total_returned": len(compact), "hits": compact})
    except Exception as e:
        return _dumps({"error": f"Qdrant job search failed: {e}"})


async def find_candidates_by_skill(skill: str, limit: int = 15) -> str:
    """Find candidates linked to a skill in the Neo4j knowledge graph."""
    return _dumps(await graph_query.candidates_with_skill(skill, limit=limit))


async def find_jobs_by_skill(skill: str, limit: int = 15) -> str:
    """Find jobs that require a skill in the Neo4j knowledge graph."""
    return _dumps(await graph_query.jobs_requiring_skill(skill, limit=limit))


async def explore_candidate_graph(candidate_id: str) -> str:
    """Explore a candidate's Neo4j neighborhood: skills, companies, education, evaluations."""
    return _dumps(await graph_query.candidate_neighborhood(candidate_id))


async def compare_candidate_job_skills(candidate_id: str, job_id: str) -> str:
    """Compare candidate skills vs job required skills via Neo4j (overlap and missing)."""
    return _dumps(await graph_query.skill_path_between(candidate_id, job_id))


async def find_shared_company_candidates(
    candidate_id: str,
    skill: str = "",
    limit: int = 15,
) -> str:
    """Find other candidates who shared employers with this candidate (optional skill filter)."""
    return _dumps(
        await graph_query.shared_company_candidates(
            candidate_id,
            skill=skill or None,
            limit=limit,
        )
    )


ALL_TOOLS = [
    lookup_candidate,
    lookup_job,
    list_candidates_filtered,
    list_jobs_filtered,
    get_candidate_job_evaluation,
    semantic_search_candidates,
    semantic_search_jobs,
    find_candidates_by_skill,
    find_jobs_by_skill,
    explore_candidate_graph,
    compare_candidate_job_skills,
    find_shared_company_candidates,
]

CANDIDATE_TOOLS = [
    lookup_candidate,
    list_candidates_filtered,
    semantic_search_candidates,
    find_candidates_by_skill,
    explore_candidate_graph,
    find_shared_company_candidates,
]

JOB_TOOLS = [
    lookup_job,
    list_jobs_filtered,
    semantic_search_jobs,
    find_jobs_by_skill,
]

MATCHING_TOOLS = [
    lookup_candidate,
    lookup_job,
    get_candidate_job_evaluation,
    semantic_search_candidates,
    semantic_search_jobs,
    compare_candidate_job_skills,
    find_candidates_by_skill,
    find_jobs_by_skill,
]
