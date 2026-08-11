# ============================================================================
# QDRANT CLIENT (vector search: candidate/job chunk embeddings)
# ============================================================================

import logging

from qdrant_client import AsyncQdrantClient, models

from backend.config import Config

logger = logging.getLogger(__name__)

client = AsyncQdrantClient(
    url=Config.QDRANT_URL,
    api_key=Config.QDRANT_API_KEY or None,
)


async def ensure_collections() -> None:
    """Create the candidate/job chunk collections if they don't exist yet.

    Idempotent: safe to call on every startup. Distance is cosine, matching
    the normalized embeddings produced by most SiliconFlow/OpenAI-compatible
    embedding models.
    """
    collections = (Config.QDRANT_COLLECTION_CANDIDATES, Config.QDRANT_COLLECTION_JOBS)
    for name in collections:
        try:
            if not await client.collection_exists(name):
                await client.create_collection(
                    collection_name=name,
                    vectors_config=models.VectorParams(
                        size=Config.EMBEDDING_DIM,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection: %s (dim=%s)", name, Config.EMBEDDING_DIM)
        except Exception as e:
            # Best-effort: a single unreachable/misconfigured collection must not
            # block API startup. Vector indexing is an additive feature on top
            # of MongoDB, which remains the source of truth.
            logger.warning("Could not ensure Qdrant collection %s: %s", name, e)


async def ping() -> bool:
    """Best-effort connectivity check for /health."""
    try:
        await client.get_collections()
        return True
    except Exception as e:
        logger.warning("Qdrant ping failed: %s", e)
        return False
