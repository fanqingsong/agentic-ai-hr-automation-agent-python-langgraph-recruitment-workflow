# ============================================================================
# Vector index: upsert/search candidate and job chunks in Qdrant.
#
# Point ids are deterministic (uuid5 of candidate_id/job_id + chunk_type +
# position), and a full replace (delete-by-filter then upsert) is used on
# every sync call so re-processing a candidate/job never leaves stale chunks
# behind when the number of experience/education/section entries changes.
# ============================================================================

import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import models

from backend.config import Config
from backend.core.qdrant_client import client
from backend.services.knowledge.chunking import Chunk
from backend.services.knowledge.embedding_provider import embed_query, embed_texts

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.UUID("6f5b8b1a-6b8a-4e2a-9f3d-1f8c6b9a2d10")


def _point_id(entity_id: str, chunk_type: str, idx: int) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"{entity_id}:{chunk_type}:{idx}"))


async def _delete_by_id_field(collection: str, id_field: str, entity_id: str) -> None:
    try:
        await client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key=id_field, match=models.MatchValue(value=entity_id))]
                )
            ),
        )
    except Exception as e:
        # Deleting stale chunks is best-effort; a missing collection on first
        # run is expected and must not block the subsequent upsert.
        logger.warning("Could not delete existing %s chunks for %s: %s", collection, entity_id, e)


async def _upsert_chunks(collection: str, id_field: str, entity_id: str, chunks: List[Chunk]) -> None:
    await _delete_by_id_field(collection, id_field, entity_id)
    if not chunks:
        return

    vectors = await embed_texts([c.text for c in chunks])
    points = [
        models.PointStruct(
            id=_point_id(entity_id, chunk.chunk_type, idx),
            vector=vector,
            payload={
                id_field: entity_id,
                "chunk_type": chunk.chunk_type,
                "text": chunk.text,
                "source_ref": chunk.source_ref,
            },
        )
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    await client.upsert(collection_name=collection, points=points)


async def upsert_candidate_vectors(candidate_id: str, chunks: List[Chunk]) -> None:
    """Replace all vector chunks for a candidate."""
    await _upsert_chunks(Config.QDRANT_COLLECTION_CANDIDATES, "candidate_id", candidate_id, chunks)


async def upsert_job_vectors(job_id: str, chunks: List[Chunk]) -> None:
    """Replace all vector chunks for a job."""
    await _upsert_chunks(Config.QDRANT_COLLECTION_JOBS, "job_id", job_id, chunks)


async def delete_candidate_vectors(candidate_id: str) -> None:
    await _delete_by_id_field(Config.QDRANT_COLLECTION_CANDIDATES, "candidate_id", candidate_id)


async def delete_job_vectors(job_id: str) -> None:
    await _delete_by_id_field(Config.QDRANT_COLLECTION_JOBS, "job_id", job_id)


async def search(
    collection: str,
    query_text: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Semantic search over a collection. Returns [{score, payload}, ...].

    Kept as a plain, side-effect-free function so a future Agent tool layer
    can call it directly (e.g. as a LangChain/LangGraph tool) without needing
    to know about Qdrant internals.
    """
    vector = await embed_query(query_text)
    query_filter = None
    if filters:
        query_filter = models.Filter(
            must=[models.FieldCondition(key=k, match=models.MatchValue(value=v)) for k, v in filters.items()]
        )

    result = await client.query_points(
        collection_name=collection,
        query=vector,
        query_filter=query_filter,
        limit=top_k,
    )
    return [{"score": p.score, "payload": p.payload} for p in result.points]
