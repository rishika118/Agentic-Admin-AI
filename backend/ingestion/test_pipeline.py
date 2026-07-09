"""
ingestion/test_pipeline.py — Ingestion Pipeline Test
======================================================

What it does:
    Tests the complete ingestion pipeline end-to-end:
        1. Creates a simple test PDF programmatically (no need to download one)
        2. Runs the full pipeline: parse → chunk → embed → store
        3. Verifies the document appears in PostgreSQL
        4. Verifies the embeddings are searchable in Qdrant
        5. Cleans up test data

How to run:
    cd backend
    venv\\Scripts\\activate
    python -m ingestion.test_pipeline

Expected output (if everything works):
    [PASS] PDF created
    [PASS] Pipeline completed: 'Test Administrative Circular'
    [PASS] Document found in PostgreSQL (id=X)
    [PASS] Chunks found in PostgreSQL (N chunks)
    [PASS] Vectors found in Qdrant
    [SUCCESS] All pipeline checks passed!

Prerequisites:
    - PostgreSQL running and agentic_admin database exists
    - Qdrant running on localhost:6333
    - pip install pymupdf sentence-transformers qdrant-client langchain
"""

import sys
import os
import tempfile

# Run from backend/ directory:  python -m ingestion.test_pipeline
from database.postgres import SessionLocal, create_tables, Document, Chunk
from ingestion.parser import extract_text_from_pdf, calculate_file_hash
from ingestion.chunking import chunk_document
from ingestion.embeddings import generate_embeddings, embed_single_query
from rag.vector_store import ensure_collection, upsert_chunks, search_similar, delete_document_vectors
from ingestion.pipeline import ingest_document, DuplicateDocumentError


def create_test_pdf(output_path: str) -> None:
    """
    Create a simple multi-page test PDF using PyMuPDF.
    This avoids needing an actual NIT Calicut PDF for testing.
    """
    import fitz

    doc = fitz.open()   # Create a new empty PDF

    # Page 1
    page1 = doc.new_page()
    page1.insert_text(
        (72, 100),
        "NATIONAL INSTITUTE OF TECHNOLOGY CALICUT\n\n"
        "OFFICE OF THE REGISTRAR\n\n"
        "Circular No. NITC/REG/2024/001\nDate: 01 July 2024\n\n"
        "SUBJECT: Guidelines for Hostel Residents 2024-25\n\n"
        "All students residing in hostels are hereby informed that the\n"
        "following rules shall be in effect from the academic year 2024-25.\n\n"
        "1. Students must maintain cleanliness in common areas.\n"
        "2. Visitors are permitted only between 10:00 AM and 06:00 PM.\n"
        "3. Ragging in any form is strictly prohibited.",
        fontsize=11,
    )

    # Page 2
    page2 = doc.new_page()
    page2.insert_text(
        (72, 100),
        "4. Students must carry their ID cards at all times.\n"
        "5. Electricity usage must be conserved. Lights and fans must\n"
        "   be switched off when leaving the room.\n"
        "6. Any damage to hostel property will be charged to the student.\n\n"
        "Students are advised to follow these guidelines strictly.\n"
        "Violations will lead to disciplinary action.\n\n"
        "Sd/-\nRegistrar\nNIT Calicut",
        fontsize=11,
    )

    doc.save(output_path)
    doc.close()


def run_tests():
    print("\n[INFO] Running ingestion pipeline tests...\n")

    # ------------------------------------------------------------------
    # Setup: Create tables and DB session
    # ------------------------------------------------------------------
    create_tables()
    db = SessionLocal()

    # We'll track the created document ID for cleanup
    created_doc_id = None

    try:
        # ------------------------------------------------------------------
        # Check 1: Create test PDF
        # ------------------------------------------------------------------
        test_pdf_path = os.path.join("storage", "uploads", "_test_circular.pdf")
        os.makedirs(os.path.dirname(test_pdf_path), exist_ok=True)

        create_test_pdf(test_pdf_path)
        print(f"[PASS] Test PDF created at '{test_pdf_path}'")

        # ------------------------------------------------------------------
        # Check 2: Parse PDF
        # ------------------------------------------------------------------
        pages = extract_text_from_pdf(test_pdf_path)
        assert len(pages) == 2, f"Expected 2 pages, got {len(pages)}"
        assert any(p.text for p in pages), "No text extracted from any page"
        print(f"[PASS] Parser extracted text from {len(pages)} pages")

        # ------------------------------------------------------------------
        # Check 3: Chunking
        # ------------------------------------------------------------------
        page_tuples = [(p.page_no, p.text) for p in pages]
        chunks = chunk_document(page_tuples)
        assert len(chunks) > 0, "No chunks generated"
        print(f"[PASS] Chunking created {len(chunks)} chunks")

        # ------------------------------------------------------------------
        # Check 4: Embeddings
        # ------------------------------------------------------------------
        chunk_vectors = generate_embeddings(chunks)
        assert len(chunk_vectors) == len(chunks), "Chunk/vector count mismatch"
        _, first_vector = chunk_vectors[0]
        assert len(first_vector) == 384, f"Expected 384-dim vector, got {len(first_vector)}"
        print(f"[PASS] Embeddings: {len(chunk_vectors)} vectors of {len(first_vector)} dims")

        # ------------------------------------------------------------------
        # Check 5: Full pipeline (ingest_document)
        # ------------------------------------------------------------------
        # First, clean up any leftover test document from a previous run
        old = db.query(Document).filter(Document.file_path.like("%_test_circular%")).first()
        if old:
            delete_document_vectors(old.id)
            db.delete(old)
            db.commit()
            print("[INFO] Removed leftover test document from previous run")

        document = ingest_document(
            file_path  = test_pdf_path,
            db         = db,
            source_url = "https://nitc.ac.in/test/circular",
        )
        created_doc_id = document.id
        print(f"[PASS] Pipeline completed: '{document.title}' (id={document.id})")

        # ------------------------------------------------------------------
        # Check 6: Document in PostgreSQL
        # ------------------------------------------------------------------
        fetched_doc = db.query(Document).filter(Document.id == document.id).first()
        assert fetched_doc is not None
        print(f"[PASS] Document in PostgreSQL: id={fetched_doc.id}, title='{fetched_doc.title}'")

        # ------------------------------------------------------------------
        # Check 7: Chunks in PostgreSQL
        # ------------------------------------------------------------------
        db_chunks = db.query(Chunk).filter(Chunk.document_id == document.id).all()
        assert len(db_chunks) > 0, "No chunks in PostgreSQL"
        print(f"[PASS] Chunks in PostgreSQL: {len(db_chunks)} chunk records")

        # ------------------------------------------------------------------
        # Check 8: Search in Qdrant
        # ------------------------------------------------------------------
        query = "hostel rules for students"
        query_vec = embed_single_query(query)
        results = search_similar(query_vec, top_k=3)
        assert len(results) > 0, "No results from Qdrant search"
        top = results[0]
        print(f"[PASS] Qdrant search returned {len(results)} results")
        print(f"  Top result (score={top['score']:.3f}): '{top['chunk_text'][:60]}...'")

        # ------------------------------------------------------------------
        # Check 9: Duplicate Detection
        # ------------------------------------------------------------------
        try:
            ingest_document(file_path=test_pdf_path, db=db)
            print("[FAIL] Duplicate was NOT detected — this is a bug!")
        except DuplicateDocumentError as e:
            print(f"[PASS] Duplicate detection works: '{e}'")

        print("\n[SUCCESS] All pipeline checks passed!\n")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # ------------------------------------------------------------------
        # Cleanup: Remove test document from DB and Qdrant
        # ------------------------------------------------------------------
        if created_doc_id:
            print(f"[INFO] Cleaning up test data (doc_id={created_doc_id})...")
            delete_document_vectors(created_doc_id)
            doc_to_del = db.query(Document).filter(Document.id == created_doc_id).first()
            if doc_to_del:
                db.delete(doc_to_del)
                db.commit()
            print("[INFO] Cleanup done.")

        db.close()

        # Remove test PDF file
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)


if __name__ == "__main__":
    run_tests()
