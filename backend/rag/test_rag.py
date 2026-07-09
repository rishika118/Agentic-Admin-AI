"""
rag/test_rag.py — RAG Engine Test
====================================

What it tests:
    1. Ingest a real test PDF (same as pipeline test)
    2. Ask a question about its content
    3. Verify the retriever finds relevant chunks (retrieval quality)
    4. Call Ollama and verify a grounded answer is returned
    5. Verify citations are attached to the response
    6. Clean up

How to run:
    cd backend
    venv\\Scripts\\activate
    python -m rag.test_rag

Prerequisites:
    - PostgreSQL running (agentic_admin DB exists)
    - Qdrant running on localhost:6333
    - Ollama running with mistral:latest pulled
      (check with: ollama list)
    - All packages installed: pip install -r requirements.txt
"""

import os
import sys

# ---- Setup ----
from database.postgres import SessionLocal, create_tables, Document
from ingestion.pipeline import ingest_document, DuplicateDocumentError
from ingestion.test_pipeline import create_test_pdf
from rag.retriever import retrieve_and_answer, retrieve_only
from rag.vector_store import delete_document_vectors


def run_rag_tests():
    print("\n[INFO] Running RAG engine tests...\n")

    create_tables()
    db            = SessionLocal()
    created_doc_id = None

    # Test PDF path
    test_pdf_path = os.path.join("storage", "uploads", "_test_rag.pdf")
    os.makedirs(os.path.dirname(test_pdf_path), exist_ok=True)

    try:
        # ------------------------------------------------------------------
        # Setup: Ingest the test PDF
        # ------------------------------------------------------------------
        # Clean up any leftover from a previous run
        old = db.query(Document).filter(Document.file_path.like("%_test_rag%")).first()
        if old:
            delete_document_vectors(old.id)
            db.delete(old)
            db.commit()

        create_test_pdf(test_pdf_path)
        document = ingest_document(
            file_path  = test_pdf_path,
            db         = db,
            source_url = "https://nitc.ac.in/hostel/circular/2024",
        )
        created_doc_id = document.id
        print(f"[INFO] Ingested test document: id={document.id}, title='{document.title}'")

        # ------------------------------------------------------------------
        # Test 1: retrieve_only() — no LLM, just vector search
        # ------------------------------------------------------------------
        print("\n--- Test 1: Retrieval Quality ---")
        query = "hostel visitor timing rules"
        citations = retrieve_only(query, top_k=3)

        assert len(citations) > 0, "No chunks retrieved"
        print(f"[PASS] retrieve_only(): {len(citations)} chunks found for '{query}'")
        for c in citations:
            print(f"  score={c.score:.3f} | page={c.page_no} | '{c.chunk_text[:60]}...'")

        # Verify the top result is actually relevant (score > 0.5)
        assert citations[0].score > 0.5, f"Top result score too low: {citations[0].score}"
        print(f"[PASS] Top result relevance score: {citations[0].score:.3f} (> 0.5)")

        # Verify citations have correct document title
        assert citations[0].document_title == document.title
        print(f"[PASS] Citation links back to correct document: '{citations[0].document_title}'")

        # ------------------------------------------------------------------
        # Test 2: retrieve_and_answer() — full RAG with LLM
        # ------------------------------------------------------------------
        print("\n--- Test 2: Full RAG (retrieve + Ollama) ---")
        response = retrieve_and_answer(
            query = "What are the rules for hostel visitors?",
            top_k = 3,
        )

        assert response.query  == "What are the rules for hostel visitors?"
        assert len(response.citations) > 0, "No citations in RAG response"
        assert len(response.answer) > 10, "Answer is too short"

        print(f"[PASS] RAG answer generated ({len(response.answer)} chars)")
        print(f"[PASS] Citations: {len(response.citations)}")
        print(f"\n  Question: {response.query}")
        print(f"  Answer:   {response.answer[:200]}...")
        print(f"\n  Sources:")
        for c in response.citations:
            print(f"    - '{c.document_title}', Page {c.page_no} (score={c.score:.3f})")

        # ------------------------------------------------------------------
        # Test 3: Document-scoped search
        # ------------------------------------------------------------------
        print("\n--- Test 3: Document-Scoped Search ---")
        scoped_citations = retrieve_only(
            query       = "student rules",
            top_k       = 5,
            document_id = document.id,
        )
        # All results must belong to the test document
        for c in scoped_citations:
            assert c.document_title == document.title, \
                f"Scoped search returned wrong document: {c.document_title}"

        print(f"[PASS] Scoped search: all {len(scoped_citations)} results from correct document")

        # ------------------------------------------------------------------
        # Test 4: Empty query edge case
        # ------------------------------------------------------------------
        print("\n--- Test 4: Out-of-scope Query ---")
        oos_response = retrieve_and_answer(
            query = "What is the price of tea in China?",
            top_k = 3,
        )
        # Should still return something (either a "not found" msg or low-relevance answer)
        assert oos_response.answer is not None
        print(f"[PASS] Out-of-scope query handled gracefully")
        print(f"  Answer: '{oos_response.answer[:120]}...'")

        print("\n[SUCCESS] All RAG engine tests passed!\n")

    except Exception as e:
        print(f"\n[FAIL] RAG test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        if created_doc_id:
            print(f"[INFO] Cleaning up (doc_id={created_doc_id})...")
            delete_document_vectors(created_doc_id)
            doc = db.query(Document).filter(Document.id == created_doc_id).first()
            if doc:
                db.delete(doc)
                db.commit()
            print("[INFO] Cleanup done.")

        db.close()
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)


if __name__ == "__main__":
    run_rag_tests()
