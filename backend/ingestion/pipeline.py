"""
ingestion/pipeline.py — Complete Ingestion Orchestrator
=========================================================

What it does:
    Ties together ALL ingestion steps into one simple function call:

        ingest_document(file_path, source_url) → DocumentOut

    The steps in order:
        1. Calculate file hash   → check for duplicates
        2. Extract text          → parser.py (PyMuPDF)
        3. OCR scanned pages     → ocr.py (PaddleOCR, only if needed)
        4. Extract metadata      → metadata.py (Regex → LLM fallback)
        5. Chunk text            → chunking.py (RecursiveCharacterTextSplitter)
        6. Generate embeddings   → embeddings.py (BAAI/bge-small-en-v1.5)
        7. Store in Qdrant       → rag/vector_store.py
        8. Store in PostgreSQL   → database/postgres.py

Why it exists:
    The FastAPI upload endpoint (Phase 6) just calls `ingest_document()`.
    It doesn't need to know about PyMuPDF, PaddleOCR, or Qdrant at all.
    Clean separation of concerns.

How it connects:
    - Called by the POST /api/documents/upload endpoint (Phase 6).
    - Uses all modules in ingestion/ and rag/vector_store.py.
    - Writes to both PostgreSQL and Qdrant.
"""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from config import settings
from database.postgres import Document, Chunk
from ingestion.parser import extract_text_from_pdf, calculate_file_hash, PageResult
from ingestion.ocr import ocr_page
from ingestion.metadata import extract_metadata
from ingestion.chunking import chunk_document, ChunkData
from ingestion.embeddings import generate_embeddings
from rag.vector_store import upsert_chunks, ensure_collection


class DuplicateDocumentError(Exception):
    """Raised when a document with the same file hash already exists in the DB."""
    pass


def ingest_document(
    file_path:  str,
    db:         Session,
    source_url: Optional[str] = None,
) -> Document:
    """
    Full ingestion pipeline for a single PDF document.

    Args:
        file_path  : Path to the saved PDF file (in storage/uploads/).
        db         : SQLAlchemy database session (from FastAPI's get_db()).
        source_url : Original URL of the document (for citations). Optional.

    Returns:
        The newly created Document ORM object (saved to PostgreSQL).

    Raises:
        DuplicateDocumentError : If this exact file was already ingested.
        FileNotFoundError      : If the file doesn't exist.
        Exception              : For any unexpected error during processing.

    Example (used in Phase 6):
        doc = ingest_document(
            file_path  = "storage/uploads/hostel_circular.pdf",
            db         = db_session,
            source_url = "https://nitc.ac.in/hostel/circular/2024"
        )
        print(f"Ingested: {doc.title} ({len(doc.chunks)} chunks)")
    """
    filename = Path(file_path).name
    print(f"\n{'='*60}")
    print(f"[Pipeline] Starting ingestion: '{filename}'")
    print(f"{'='*60}")

    # =========================================================================
    # STEP 1: Duplicate Check
    # Calculate file hash and see if it's already in the DB.
    # This prevents re-processing the same file if uploaded twice.
    # =========================================================================
    print("[Pipeline] Step 1/8: Checking for duplicates...")
    file_hash = calculate_file_hash(file_path)

    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing:
        raise DuplicateDocumentError(
            f"Document already exists: '{existing.title}' (id={existing.id})"
        )
    print(f"[Pipeline] Hash: {file_hash[:16]}... — new document, continuing.")

    # =========================================================================
    # STEP 2: Extract Text (PyMuPDF)
    # =========================================================================
    print("[Pipeline] Step 2/8: Extracting text with PyMuPDF...")
    page_results = extract_text_from_pdf(file_path)

    # =========================================================================
    # STEP 3: OCR Scanned Pages (PaddleOCR — only if needed)
    # =========================================================================
    scanned_pages = [p for p in page_results if p.needs_ocr]
    if scanned_pages:
        print(f"[Pipeline] Step 3/8: Running OCR on {len(scanned_pages)} scanned page(s)...")
        for page in scanned_pages:
            ocr_text = ocr_page(file_path, page.page_no)
            page.text = ocr_text            # Replace empty text with OCR result
            page.needs_ocr = False          # Mark as processed
    else:
        print("[Pipeline] Step 3/8: No scanned pages — OCR not needed.")

    is_scanned = len(scanned_pages) > 0

    # Combine all page text into one string for metadata extraction
    full_text = "\n".join(p.text for p in page_results if p.text.strip())

    if not full_text.strip():
        print("[Pipeline] WARNING: No text extracted from any page. "
              "Check if PaddleOCR is installed for scanned documents.")

    # =========================================================================
    # STEP 4: Extract Metadata
    # =========================================================================
    print("[Pipeline] Step 4/8: Extracting metadata...")
    meta = extract_metadata(full_text, filename)
    print(f"  Title:    {meta.title}")
    print(f"  Category: {meta.category}")
    print(f"  Dept:     {meta.department}")
    print(f"  Date:     {meta.date}")
    print(f"  Doc No.:  {meta.document_number}")

    # =========================================================================
    # STEP 5: Chunk Text
    # =========================================================================
    print("[Pipeline] Step 5/8: Chunking text...")
    pages_for_chunking = [(p.page_no, p.text) for p in page_results]
    chunks = chunk_document(pages_for_chunking)

    if not chunks:
        print("[Pipeline] WARNING: No chunks generated. The document may be empty.")

    # =========================================================================
    # STEP 6: Generate Embeddings
    # =========================================================================
    print("[Pipeline] Step 6/8: Generating embeddings...")
    chunk_vectors = generate_embeddings(chunks)

    # =========================================================================
    # STEP 7: Save Document Record to PostgreSQL (get the auto-generated ID)
    # We save to PostgreSQL BEFORE Qdrant so we have document_id available.
    # =========================================================================
    print("[Pipeline] Step 7/8: Saving document to PostgreSQL...")
    document = Document(
        title           = meta.title or filename,
        department      = meta.department,
        category        = meta.category,
        document_number = meta.document_number,
        date            = meta.date,
        status          = "active",
        source_url      = source_url,
        file_path       = str(file_path),
        file_hash       = file_hash,
        is_scanned      = is_scanned,
    )
    db.add(document)
    db.flush()       # flush() sends the INSERT to DB and populates document.id
                     # without fully committing (so we can rollback if Qdrant fails)

    # =========================================================================
    # STEP 7b: Save Chunk Records to PostgreSQL
    # =========================================================================
    ensure_collection()   # Make sure Qdrant collection exists

    # Store chunks in Qdrant first to get chunk_ids
    chunk_ids = upsert_chunks(
        chunk_vectors   = chunk_vectors,
        document_id     = document.id,
        document_title  = document.title,
        source_url      = source_url,
    )

    # Now save chunk records to PostgreSQL with the Qdrant chunk_ids
    for (chunk_data, _vector), chunk_id in zip(chunk_vectors, chunk_ids):
        db_chunk = Chunk(
            document_id     = document.id,
            chunk_id        = chunk_id,
            chunk_index     = chunk_data.chunk_index,
            page_no         = chunk_data.page_no,
            chunk_text      = chunk_data.chunk_text,
            embedding_model = settings.EMBEDDING_MODEL,
        )
        db.add(db_chunk)

    # =========================================================================
    # STEP 8: Commit Everything
    # =========================================================================
    print("[Pipeline] Step 8/8: Committing to database...")
    db.commit()
    db.refresh(document)

    print(f"\n[Pipeline] DONE: '{document.title}'")
    print(f"  document_id : {document.id}")
    print(f"  chunks      : {len(chunk_ids)}")
    print(f"  is_scanned  : {document.is_scanned}")
    print(f"{'='*60}\n")

    return document
