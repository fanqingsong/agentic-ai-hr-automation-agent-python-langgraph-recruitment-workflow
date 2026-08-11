# ============================================================================
# Embedding provider - SiliconFlow (OpenAI-compatible API), model configurable
#
# SiliconFlow exposes an OpenAI-compatible /v1/embeddings endpoint, so the
# existing langchain-openai dependency can talk to it by pointing base_url at
# SiliconFlow instead of adding a dedicated SDK. Model name, API key, base
# URL, and vector dimension are all configurable via Config so the embedding
# model can be swapped (e.g. BAAI/bge-m3, BAAI/bge-large-zh-v1.5,
# Qwen/Qwen3-Embedding-8B) without code changes.
# ============================================================================

import logging
from functools import lru_cache
from typing import List

from langchain_openai import OpenAIEmbeddings

from backend.config import Config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def get_embeddings_client() -> OpenAIEmbeddings:
    """Return a shared embeddings client for the configured provider.

    Only SiliconFlow (OpenAI-compatible) is implemented today. The
    ``EMBEDDING_PROVIDER`` switch is kept so a future local/Ollama or
    official-OpenAI embedding backend can be added without touching callers.
    """
    provider = (Config.EMBEDDING_PROVIDER or "siliconflow").lower()

    if provider in ("siliconflow", "openai"):
        return OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            api_key=Config.EMBEDDING_API_KEY or "not-needed",
            base_url=Config.EMBEDDING_BASE_URL,
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts. Returns one vector per input text, same order."""
    if not texts:
        return []
    client = get_embeddings_client()
    return await client.aembed_documents(texts)


async def embed_query(text: str) -> List[float]:
    """Embed a single query string (used for vector search)."""
    client = get_embeddings_client()
    return await client.aembed_query(text)
