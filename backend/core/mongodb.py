# ============================================================================
# MONGODB CLIENT (HR candidates, job posts)
# ============================================================================

import logging
import os
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient

logger = logging.getLogger(__name__)

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncMongoClient(MONGODB_URL)


def get_mongo_db():
    """Return MongoDB database instance for ai-hr-automation."""
    return client.get_database("ai-hr-automation")


async def ensure_indexes(db) -> None:
    """Create indexes for frequently queried fields.

    Idempotent: MongoDB skips indexes that already exist. Runs on startup so
    common lookups (by user, email, batch, job, score) avoid collection scans.
    """
    specs = [
        (db.candidates, [("user_id", ASCENDING)], {}),
        (db.candidates, [("candidate_email", ASCENDING)], {}),
        (db.candidates, [("batch_id", ASCENDING)], {}),
        (db.candidates, [("file_hash", ASCENDING)], {"unique": True, "sparse": True}),
        (db.candidates, [("source_folder", ASCENDING)], {}),
        (db.candidates, [("timestamp", DESCENDING)], {}),
        (db.candidate_evaluations, [("job_id", ASCENDING), ("score", DESCENDING)], {}),
        (db.candidate_evaluations, [("candidate_id", ASCENDING), ("score", DESCENDING)], {}),
        (db.candidate_evaluations, [("candidate_id", ASCENDING), ("job_id", ASCENDING)], {"unique": True}),
        (db.hr_job_posts, [("createdAt", DESCENDING)], {}),
        (db.hr_job_posts, [("ulid", ASCENDING)], {}),
        (db.batch_imports, [("batch_id", ASCENDING)], {"unique": True}),
    ]
    for collection, keys, options in specs:
        try:
            await collection.create_index(keys, **options)
        except Exception as e:
            # Duplicate data can block a unique index; log and continue so a
            # single bad index never prevents the app from starting.
            logger.warning("Skipped index %s on %s: %s", keys, collection.name, e)
