"""
Vector Retrieval Module — OpenSearch k-NN index for RAG.
In local dev: uses a lightweight mock embedding (deterministic MD5 hash).
In production: swaps in Bedrock Titan Embeddings (amazon.titan-embed-text-v2:0).
"""
import hashlib
import logging
import random
from typing import Any

import httpx

from agent.config import settings

logger = logging.getLogger(__name__)

OPENSEARCH_BASE = (
    settings.opensearch_endpoint.rstrip("/")
    if settings.opensearch_endpoint and settings.opensearch_endpoint.startswith("http")
    else "http://localhost:9200"
)
INDEX_NAME = settings.opensearch_index
EMBEDDING_DIMS = 8  # Small dims for local dev; prod uses 1024 (Titan v2)


# ── Embedding ─────────────────────────────────────────────────────────────────

def _mock_embed(text: str, dims: int = EMBEDDING_DIMS) -> list[float]:
    """
    Deterministic pseudo-embedding for local dev — no Bedrock needed.
    Based on an MD5 hash seed → reproducible but not semantically meaningful.
    Replace with Titan Embeddings for production.
    """
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dims)]


# ── Index Management ──────────────────────────────────────────────────────────

async def ensure_index_exists() -> None:
    """Create the k-NN index if it doesn't already exist."""
    mapping = {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": EMBEDDING_DIMS,
                    "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "nmslib"},
                },
                "doc_type": {"type": "keyword"},   # "runbook" | "past_incident"
                "incident_id": {"type": "keyword"},
                "title": {"type": "text"},
            }
        },
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            head = await client.head(f"{OPENSEARCH_BASE}/{INDEX_NAME}")
            if head.status_code == 404:
                await client.put(f"{OPENSEARCH_BASE}/{INDEX_NAME}", json=mapping)
                logger.info(f"Created OpenSearch k-NN index '{INDEX_NAME}'")
    except Exception as e:
        logger.warning(f"Could not connect to OpenSearch ({OPENSEARCH_BASE}): {e}")


# ── Indexing ──────────────────────────────────────────────────────────────────

async def index_document(
    doc_id: str,
    text: str,
    title: str = "",
    doc_type: str = "runbook",
    incident_id: str = "",
) -> None:
    """Index a runbook or past incident into the vector store."""
    body = {
        "text": text,
        "embedding": _mock_embed(text),
        "doc_type": doc_type,
        "title": title,
        "incident_id": incident_id,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(f"{OPENSEARCH_BASE}/{INDEX_NAME}/_doc/{doc_id}", json=body)
            logger.debug(f"Indexed document '{doc_id}' ({doc_type})")
    except Exception as e:
        logger.warning(f"Failed to index document '{doc_id}': {e}")


# ── Retrieval ─────────────────────────────────────────────────────────────────

async def retrieve_similar(incident_text: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Embed the incident description and query the k-NN index for similar runbooks
    or past incidents. Returns top-k results with id, score, and source text.
    """
    embedding = _mock_embed(incident_text)
    query = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {"vector": embedding, "k": top_k}
            }
        },
        "_source": ["text", "title", "doc_type", "incident_id"],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{OPENSEARCH_BASE}/{INDEX_NAME}/_search",
                json=query,
            )
            if r.status_code == 200:
                hits = r.json().get("hits", {}).get("hits", [])
                return [
                    {
                        "id": h["_id"],
                        "score": h["_score"],
                        "title": h["_source"].get("title", ""),
                        "text": h["_source"].get("text", ""),
                        "doc_type": h["_source"].get("doc_type", ""),
                    }
                    for h in hits
                ]
    except Exception as e:
        logger.warning(f"RAG retrieval failed (OpenSearch unreachable?): {e}")

    return []
