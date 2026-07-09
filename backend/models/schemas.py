"""
models/schemas.py — Pydantic Request & Response Schemas
=========================================================

What it does:
    Defines the *shape* of data that flows in and out of our API:
        - Request bodies  (what the frontend sends TO  FastAPI)
        - Response models (what FastAPI sends BACK to the frontend)

Why it exists:
    FastAPI uses Pydantic schemas to:
        1. Validate incoming data automatically (wrong type → 422 error).
        2. Generate the Swagger docs at /docs with correct field types.
        3. Serialise ORM model objects into JSON for the frontend.

    Keeping schemas separate from ORM models (database/postgres.py)
    is important — the DB model has everything; the API schema exposes
    only what the frontend needs.

How it connects:
    - Phase 6 API routes import these schemas as function arguments
      and return types.
    - The frontend TypeScript types (Phase 7) will mirror these exactly.

Quick Pydantic cheatsheet:
    BaseModel      → define a schema class
    Optional[X]    → field is not required (can be None)
    model_config   → allow ORM objects to be passed directly
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ===========================================================================
# DOCUMENT SCHEMAS
# ===========================================================================

class DocumentBase(BaseModel):
    """Fields shared by create + read schemas."""
    title:           str
    department:      Optional[str] = None
    category:        Optional[str] = None
    document_number: Optional[str] = None
    date:            Optional[str] = None
    version:         Optional[str] = None
    status:          Optional[str] = "active"
    source_url:      Optional[str] = None


class DocumentCreate(DocumentBase):
    """
    Schema for creating a new document record.
    Used internally by the ingestion pipeline — not sent by the user directly.
    """
    file_path:  str
    file_hash:  Optional[str] = None
    is_scanned: bool = False


class DocumentOut(DocumentBase):
    """
    Schema returned to the frontend when listing or retrieving documents.
    Includes the auto-generated id and timestamps.
    """
    id:         int
    file_path:  str
    is_scanned: bool
    created_at: datetime

    # This tells Pydantic: "it's OK to receive a SQLAlchemy ORM object,
    # not just a plain dictionary."
    model_config = {"from_attributes": True}


# ===========================================================================
# CHUNK SCHEMAS
# ===========================================================================

class ChunkOut(BaseModel):
    """
    A single retrieved chunk — included in chat responses as context.
    """
    id:              int
    document_id:     int
    chunk_id:        str
    chunk_index:     int
    page_no:         Optional[int] = None
    chunk_text:      str
    embedding_model: Optional[str] = None

    model_config = {"from_attributes": True}


# ===========================================================================
# CITATION SCHEMA
# ===========================================================================

class Citation(BaseModel):
    """
    A citation attached to every AI response.
    The frontend will display this as a clickable card linking to the source.
    """
    document_title: str
    page_no:        Optional[int] = None
    source_url:     Optional[str] = None
    chunk_text:     str   # Short excerpt that was used


# ===========================================================================
# CHAT SCHEMAS
# ===========================================================================

class ChatRequest(BaseModel):
    """
    What the frontend sends when the user asks a question.

    Example JSON body:
        {
          "message": "What is the leave policy for faculty?",
          "top_k": 5
        }
    """
    message: str = Field(..., min_length=1, max_length=2000, description="The user's question")
    top_k:   int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class ChatResponse(BaseModel):
    """
    What the API returns after answering a question.

    The `answer` is the LLM-generated text.
    The `citations` list tells the user *where* the answer came from.
    """
    answer:    str
    citations: List[Citation] = []


# ===========================================================================
# TASK SCHEMAS — Report, Draft, Compare
# ===========================================================================

class ReportRequest(BaseModel):
    """
    Request to generate a summary report.

    Example:
        { "topic": "hostel circulars 2024", "top_k": 10 }
    """
    topic: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=10, ge=1, le=30)


class ReportResponse(BaseModel):
    """The generated report text, with citations."""
    report:    str
    citations: List[Citation] = []


class DraftRequest(BaseModel):
    """
    Request to draft an official letter.

    Example:
        {
          "template_type": "leave_request",
          "context": "I need 5 days leave from July 10 to July 14 for a family function."
        }
    """
    template_type: str = Field(..., description="e.g. 'leave_request', 'office_order'")
    context:       str = Field(..., min_length=10, max_length=2000,
                               description="Details to fill into the template")


class DraftResponse(BaseModel):
    """The drafted letter text."""
    draft: str


class CompareRequest(BaseModel):
    """
    Request to compare two policies.

    Example:
        {
          "policy_a": "old hostel rules",
          "policy_b": "new hostel rules 2024"
        }
    """
    policy_a: str = Field(..., min_length=3, max_length=300)
    policy_b: str = Field(..., min_length=3, max_length=300)
    top_k:    int = Field(default=5, ge=1, le=20)


class CompareResponse(BaseModel):
    """Side-by-side policy comparison with citations from both sources."""
    comparison: str
    citations:  List[Citation] = []


# ===========================================================================
# TEMPLATE SCHEMAS
# ===========================================================================

class TemplateOut(BaseModel):
    """A letter/report template stored in the DB."""
    id:            int
    template_name: str
    template_type: str
    content:       str
    created_at:    datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# SYSTEM SCHEMAS
# ===========================================================================

class HealthResponse(BaseModel):
    """Response shape for the /health endpoint."""
    status:      str
    app:         str
    version:     str
    environment: str
