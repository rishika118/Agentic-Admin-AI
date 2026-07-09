"""
routers/documents.py — Document Management API Endpoints
==========================================================

What it does:
    Exposes the document CRUD endpoints:

        POST   /api/documents/upload   — Upload a PDF, ingest it into the system
        GET    /api/documents          — List all ingested documents
        GET    /api/documents/{id}     — Get one document's details
        DELETE /api/documents/{id}     — Remove a document from everything

    These endpoints are what the frontend admin panel will use.
    Regular users only see the chat endpoint; admins manage documents here.

Key design decisions:
    - File upload uses FastAPI's UploadFile (multipart/form-data)
    - Ingestion is synchronous for MVP (the client waits for completion)
      In v2.0 this would become a background task with a job-status endpoint
    - Deletion removes from PostgreSQL AND Qdrant (no orphaned vectors)
"""

import os
import shutil
import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database.postgres import SessionLocal, Document, Chunk
from ingestion.pipeline import ingest_document, DuplicateDocumentError
from rag.vector_store import delete_document_vectors


router = APIRouter(prefix="/api/documents", tags=["Documents"])


# ---------------------------------------------------------------------------
# DB dependency — provides a session per request and closes it when done
# ---------------------------------------------------------------------------
def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy session.

    How it works (dependency injection):
        FastAPI calls get_db() for every request that declares it as a
        parameter with `Depends(get_db)`. The `finally` block guarantees
        the session is closed even if an exception occurs.

    This pattern prevents connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ChunkInfo(BaseModel):
    chunk_index: int
    page_no:     int
    chunk_text:  str


class DocumentResponse(BaseModel):
    """Serialized view of one document returned by the API."""
    id:              int
    title:           str
    department:      Optional[str]
    category:        Optional[str]
    document_number: Optional[str]
    date:            Optional[str]
    status:          str
    source_url:      Optional[str]
    file_path:       str
    is_scanned:      bool
    chunk_count:     int
    created_at:      str


class IngestResponse(BaseModel):
    """Returned after a successful ingestion."""
    message:     str
    document_id: int
    title:       str
    chunks:      int
    is_scanned:  bool


class DeleteResponse(BaseModel):
    """Returned after a successful deletion."""
    message:     str
    document_id: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _doc_to_response(doc: Document, db: Session) -> DocumentResponse:
    """Convert a SQLAlchemy Document ORM object to a DocumentResponse."""
    chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
    return DocumentResponse(
        id              = doc.id,
        title           = doc.title,
        department      = doc.department,
        category        = doc.category,
        document_number = doc.document_number,
        date            = doc.date,
        status          = doc.status,
        source_url      = doc.source_url,
        file_path       = doc.file_path,
        is_scanned      = doc.is_scanned,
        chunk_count     = chunk_count,
        created_at      = str(doc.created_at),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=IngestResponse,
    summary="Upload and ingest a PDF document",
    description=(
        "Accepts a PDF file upload, runs the full ingestion pipeline "
        "(parse → chunk → embed → store), and returns the document ID. "
        "Duplicate files are rejected based on SHA-256 hash."
    ),
)
async def upload_document(
    file:        UploadFile = File(..., description="PDF file to ingest"),
    source_url:  str        = Form("", description="Optional source URL of the document"),
    db:          Session    = Depends(get_db),
) -> IngestResponse:
    """
    Upload a PDF and run the ingestion pipeline.

    Steps:
        1. Validate file type (must be PDF)
        2. Save to storage/uploads/
        3. Call ingest_document() — the 8-step pipeline from Phase 3
        4. Return document info

    Error cases:
        - Non-PDF file → 400 Bad Request
        - Duplicate PDF → 409 Conflict
        - Ingestion error → 500 Internal Server Error
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # Check file size (FastAPI doesn't enforce this automatically)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content   = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # Save to upload folder
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
    safe_filename = os.path.basename(file.filename)          # Prevent path traversal
    save_path     = os.path.join(settings.UPLOAD_FOLDER, safe_filename)

    with open(save_path, "wb") as f:
        f.write(content)

    # Run ingestion pipeline
    try:
        document = ingest_document(
            file_path  = save_path,
            db         = db,
            source_url = source_url or None,
        )
    except DuplicateDocumentError as e:
        # Clean up the uploaded file since we won't use it
        os.remove(save_path)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    # Count how many chunks were stored
    chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()

    return IngestResponse(
        message     = "Document ingested successfully.",
        document_id = document.id,
        title       = document.title,
        chunks      = chunk_count,
        is_scanned  = document.is_scanned,
    )


@router.get(
    "/",
    response_model=List[DocumentResponse],
    summary="List all ingested documents",
)
async def list_documents(db: Session = Depends(get_db)) -> List[DocumentResponse]:
    """Return all documents stored in PostgreSQL, newest first."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [_doc_to_response(doc, db) for doc in docs]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a single document by ID",
)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Return details of one document. Returns 404 if not found."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return _doc_to_response(doc, db)


@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    summary="Delete a document from PostgreSQL and Qdrant",
)
async def delete_document(
    document_id: int,
    db: Session  = Depends(get_db),
) -> DeleteResponse:
    """
    Completely remove a document:
        1. Delete its vectors from Qdrant
        2. Delete its chunks from PostgreSQL
        3. Delete the document record from PostgreSQL
        4. Optionally delete the physical PDF file

    Returns 404 if the document doesn't exist.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    # Step 1: Remove vectors from Qdrant
    delete_document_vectors(document_id)

    # Step 2 & 3: Remove DB records (cascades to chunks via SQLAlchemy relationship)
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    for chunk in chunks:
        db.delete(chunk)
    db.delete(doc)
    db.commit()

    return DeleteResponse(
        message     = f"Document '{doc.title}' deleted successfully.",
        document_id = document_id,
    )
