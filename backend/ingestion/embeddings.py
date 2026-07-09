"""
ingestion/embeddings.py — Embedding Generator
===============================================

What it does:
    Loads the BAAI/bge-small-en-v1.5 sentence embedding model and converts
    text chunks into numerical vectors (embeddings).

    An embedding is a list of 384 numbers that represents the *meaning* of
    a piece of text. Chunks with similar meanings have vectors that are
    close together in this 384-dimensional space.

Why it exists:
    Qdrant is a *vector* database — it stores and searches embeddings,
    not raw text. This module bridges the gap:
        text chunk → [0.12, -0.44, 0.93, ...] (384 numbers)

Why BAAI/bge-small-en-v1.5?
    - "small" = fast and lightweight (168 MB model)
    - "bge" (BAAI General Embedding) = excellent quality for English
    - 384 dimensions = good balance of accuracy vs. storage size
    - Runs entirely locally (no API key, no internet needed)

How it connects:
    - Called by ingestion/pipeline.py after chunking.py produces ChunkData objects.
    - Returns (ChunkData, vector) pairs.
    - The vectors are stored in Qdrant via rag/vector_store.py.
    - The chunk text + metadata are stored in PostgreSQL.

Note on first run:
    The first time this runs, sentence-transformers will download the model
    (~168 MB) from HuggingFace. Subsequent runs use the cached version.
"""

from typing import List, Tuple

from sentence_transformers import SentenceTransformer

from config import settings
from ingestion.chunking import ChunkData

# ---------------------------------------------------------------------------
# Module-level model instance (lazy-loaded on first use).
# Loading a model takes ~1-2 seconds. We do it once and reuse it.
# ---------------------------------------------------------------------------
_model: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    """
    Returns the shared embedding model, loading it on first call.

    Using a module-level variable means we load the model weights
    once per process lifetime, not once per document.
    """
    global _model
    if _model is None:
        print(f"[Embeddings] Loading model '{settings.EMBEDDING_MODEL}'...")
        print("  (First run downloads ~168 MB from HuggingFace — please wait)")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print(f"[Embeddings] Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


def generate_embeddings(chunks: List[ChunkData]) -> List[Tuple[ChunkData, List[float]]]:
    """
    Generate embedding vectors for a list of text chunks.

    Args:
        chunks: List of ChunkData objects from chunking.py.

    Returns:
        A list of (ChunkData, vector) pairs.
        vector is a list of 384 floats.

    Example:
        chunk_vectors = generate_embeddings(my_chunks)
        for chunk, vector in chunk_vectors:
            print(f"Chunk {chunk.chunk_index}: {len(vector)} dimensions")
            # → Chunk 0: 384 dimensions
    """
    if not chunks:
        return []

    model = _get_model()

    # Extract just the text from each chunk for batch encoding.
    # Batch encoding is much faster than encoding one chunk at a time.
    texts = [chunk.chunk_text for chunk in chunks]

    print(f"[Embeddings] Encoding {len(texts)} chunks...")

    # encode() returns a numpy array of shape (num_chunks, 384)
    # convert_to_python_objects=True gives us plain Python lists (not numpy arrays)
    # which are JSON-serialisable and Qdrant-compatible.
    vectors = model.encode(
        texts,
        show_progress_bar = len(texts) > 10,   # Show progress for large batches
        normalize_embeddings = True,            # L2-normalise → better cosine similarity
        convert_to_numpy = True,
    )

    # Pair each chunk with its vector
    result = [
        (chunk, vector.tolist())    # .tolist() converts numpy → Python list
        for chunk, vector in zip(chunks, vectors)
    ]

    print(f"[Embeddings] Done. Generated {len(result)} embeddings "
          f"({settings.EMBEDDING_DIMENSION} dimensions each).")

    return result


def embed_single_query(query: str) -> List[float]:
    """
    Embed a single user query for similarity search.

    Args:
        query: The user's question text.

    Returns:
        A 384-dimensional float vector.

    This is called by the Retrieval Agent at query time.
    We use the same model and normalisation as during ingestion,
    which is essential for correct similarity search.
    """
    model = _get_model()
    vector = model.encode(query, normalize_embeddings=True, convert_to_numpy=True)
    return vector.tolist()
