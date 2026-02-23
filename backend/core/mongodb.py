# ============================================================================
# MONGODB CLIENT (HR candidates, job posts)
# ============================================================================

import os
from pymongo import AsyncMongoClient

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncMongoClient(MONGODB_URL)


def get_mongo_db():
    """Return MongoDB database instance for ai-hr-automation."""
    return client.get_database("ai-hr-automation")
