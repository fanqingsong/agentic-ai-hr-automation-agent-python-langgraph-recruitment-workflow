# ============================================================================
# Backfill script: index existing MongoDB candidates/jobs/evaluations into
# Qdrant (vectors) and Neo4j (graph).
#
# Run once after standing up the Qdrant/Neo4j services so historical data
# (created before the knowledge-store sync pipeline existed) is not missing
# from the derived stores. Safe to re-run: every sync.* call is idempotent.
#
# Usage:
#   uv run python -m backend.scripts.backfill_knowledge_stores
#   uv run python -m backend.scripts.backfill_knowledge_stores --only candidates
# ============================================================================

import argparse
import asyncio
import logging

from backend.core.mongodb import get_mongo_db
from backend.core.neo4j_client import ensure_constraints
from backend.core.qdrant_client import ensure_collections
from backend.services.knowledge import sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def backfill_candidates(db) -> None:
    query = {"$or": [{"extracted_cv_data": {"$exists": True, "$ne": {}}}, {"summary": {"$exists": True, "$ne": ""}}]}
    cursor = db.candidates.find(query)
    ok, failed = 0, 0
    async for doc in cursor:
        candidate_id = str(doc.get("_id"))
        result = await sync.index_candidate(
            candidate_id=candidate_id,
            name=doc.get("candidate_name", ""),
            email=doc.get("candidate_email", ""),
            extracted_cv_data=doc.get("extracted_cv_data", {}),
            summary=doc.get("summary", ""),
        )
        if result.get("errors"):
            failed += 1
            logger.warning("Candidate %s: %s", candidate_id, result["errors"])
        else:
            ok += 1
    logger.info("Candidates backfilled: %d ok, %d failed", ok, failed)


async def backfill_jobs(db) -> None:
    from backend.services.hr.graph.nodes.job_skills import extract_job_skills

    cursor = db.hr_job_posts.find({})
    ok, failed = 0, 0
    async for doc in cursor:
        job_id = str(doc.get("_id"))
        ja = doc.get("jobApplication") or doc.get("job_application") or {}
        title = doc.get("job_title") or ja.get("title", "")
        description = doc.get("job_description") or ja.get("description", "")

        cached = doc.get("job_skills") or {}
        if cached.get("tech_skills") or cached.get("soft_skills"):
            tech_skills, soft_skills = cached.get("tech_skills", []), cached.get("soft_skills", [])
        else:
            job_skills = await extract_job_skills(description)
            tech_skills, soft_skills = job_skills.tech_skills, job_skills.soft_skills
            try:
                await db.hr_job_posts.update_one({"_id": doc["_id"]}, {"$set": {"job_skills": job_skills.to_dict()}})
            except Exception as e:
                logger.warning("Could not cache job_skills for job %s: %s", job_id, e)

        result = await sync.index_job(
            job_id=job_id,
            title=title,
            description=description,
            tech_skills=tech_skills,
            soft_skills=soft_skills,
        )
        if result.get("errors"):
            failed += 1
            logger.warning("Job %s: %s", job_id, result["errors"])
        else:
            ok += 1
    logger.info("Jobs backfilled: %d ok, %d failed", ok, failed)


async def backfill_evaluations(db) -> None:
    cursor = db.candidate_evaluations.find({})
    ok, failed = 0, 0
    async for doc in cursor:
        result = await sync.index_evaluation(
            candidate_id=doc.get("candidate_id", ""),
            job_id=doc.get("job_id", ""),
            score=doc.get("score"),
            tag=doc.get("tag", ""),
        )
        if result.get("errors"):
            failed += 1
            logger.warning("Evaluation %s/%s: %s", doc.get("candidate_id"), doc.get("job_id"), result["errors"])
        else:
            ok += 1
    logger.info("Evaluations backfilled: %d ok, %d failed", ok, failed)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Qdrant/Neo4j from existing MongoDB data.")
    parser.add_argument(
        "--only",
        choices=["candidates", "jobs", "evaluations"],
        help="Backfill only this entity type (default: all, in dependency order).",
    )
    args = parser.parse_args()

    db = get_mongo_db()

    logger.info("Ensuring Qdrant collections and Neo4j constraints...")
    await ensure_collections()
    await ensure_constraints()

    if args.only in (None, "candidates"):
        logger.info("Backfilling candidates...")
        await backfill_candidates(db)
    if args.only in (None, "jobs"):
        logger.info("Backfilling jobs...")
        await backfill_jobs(db)
    if args.only in (None, "evaluations"):
        logger.info("Backfilling evaluations...")
        await backfill_evaluations(db)

    logger.info("Backfill complete.")


if __name__ == "__main__":
    asyncio.run(main())
