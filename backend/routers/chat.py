"""
routers/chat.py — Chat / Q&A API Endpoint
==========================================

What it does:
    Exposes POST /api/chat — the main user-facing endpoint.

    When the React frontend sends a question, this endpoint:
        1. Validates the request body (Pydantic)
        2. Calls run_agent(query) — the full LangGraph pipeline
        3. Returns a structured JSON response with the answer + citations

    That's it. The endpoint stays thin — all intelligence is in agents/graph.py.

Why a separate router file?
    Keeping each feature in its own router file makes it easy to:
    - Find and edit a specific endpoint
    - Add authentication to one endpoint without touching others
    - Test endpoints independently

Request body:  { "query": "What is the hostel visitor policy?" }
Response body: { "answer": "...", "citations": [...], "intent": "answer" }
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.graph import run_agent


router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """
    What the frontend sends to POST /api/chat.

    Attributes:
        query: The user's question in plain English.
               Min length 1 ensures empty strings are rejected by FastAPI.
    """
    query: str = Field(..., min_length=1, max_length=2000,
                       description="The user's question",
                       examples=["What is the hostel visitor policy?"])


class CitationResponse(BaseModel):
    """One source citation returned to the frontend."""
    document_title: str
    page_no:        int
    source_url:     str
    score:          float
    chunk_text:     str


class ChatResponse(BaseModel):
    """
    What the API returns for every chat request.

    Attributes:
        answer    : The final answer string (from LLM or fallback).
        citations : Source documents used to generate the answer.
        intent    : Planner's decision — "answer" | "clarify" | "out_of_scope"
        query     : The original question echoed back (useful for debugging).
    """
    answer:    str
    citations: list[CitationResponse]
    intent:    str
    query:     str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ChatResponse,
    summary="Ask a question about NIT Calicut administrative documents",
    description=(
        "Runs the full agentic RAG pipeline: the Planner classifies the query, "
        "the RAG node retrieves relevant document chunks, and the LLM generates "
        "a grounded answer. Returns the answer and source citations."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main Q&A endpoint.

    The heavy lifting is done by run_agent() in agents/graph.py.
    This endpoint simply validates input, calls the agent, and shapes the response.
    """
    try:
        result = run_agent(query=request.query)
    except Exception as e:
        # Unexpected agent error — return 500 with a clear message
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline error: {str(e)}"
        )

    # Build citation list (raw dicts from state -> Pydantic models)
    citations = [
        CitationResponse(
            document_title = c["document_title"],
            page_no        = c["page_no"],
            source_url     = c["source_url"],
            score          = c["score"],
            chunk_text     = c["chunk_text"][:300],   # Truncate for API response
        )
        for c in (result.get("citations") or [])
    ]

    return ChatResponse(
        answer    = result.get("final_answer") or "No answer generated.",
        citations = citations,
        intent    = result.get("intent") or "answer",
        query     = request.query,
    )
