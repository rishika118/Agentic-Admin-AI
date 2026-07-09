"""
agents/task.py — RAG Task Node
================================

What does the Task Node do?
    This is the worker node that actually retrieves information and generates
    an answer. It's the "doing" part of the agent pipeline.

    It takes the user's query (validated by the Planner) and runs the full
    RAG pipeline from Phase 4:
        1. Embeds the query into a vector
        2. Searches Qdrant for similar chunks
        3. Builds a context string
        4. Calls Mistral to generate a grounded answer
        5. Returns answer + citations

Why is this a separate node from the Planner?
    Separation of concerns:
    - Planner = decides WHAT to do
    - Task     = actually DOES it

    This makes each node small, testable, and replaceable. In a future
    version, you could add multiple task nodes (e.g., one for documents,
    one for live database queries) and the Planner routes to the right one.

How it connects:
    - Reads:  state["query"]
    - Calls:  rag/retriever.py → retrieve_and_answer()
    - Writes: state["rag_answer"], state["citations"]
    - Called by graph.py only when intent == "answer"
"""

from typing import Optional

from agents.state import AgentState, CitationDict
from rag.retriever import retrieve_and_answer


def rag_node(state: AgentState) -> AgentState:
    """
    LangGraph node: RAG Task.

    Runs the full retrieve-and-answer pipeline for the given query.
    Converts the RAGResponse into serializable dicts for the state.

    Args:
        state: Current AgentState (must have "query" set, intent == "answer").

    Returns:
        Updated AgentState with "rag_answer" and "citations" populated.
        If an error occurs, sets "error" and leaves rag_answer empty.
    """
    query = state.get("query", "").strip()
    print(f"\n[RAGNode] Running RAG for: '{query[:80]}'")

    try:
        response = retrieve_and_answer(
            query = query,
            top_k = 5,   # Retrieve top 5 most relevant chunks
        )

        # Convert Citation dataclasses to plain dicts (LangGraph state is serializable)
        citations: list[CitationDict] = [
            CitationDict(
                chunk_text     = c.chunk_text,
                document_title = c.document_title,
                page_no        = c.page_no,
                source_url     = c.source_url,
                score          = c.score,
            )
            for c in response.citations
        ]

        print(f"[RAGNode] Retrieved {len(citations)} citations. "
              f"Answer length: {len(response.answer)} chars.")

        return {
            **state,
            "rag_answer": response.answer,
            "citations":  citations,
        }

    except Exception as e:
        print(f"[RAGNode] Error: {e}")
        return {
            **state,
            "rag_answer": None,
            "citations":  [],
            "error":      str(e),
        }
