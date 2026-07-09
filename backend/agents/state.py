"""
agents/state.py — Shared Agent State
======================================

What is "State" in LangGraph?
    LangGraph is a framework for building stateful, multi-step AI workflows.
    Every node in the graph reads from and writes to a shared State object.
    Think of it as a "baton" passed between runners in a relay race — each
    node picks it up, does its work, and passes it forward.

Why TypedDict?
    TypedDict gives us type hints (helpful for readability) without the
    overhead of a full dataclass. LangGraph reads these annotations to know
    what fields exist in the state.

Flow of state through the graph:
    1. User query enters → AgentState is created with just `query` set
    2. PlannerNode reads `query` → sets `intent` + `planner_notes`
    3. RAGNode reads `query` → calls retriever → sets `rag_answer` + `citations`
    4. FormatNode reads everything → sets `final_answer` (the user-facing response)
    5. Graph returns the final AgentState to the API layer
"""

from typing import Optional, List
from typing_extensions import TypedDict


class CitationDict(TypedDict):
    """
    A serializable representation of one source citation.
    (We use plain dicts instead of dataclasses so LangGraph can serialize state.)
    """
    chunk_text:     str
    document_title: str
    page_no:        int
    source_url:     str
    score:          float


class AgentState(TypedDict):
    """
    The single shared state object that all graph nodes read and write.

    Fields (in order of population):
        query          : The original user question. Set at graph entry.
        intent         : Set by PlannerNode.
                         - "answer"       → proceed to RAG
                         - "clarify"      → query is too vague, ask user
                         - "out_of_scope" → not an admin question
        planner_notes  : Human-readable explanation of the planner's decision.
        rag_answer     : The LLM-generated answer text (set by RAGNode).
        citations      : Source chunks used to generate the answer.
        final_answer   : The polished, user-facing response (set by FormatNode).
        error          : If something goes wrong, this holds the error message.
    """
    query:         str
    intent:        Optional[str]
    planner_notes: Optional[str]
    rag_answer:    Optional[str]
    citations:     Optional[List[CitationDict]]
    final_answer:  Optional[str]
    error:         Optional[str]
