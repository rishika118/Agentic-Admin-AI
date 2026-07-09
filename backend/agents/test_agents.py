"""
agents/test_agents.py — Agent Graph Tests
==========================================

What it tests:
    1. Graph imports correctly and builds without error
    2. Planner correctly classifies: answer / clarify / out_of_scope
    3. Full agent pipeline with ingested document (end-to-end)
    4. Out-of-scope query returns a helpful message
    5. Vague query returns a clarification request

How to run:
    cd backend
    venv\\Scripts\\activate
    python -m agents.test_agents

Prerequisites:
    - PostgreSQL running
    - Qdrant running on localhost:6333 (run .\\qdrant-bin\\qdrant.exe first)
    - Ollama running with mistral:latest
    - At least one document ingested (or this test will ingest a test doc)
"""

import os
from database.postgres import SessionLocal, create_tables, Document
from ingestion.pipeline import ingest_document
from ingestion.test_pipeline import create_test_pdf
from rag.vector_store import delete_document_vectors
from agents.graph import run_agent
from agents.planner import planner_node


def run_agent_tests():
    print("\n[INFO] Running Agent Orchestration Tests...\n")
    create_tables()

    db             = SessionLocal()
    created_doc_id = None
    test_pdf_path  = os.path.join("storage", "uploads", "_test_agents.pdf")
    os.makedirs(os.path.dirname(test_pdf_path), exist_ok=True)

    try:
        # ----------------------------------------------------------------
        # Test 1: Planner classification (no LLM needed)
        # ----------------------------------------------------------------
        print("--- Test 1: Planner Rule-Based Classification ---")

        cases = [
            ("What are the hostel visitor timing rules?", "answer"),
            ("hi",                                        "clarify"),
            ("write me a poem",                           "out_of_scope"),
            ("hostel fee deadline",                       "answer"),
            ("What is bitcoin?",                          "out_of_scope"),
        ]

        for query, expected in cases:
            result = planner_node({"query": query, "intent": None,
                                   "planner_notes": None, "rag_answer": None,
                                   "citations": None, "final_answer": None,
                                   "error": None})
            got = result["intent"]
            status = "[PASS]" if got == expected else f"[FAIL] (expected '{expected}')"
            print(f"  {status} '{query[:50]}' -> intent='{got}'")
            assert got == expected, f"Planner misclassified: got '{got}', expected '{expected}'"

        print("[PASS] All planner classification tests passed\n")

        # ----------------------------------------------------------------
        # Setup: Ingest a real test document
        # ----------------------------------------------------------------
        # Clean up any leftover test doc from before
        old = db.query(Document).filter(
            Document.file_path.like("%_test_agents%")
        ).first()
        if old:
            delete_document_vectors(old.id)
            db.delete(old)
            db.commit()

        create_test_pdf(test_pdf_path)
        document = ingest_document(
            file_path  = test_pdf_path,
            db         = db,
            source_url = "https://nitc.ac.in/agents/test",
        )
        created_doc_id = document.id
        print(f"[INFO] Ingested test doc: id={document.id}, "
              f"title='{document.title}'\n")

        # ----------------------------------------------------------------
        # Test 2: Full pipeline — answerable query
        # ----------------------------------------------------------------
        print("--- Test 2: Full Pipeline — Answerable Query ---")
        result = run_agent("What are the rules for hostel visitors?")

        assert result["intent"]       == "answer",     f"Expected intent='answer', got '{result['intent']}'"
        assert result["final_answer"] is not None,     "final_answer should not be None"
        assert len(result["final_answer"]) > 20,       "final_answer too short"
        assert result["citations"]    is not None,     "citations should not be None"
        assert len(result["citations"]) > 0,           "At least 1 citation expected"

        print(f"[PASS] intent='{result['intent']}'")
        print(f"[PASS] final_answer ({len(result['final_answer'])} chars)")
        print(f"[PASS] citations: {len(result['citations'])} sources")
        print(f"\n  Answer preview: {result['final_answer'][:200]}...")
        print(f"  Top citation:   '{result['citations'][0]['document_title']}' "
              f"p.{result['citations'][0]['page_no']} "
              f"(score={result['citations'][0]['score']:.3f})\n")

        # ----------------------------------------------------------------
        # Test 3: Clarify path (no RAG called)
        # ----------------------------------------------------------------
        print("--- Test 3: Clarify Path ---")
        result = run_agent("hi")

        assert result["intent"]      == "clarify",  f"Expected 'clarify', got '{result['intent']}'"
        assert result["final_answer"] is not None
        assert result["citations"]    is None or len(result.get("citations") or []) == 0

        print(f"[PASS] intent='clarify'")
        print(f"[PASS] No RAG called (citations={len(result.get('citations') or [])})")
        print(f"  Response: '{result['final_answer'][:100]}...'\n")

        # ----------------------------------------------------------------
        # Test 4: Out-of-scope path (no RAG called)
        # ----------------------------------------------------------------
        print("--- Test 4: Out-of-Scope Path ---")
        result = run_agent("write me a poem")

        assert result["intent"]      == "out_of_scope", f"Expected 'out_of_scope', got '{result['intent']}'"
        assert result["final_answer"] is not None
        assert result["citations"]    is None or len(result.get("citations") or []) == 0

        print(f"[PASS] intent='out_of_scope'")
        print(f"[PASS] No RAG called")
        print(f"  Response: '{result['final_answer'][:100]}...'\n")

        print("[SUCCESS] All agent orchestration tests passed!\n")

    except Exception as e:
        print(f"\n[FAIL] Agent test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
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
    run_agent_tests()
