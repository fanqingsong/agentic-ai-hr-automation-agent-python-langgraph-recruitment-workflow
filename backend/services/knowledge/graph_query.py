# ============================================================================
# Neo4j read-only graph queries for the HR explorer Agent.
# ============================================================================

import logging
from typing import Any, Dict, List, Optional

from backend.core.neo4j_client import run_query
from backend.services.knowledge.graph_index import normalize_skill

logger = logging.getLogger(__name__)


async def candidates_with_skill(skill: str, limit: int = 15) -> Dict[str, Any]:
    """Find candidates that HAVE_SKILL the given skill name."""
    try:
        skill_name = normalize_skill(skill)
        if not skill_name:
            return {"error": "skill is required"}
        limit = max(1, min(int(limit or 15), 30))
        rows = await run_query(
            """
            MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill {name: $skill_name})
            RETURN c.candidate_id AS candidate_id, c.name AS name, c.email AS email, s.name AS skill
            LIMIT $limit
            """,
            skill_name=skill_name,
            limit=limit,
        )
        return {"skill": skill_name, "total_returned": len(rows), "candidates": rows}
    except Exception as e:
        logger.warning("candidates_with_skill failed: %s", e)
        return {"error": f"Neo4j unavailable or query failed: {e}"}


async def jobs_requiring_skill(skill: str, limit: int = 15) -> Dict[str, Any]:
    """Find jobs that REQUIRE_SKILL the given skill name."""
    try:
        skill_name = normalize_skill(skill)
        if not skill_name:
            return {"error": "skill is required"}
        limit = max(1, min(int(limit or 15), 30))
        rows = await run_query(
            """
            MATCH (j:Job)-[r:REQUIRES_SKILL]->(s:Skill {name: $skill_name})
            RETURN j.job_id AS job_id, j.title AS title, r.skill_type AS skill_type, s.name AS skill
            LIMIT $limit
            """,
            skill_name=skill_name,
            limit=limit,
        )
        return {"skill": skill_name, "total_returned": len(rows), "jobs": rows}
    except Exception as e:
        logger.warning("jobs_requiring_skill failed: %s", e)
        return {"error": f"Neo4j unavailable or query failed: {e}"}


async def candidate_neighborhood(candidate_id: str) -> Dict[str, Any]:
    """Return skills, companies, and education linked to a candidate."""
    try:
        if not candidate_id:
            return {"error": "candidate_id is required"}
        skills = await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})-[:HAS_SKILL]->(s:Skill)
            RETURN s.name AS skill
            ORDER BY s.name
            LIMIT 50
            """,
            candidate_id=candidate_id,
        )
        companies = await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})-[r:WORKED_AT]->(co:Company)
            RETURN co.name AS company, r.title AS title, r.duration AS duration
            LIMIT 20
            """,
            candidate_id=candidate_id,
        )
        education = await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})-[:HAS_EDUCATION]->(e:Education)
            RETURN e.degree AS degree, e.institution AS institution
            LIMIT 10
            """,
            candidate_id=candidate_id,
        )
        evaluations = await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})-[r:EVALUATED_FOR]->(j:Job)
            RETURN j.job_id AS job_id, j.title AS title, r.score AS score, r.tag AS tag
            ORDER BY r.score DESC
            LIMIT 15
            """,
            candidate_id=candidate_id,
        )
        return {
            "candidate_id": candidate_id,
            "skills": [r.get("skill") for r in skills if r.get("skill")],
            "companies": companies,
            "education": education,
            "evaluations": evaluations,
        }
    except Exception as e:
        logger.warning("candidate_neighborhood failed: %s", e)
        return {"error": f"Neo4j unavailable or query failed: {e}"}


async def skill_path_between(candidate_id: str, job_id: str) -> Dict[str, Any]:
    """Compare candidate skills vs job required skills (overlap / missing)."""
    try:
        if not candidate_id or not job_id:
            return {"error": "candidate_id and job_id are required"}
        rows = await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})
            MATCH (j:Job {job_id: $job_id})
            OPTIONAL MATCH (c)-[:HAS_SKILL]->(cs:Skill)
            OPTIONAL MATCH (j)-[req:REQUIRES_SKILL]->(js:Skill)
            WITH collect(DISTINCT cs.name) AS candidate_skills,
                 collect(DISTINCT {name: js.name, skill_type: req.skill_type}) AS job_skills
            RETURN candidate_skills, job_skills
            """,
            candidate_id=candidate_id,
            job_id=job_id,
        )
        if not rows:
            return {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "overlap": [],
                "missing": [],
                "candidate_only": [],
            }
        candidate_skills = set(rows[0].get("candidate_skills") or [])
        job_skill_rows = rows[0].get("job_skills") or []
        job_skills = {item.get("name") for item in job_skill_rows if item and item.get("name")}
        overlap = sorted(candidate_skills & job_skills)
        missing = sorted(job_skills - candidate_skills)
        candidate_only = sorted(candidate_skills - job_skills)
        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "overlap": overlap,
            "missing": missing,
            "candidate_only": candidate_only[:30],
            "job_skill_details": [x for x in job_skill_rows if x and x.get("name")][:40],
        }
    except Exception as e:
        logger.warning("skill_path_between failed: %s", e)
        return {"error": f"Neo4j unavailable or query failed: {e}"}


async def shared_company_candidates(
    candidate_id: str,
    skill: Optional[str] = None,
    limit: int = 15,
) -> Dict[str, Any]:
    """Find other candidates who worked at the same companies (optional skill filter)."""
    try:
        if not candidate_id:
            return {"error": "candidate_id is required"}
        limit = max(1, min(int(limit or 15), 30))
        skill_name = normalize_skill(skill) if skill else None
        if skill_name:
            rows = await run_query(
                """
                MATCH (c:Candidate {candidate_id: $candidate_id})-[:WORKED_AT]->(co:Company)
                      <-[:WORKED_AT]-(other:Candidate)
                WHERE other.candidate_id <> $candidate_id
                MATCH (other)-[:HAS_SKILL]->(s:Skill {name: $skill_name})
                RETURN DISTINCT other.candidate_id AS candidate_id,
                       other.name AS name,
                       collect(DISTINCT co.name) AS shared_companies,
                       s.name AS skill
                LIMIT $limit
                """,
                candidate_id=candidate_id,
                skill_name=skill_name,
                limit=limit,
            )
        else:
            rows = await run_query(
                """
                MATCH (c:Candidate {candidate_id: $candidate_id})-[:WORKED_AT]->(co:Company)
                      <-[:WORKED_AT]-(other:Candidate)
                WHERE other.candidate_id <> $candidate_id
                RETURN DISTINCT other.candidate_id AS candidate_id,
                       other.name AS name,
                       collect(DISTINCT co.name) AS shared_companies
                LIMIT $limit
                """,
                candidate_id=candidate_id,
                limit=limit,
            )
        return {
            "seed_candidate_id": candidate_id,
            "skill_filter": skill_name,
            "total_returned": len(rows),
            "candidates": rows,
        }
    except Exception as e:
        logger.warning("shared_company_candidates failed: %s", e)
        return {"error": f"Neo4j unavailable or query failed: {e}"}
