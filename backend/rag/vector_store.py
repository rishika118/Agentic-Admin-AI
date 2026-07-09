"""
rag/vector_store.py — Qdrant Vector Database Wrapper
======================================================

What it does:
    Wraps all Qdrant operations behind simple, well-named Python functions:

        ensure_collection()  → Create the Qdrant collection if it doesn't exist
        upsert_chunks()      → Store embeddings + metadata in Qdrant
        search_similar()     → Find the top-k most similar chunks to a query
        delete_document()    → Remove all vectors for a given document

Why it exists:
    - Keeps all Qdrant client code in ONE place.
    - If we ever switch to a different vector DB, only THIS file changes.
    - The rest of the codebase (agents, ingestion) never sees Qdrant directly.

How it connects:
    - ingestion/pipeline.py calls upsert_chunks() when indexing a new document.
    - rag/retriever.py calls search_similar() when answering user questions.
    - The FastAPI delete endpoint (Phase 6) calls delete_document().

Qdrant Concepts (quick reference):
    Collection  = a named group of vectors (like a table in a SQL DB)
    Point       = one vector + its payload (like a row in a SQL table)
    Payload     = metadata attached to a vector (dict with arbitrary keys)
    Distance    = how we measure similarity (we use Cosine)
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
    QueryRequest,
)

from config import settings

# ---------------------------------------------------------------------------
# Shared Qdrant client (one connection for the whole application).
# ---------------------------------------------------------------------------
_client: Optional[QdrantClient] = None


def _get_client() -> QdrantClient:
    """
    Returns the shared Qdrant client, creating it on first call.
    Qdrant runs locally on http://localhost:6333 by default.
    We set prefer_grpc=False to use the REST API (more compatible on Windows).
    """
    global _client
    if _client is None:
        _client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            prefer_grpc=False,          # Use REST (HTTP) instead of gRPC
            check_compatibility=False,  # Skip version mismatch warnings
        )
    return _client


def ensure_collection() -> None:
    """
    Create the Qdrant collection if it doesn't already exist.

    A collection must exist before we can store any vectors in it.
    This function is safe to call multiple times — if the collection
    already exists, it does nothing.

    Collection settings:
        - name     : from config (QDRANT_COLLECTION_NAME = "admin_documents")
        - size     : 384 (must match BAAI/bge-small-en-v1.5 output dimension)
        - distance : Cosine (standard for text similarity)
    """
    client = _get_client()
    existing = [col.name for col in client.get_collections().collections]

    if settings.QDRANT_COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name = settings.QDRANT_COLLECTION_NAME,
            vectors_config  = VectorParams(
                size     = settings.EMBEDDING_DIMENSION,  # 384
                distance = Distance.COSINE,
            ),
        )
        print(f"[VectorStore] Created Qdrant collection '{settings.QDRANT_COLLECTION_NAME}'")
    else:
        print(f"[VectorStore] Collection '{settings.QDRANT_COLLECTION_NAME}' already exists")


def upsert_chunks(
    chunk_vectors: List[Tuple[Any, List[float]]],   # (ChunkData, vector) pairs
    document_id:   int,
    document_title: str,
    source_url:    Optional[str] = None,
) -> List[str]:
    """
    Store embedding vectors and metadata in Qdrant.

    Args:
        chunk_vectors  : List of (ChunkData, vector) pairs from embeddings.py.
        document_id    : The PostgreSQL document ID (for cross-referencing).
        document_title : Human-readable title (stored in Qdrant payload).
        source_url     : Original PDF URL (for citations).

    Returns:
        List of chunk_id strings (UUIDs) that were stored.
        These same IDs are also stored in the PostgreSQL `chunks` table.

    Each Qdrant Point stores:
        - id      : A UUID (str) that links Qdrant ↔ PostgreSQL chunks table
        - vector  : The 384-dim embedding
        - payload : Metadata dict {document_id, title, page_no, chunk_text, ...}
    """
    if not chunk_vectors:
        return []

    client = _get_client()
    ensure_collection()

    points    = []
    chunk_ids = []

    for chunk_data, vector in chunk_vectors:
        # Generate a unique ID for this chunk.
        # We use UUID4 (random) — it's guaranteed to be unique.
        chunk_id = str(uuid.uuid4())
        chunk_ids.append(chunk_id)

        # The payload is stored alongside the vector in Qdrant.
        # We can filter searches by any payload field.
        payload = {
            "chunk_id":      chunk_id,
            "document_id":   document_id,
            "document_title": document_title,
            "chunk_index":   chunk_data.chunk_index,
            "page_no":       chunk_data.page_no,
            "chunk_text":    chunk_data.chunk_text,
            "source_url":    source_url or "",
        }

        points.append(PointStruct(
            id      = chunk_id,   # Qdrant accepts UUID strings as IDs
            vector  = vector,
            payload = payload,
        ))

    # upsert = insert or update (if the same ID already exists, overwrite it)
    client.upsert(
        collection_name = settings.QDRANT_COLLECTION_NAME,
        points          = points,
    )

    print(f"[VectorStore] Stored {len(points)} vectors for document_id={document_id}")
    return chunk_ids


def search_similar(
    query_vector: List[float],
    top_k:        int = 5,
    document_id:  Optional[int] = None,   # Optional: restrict to one document
) -> List[Dict]:
    """
    Find the top-k most similar chunks to a query vector.

    Args:
        query_vector : The embedded user query (from embeddings.embed_single_query).
        top_k        : Number of results to return (default: 5).
        document_id  : If set, search only within chunks from this document.

    Returns:
        A list of dicts, each containing the chunk payload + similarity score.
        Results are sorted by score (highest = most similar).

    Example return value:
        [
          {
            "chunk_id": "uuid-...",
            "document_id": 3,
            "document_title": "Hostel Circular 2024",
            "page_no": 4,
            "chunk_text": "Students must vacate hostels by...",
            "source_url": "https://nitc.ac.in/...",
            "score": 0.87
          },
          ...
        ]
    """
    client = _get_client()

    # Optional filter: restrict search to a specific document
    query_filter = None
    if document_id is not None:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    results = client.query_points(
        collection_name = settings.QDRANT_COLLECTION_NAME,
        query           = query_vector,
        limit           = top_k,
        query_filter    = query_filter,
        with_payload    = True,    # Include the payload (metadata) in results
    ).points

    # Format results into plain dicts for easy use downstream
    hits = []
    for result in results:
        payload = result.payload.copy()
        payload["score"] = result.score    # Add the similarity score
        hits.append(payload)

    return hits


def delete_document_vectors(document_id: int) -> None:
    """
    Delete all Qdrant vectors belonging to a specific document.

    Called when a document is deleted from the system — we must remove
    its vectors from Qdrant to keep it consistent with PostgreSQL.

    Args:
        document_id: The PostgreSQL document ID whose vectors to remove.
    """
    client = _get_client()

    client.delete(
        collection_name = settings.QDRANT_COLLECTION_NAME,
        points_selector = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        ),
    )
    print(f"[VectorStore] Deleted all vectors for document_id={document_id}")
