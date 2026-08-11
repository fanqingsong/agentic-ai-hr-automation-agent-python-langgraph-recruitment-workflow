# ============================================================================
# NEO4J CLIENT (knowledge graph: Candidate/Job/Skill/Company/Education)
# ============================================================================

import logging

from neo4j import AsyncGraphDatabase

from backend.config import Config

logger = logging.getLogger(__name__)

driver = AsyncGraphDatabase.driver(
    Config.NEO4J_URI,
    auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD),
)

_CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate) REQUIRE c.candidate_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (co:Company) REQUIRE co.name IS UNIQUE",
]


async def ensure_constraints() -> None:
    """Create uniqueness constraints for core node labels.

    Idempotent (``IF NOT EXISTS``). Runs on startup so MERGE-based writes from
    the sync pipeline never create duplicate Candidate/Job/Skill/Company
    nodes. A single failed constraint (e.g. Neo4j unreachable) must not block
    API startup; MongoDB remains the source of truth.
    """
    try:
        async with driver.session() as session:
            for statement in _CONSTRAINTS:
                await session.run(statement)
        logger.info("Neo4j constraints ensured")
    except Exception as e:
        logger.warning("Could not ensure Neo4j constraints: %s", e)


async def run_query(query: str, **params) -> list:
    """Run a Cypher query and return the list of records as dicts."""
    async with driver.session() as session:
        result = await session.run(query, **params)
        return [record.data() async for record in result]


async def ping() -> bool:
    """Best-effort connectivity check for /health."""
    try:
        async with driver.session() as session:
            await session.run("RETURN 1")
        return True
    except Exception as e:
        logger.warning("Neo4j ping failed: %s", e)
        return False
