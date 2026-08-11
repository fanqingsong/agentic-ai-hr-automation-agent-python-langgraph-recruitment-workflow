# ============================================================================
# Graph index: upsert Candidate/Job/Skill/Company/Education nodes and their
# relationships into Neo4j.
#
# All writes use MERGE so re-processing a candidate/job (batch re-import,
# re-evaluation) is idempotent. Before re-creating a candidate's/job's
# relationships, existing ones of the same type are deleted first so removed
# skills/experience entries don't linger as stale edges.
#
# Every statement here is a small, composable Cypher call executed as its own
# query rather than one large multi-UNWIND query, because UNWIND over an
# empty list yields zero rows and would silently truncate any later clauses
# chained onto the same query with WITH.
# ============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.core.neo4j_client import run_query

logger = logging.getLogger(__name__)


def normalize_skill(name: str) -> str:
    """Canonicalize a skill name for graph merging (lowercase + trim).

    Kept as a single seam so alias resolution (e.g. "K8s" -> "Kubernetes")
    can be added later without touching callers.
    """
    return (name or "").strip().lower()


async def upsert_candidate_graph(
    candidate_id: str,
    name: str,
    email: str,
    extracted_cv_data: Optional[Dict[str, Any]],
) -> None:
    """Upsert a Candidate node and its Skill/Company/Education relationships."""
    data = extracted_cv_data or {}

    await run_query(
        "MERGE (c:Candidate {candidate_id: $candidate_id}) SET c.name = $name, c.email = $email",
        candidate_id=candidate_id,
        name=name or "",
        email=email or "",
    )

    # Full replace: drop previous relationships before re-creating them from
    # the latest extracted_cv_data, so removed skills/companies don't linger.
    await run_query(
        "MATCH (c:Candidate {candidate_id: $candidate_id})-[r:HAS_SKILL|WORKED_AT|HAS_EDUCATION]->() DELETE r",
        candidate_id=candidate_id,
    )

    skills = data.get("skills", {}) or {}
    skill_names = list({
        normalize_skill(s)
        for s in (skills.get("technical_skills") or []) + (skills.get("tools") or [])
        if normalize_skill(s)
    })
    if skill_names:
        await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})
            UNWIND $skill_names AS skill_name
            MERGE (s:Skill {name: skill_name})
            MERGE (c)-[:HAS_SKILL {source: "cv_extraction"}]->(s)
            """,
            candidate_id=candidate_id,
            skill_names=skill_names,
        )

    experience: List[Dict[str, Any]] = [
        {
            "company": exp.get("company", "").strip(),
            "title": exp.get("title", ""),
            "duration": exp.get("duration", ""),
        }
        for exp in (data.get("experience") or [])
        if (exp.get("company") or "").strip()
    ]
    if experience:
        await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})
            UNWIND $experience AS exp
            MERGE (co:Company {name: exp.company})
            MERGE (c)-[:WORKED_AT {title: exp.title, duration: exp.duration}]->(co)
            """,
            candidate_id=candidate_id,
            experience=experience,
        )

    education: List[Dict[str, Any]] = [
        {
            "degree": edu.get("degree", ""),
            "institution": edu.get("institution", "").strip(),
        }
        for edu in (data.get("education") or [])
        if (edu.get("institution") or "").strip()
    ]
    if education:
        await run_query(
            """
            MATCH (c:Candidate {candidate_id: $candidate_id})
            UNWIND $education AS edu
            MERGE (e:Education {degree: edu.degree, institution: edu.institution})
            MERGE (c)-[:HAS_EDUCATION]->(e)
            """,
            candidate_id=candidate_id,
            education=education,
        )


async def upsert_job_graph(
    job_id: str,
    title: str,
    tech_skills: Optional[List[str]],
    soft_skills: Optional[List[str]],
) -> None:
    """Upsert a Job node and its REQUIRES_SKILL relationships."""
    await run_query(
        "MERGE (j:Job {job_id: $job_id}) SET j.title = $title",
        job_id=job_id,
        title=title or "",
    )

    await run_query(
        "MATCH (j:Job {job_id: $job_id})-[r:REQUIRES_SKILL]->() DELETE r",
        job_id=job_id,
    )

    tech_names = list({normalize_skill(s) for s in (tech_skills or []) if normalize_skill(s)})
    if tech_names:
        await run_query(
            """
            MATCH (j:Job {job_id: $job_id})
            UNWIND $skill_names AS skill_name
            MERGE (s:Skill {name: skill_name})
            MERGE (j)-[:REQUIRES_SKILL {skill_type: "tech"}]->(s)
            """,
            job_id=job_id,
            skill_names=tech_names,
        )

    soft_names = list({normalize_skill(s) for s in (soft_skills or []) if normalize_skill(s)})
    if soft_names:
        await run_query(
            """
            MATCH (j:Job {job_id: $job_id})
            UNWIND $skill_names AS skill_name
            MERGE (s:Skill {name: skill_name})
            MERGE (j)-[:REQUIRES_SKILL {skill_type: "soft"}]->(s)
            """,
            job_id=job_id,
            skill_names=soft_names,
        )


async def upsert_evaluation_edge(candidate_id: str, job_id: str, score: Optional[int], tag: str) -> None:
    """Upsert the (Candidate)-[:EVALUATED_FOR]->(Job) relationship for one evaluation.

    Uses MERGE on both endpoints so this can run even if the candidate/job
    node hasn't been created yet by ``upsert_candidate_graph``/``upsert_job_graph``
    (it creates a minimal stub node that later gets enriched).
    """
    await run_query(
        """
        MERGE (c:Candidate {candidate_id: $candidate_id})
        MERGE (j:Job {job_id: $job_id})
        MERGE (c)-[r:EVALUATED_FOR]->(j)
        SET r.score = $score, r.tag = $tag, r.timestamp = $timestamp
        """,
        candidate_id=candidate_id,
        job_id=job_id,
        score=score,
        tag=tag or "",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
