"""
rag/retriever.py — RAG (Retrieval-Augmented Generation) Engine
================================================================

What it does:
    This is the heart of the AI system. It answers user questions by:

        Step 1: Embed the question into a vector
                (same model used during ingestion → BAAI/bge-small-en-v1.5)

        Step 2: Search Qdrant for the most semantically similar chunks
                (find chunks whose meaning is closest to the question)

        Step 3: Build a context block from the retrieved chunks

        Step 4: Send the question + context to Ollama (mistral:latest)
                as a carefully structured prompt

        Step 5: Parse the LLM's response and attach source citations

    This pattern is called RAG (Retrieval-Augmented Generation):
    - "Retrieval"  = find relevant chunks from the knowledge base
    - "Augmented"  = add that context to the LLM prompt
    - "Generation" = the LLM generates a grounded answer

Why RAG instead of just asking the LLM?
    Without RAG: LLM can only use knowledge from training data (may be
                 outdated, may hallucinate about NIT Calicut specifics).
    With RAG:    LLM answers using the actual documents you uploaded.
                 It is grounded, accurate, and citable.

How it connects:
    - ingestion/embeddings.py  → provides embed_single_query()
    - rag/vector_store.py      → provides search_similar()
    - Called by agents/         → the agents call retrieve_and_answer()
    - Called by Phase 6 API    → POST /api/chat
"""

from dataclasses import dataclass, field
from typing import List, Optional

from langchain_ollama import OllamaLLM

from config import settings
from ingestion.embeddings import embed_single_query
from rag.vector_store import search_similar


# ---------------------------------------------------------------------------
# Data classes for structured responses
# ---------------------------------------------------------------------------

@dataclass
class Citation:
    """
    Represents one source chunk used to answer the question.

    Attributes:
        chunk_text      : The actual text passage retrieved.
        document_title  : Title of the document it came from.
        page_no         : Page number within the document.
        source_url      : URL of the original PDF (for linking).
        score           : Similarity score 0.0–1.0 (higher = more relevant).
    """
    chunk_text:     str
    document_title: str
    page_no:        int
    source_url:     str
    score:          float


@dataclass
class RAGResponse:
    """
    The complete response from the RAG engine.

    Attributes:
        answer    : The LLM's generated answer.
        citations : List of source chunks used to generate the answer.
        query     : The original user question (echoed back).
    """
    answer:    str
    citations: List[Citation]
    query:     str


# ---------------------------------------------------------------------------
# The RAG Prompt Template
# ---------------------------------------------------------------------------

_RAG_PROMPT_TEMPLATE = """You are an AI assistant for NIT Calicut's administrative office.
Your job is to answer questions based ONLY on the provided document excerpts.

Rules:
1. Only use information from the provided context below.
2. If the context does not contain enough information to answer, say:
   "I could not find relevant information in the available documents."
3. Be concise and factual. Do not add information from outside the context.
4. If citing a specific rule or date, mention which document it comes from.

---
CONTEXT (retrieved document excerpts):
{context}
---

QUESTION: {question}

ANSWER:"""


def _build_context(citations: List[Citation]) -> str:
    """
    Format retrieved chunks into a readable context block for the LLM prompt.

    Example output:
        [1] From "Hostel Circular 2024" (Page 3):
        Students must vacate hostels by the last day of examinations...

        [2] From "Academic Regulations" (Page 12):
        Leave of absence must be approved by the Dean...
    """
    parts = []
    for i, c in enumerate(citations, start=1):
        parts.append(
            f"[{i}] From \"{c.document_title}\" (Page {c.page_no}):\n"
            f"{c.chunk_text.strip()}"
        )
    return "\n\n".join(parts)


def retrieve_and_answer(
    query:       str,
    top_k:       int = 5,
    document_id: Optional[int] = None,
) -> RAGResponse:
    """
    Full RAG pipeline: retrieve relevant chunks and generate a grounded answer.

    Args:
        query       : The user's question in plain English.
        top_k       : Number of chunks to retrieve from Qdrant (default: 5).
        document_id : If set, restrict search to one specific document.
                      If None, search across ALL documents.

    Returns:
        RAGResponse with answer text + citations list.

    Example:
        response = retrieve_and_answer("What is the hostel visitor policy?")
        print(response.answer)
        for c in response.citations:
            print(f"  Source: {c.document_title}, Page {c.page_no}")

    What happens internally:
        1. embed_single_query("What is the hostel visitor policy?")
           → [0.12, -0.44, 0.93, ...] (384 numbers)

        2. search_similar(vector, top_k=5)
           → [{chunk_text: "Visitors are permitted...", score: 0.87}, ...]

        3. Build context string from those chunks

        4. OllamaLLM("mistral").invoke(prompt_with_context)
           → "Visitors are permitted between 10:00 AM and 6:00 PM per the
              Hostel Circular No. NITC/REG/2024/001..."

        5. Return RAGResponse(answer=..., citations=[...])
    """
    print(f"\n[RAG] Query: '{query}'")

    # ------------------------------------------------------------------
    # Step 1: Embed the query
    # ------------------------------------------------------------------
    print("[RAG] Step 1/4: Embedding query...")
    query_vector = embed_single_query(query)

    # ------------------------------------------------------------------
    # Step 2: Retrieve relevant chunks from Qdrant
    # ------------------------------------------------------------------
    print(f"[RAG] Step 2/4: Searching Qdrant (top_k={top_k})...")
    raw_results = search_similar(
        query_vector=query_vector,
        top_k=top_k,
        document_id=document_id,
    )

    if not raw_results:
        print("[RAG] No results found in Qdrant.")
        return RAGResponse(
            answer    = "I could not find relevant information in the available documents.",
            citations = [],
            query     = query,
        )

    # Convert raw Qdrant results to Citation objects
    citations = [
        Citation(
            chunk_text     = r.get("chunk_text", ""),
            document_title = r.get("document_title", "Unknown Document"),
            page_no        = r.get("page_no", 1),
            source_url     = r.get("source_url", ""),
            score          = round(r.get("score", 0.0), 4),
        )
        for r in raw_results
    ]

    print(f"[RAG] Retrieved {len(citations)} chunks:")
    for c in citations:
        print(f"  score={c.score:.3f} | '{c.document_title}' p.{c.page_no}")

    # ------------------------------------------------------------------
    # Step 3: Build the prompt context
    # ------------------------------------------------------------------
    print("[RAG] Step 3/4: Building prompt context...")
    context = _build_context(citations)

    prompt = _RAG_PROMPT_TEMPLATE.format(
        context  = context,
        question = query,
    )

    # ------------------------------------------------------------------
    # Step 4: Generate answer with Ollama
    # ------------------------------------------------------------------
    print(f"[RAG] Step 4/4: Calling Ollama ({settings.OLLAMA_MODEL})...")
    try:
        llm = OllamaLLM(
            model    = settings.OLLAMA_MODEL,
            base_url = settings.OLLAMA_BASE_URL,
        )
        answer = llm.invoke(prompt).strip()
        print(f"[RAG] Answer generated ({len(answer)} chars)")

    except Exception as e:
        print(f"[RAG] Ollama error: {e}")
        # Graceful fallback: return the raw context without LLM synthesis
        answer = (
            "The Ollama LLM is not reachable. Here are the relevant passages found:\n\n"
            + context
        )

    return RAGResponse(
        answer    = answer,
        citations = citations,
        query     = query,
    )


def retrieve_only(
    query:       str,
    top_k:       int = 5,
    document_id: Optional[int] = None,
) -> List[Citation]:
    """
    Retrieve relevant chunks WITHOUT calling the LLM.

    Useful when:
    - You only need the source documents (not a generated answer)
    - Testing retrieval quality independently
    - The Planner Agent is deciding which tool to use

    Args:
        query       : Search query.
        top_k       : Number of chunks to return.
        document_id : Optional: restrict to one document.

    Returns:
        List of Citation objects sorted by relevance score.
    """
    query_vector = embed_single_query(query)
    raw_results  = search_similar(
        query_vector=query_vector,
        top_k=top_k,
        document_id=document_id,
    )
    return [
        Citation(
            chunk_text     = r.get("chunk_text", ""),
            document_title = r.get("document_title", "Unknown"),
            page_no        = r.get("page_no", 1),
            source_url     = r.get("source_url", ""),
            score          = round(r.get("score", 0.0), 4),
        )
        for r in raw_results
    ]
