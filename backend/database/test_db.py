"""
database/test_db.py — Database Connection & Schema Test Script
===============================================================

What it does:
    Runs a series of checks to confirm that:
    1. Python can connect to PostgreSQL successfully.
    2. All three tables (documents, chunks, templates) are created.
    3. We can INSERT a test record and read it back.
    4. We can DELETE the test record (clean up after ourselves).

Why it exists:
    Before building the full ingestion pipeline, we want to be 100% sure
    the database layer works in isolation. This script lets you test just
    that — without starting the full FastAPI server.

How to run:
    cd backend
    venv\\Scripts\\activate          (Windows)
    source venv/bin/activate       (macOS/Linux)

    python -m database.test_db

Expected output if everything is working:
    ✅ Connected to PostgreSQL successfully.
    ✅ Tables created: documents, chunks, templates
    ✅ Inserted test document: id=1, title='Test Document'
    ✅ Read back document: Test Document
    ✅ Deleted test document.
    🎉 All database checks passed!
"""

import sys

# ---------------------------------------------------------------------------
# We need to run this as `python -m database.test_db` from the backend/ folder
# so that imports like `from config import settings` work correctly.
# ---------------------------------------------------------------------------
from database.postgres import SessionLocal, create_tables, Document, Chunk, Template


def run_tests():
    print("\n[INFO] Running database checks...\n")

    # ------------------------------------------------------------------
    # Check 1: Can we connect?
    # ------------------------------------------------------------------
    try:
        db = SessionLocal()
        # A simple query to test the connection
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        print("[PASS] Connected to PostgreSQL successfully.")
    except Exception as e:
        print(f"[FAIL] Could not connect to PostgreSQL.\n   Error: {e}")
        print("\n[HINT] Please check:")
        print("   1. Is PostgreSQL running?")
        print("   2. Are the credentials in backend/.env correct?")
        print("   3. Does the database exist? (CREATE DATABASE agentic_admin;)")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Check 2: Create tables
    # ------------------------------------------------------------------
    try:
        create_tables()
        print("[PASS] Tables created (or already exist): documents, chunks, templates")
    except Exception as e:
        print(f"[FAIL] Failed to create tables.\n   Error: {e}")
        db.close()
        sys.exit(1)

    # ------------------------------------------------------------------
    # Check 3: INSERT a test document
    # ------------------------------------------------------------------
    try:
        test_doc = Document(
            title      = "Test Document - Phase 2 Check",
            department = "Test Department",
            category   = "Test",
            file_path  = "/tmp/test.pdf",
            file_hash  = "test_hash_phase2_abc123",
            is_scanned = False,
        )
        db.add(test_doc)
        db.commit()
        db.refresh(test_doc)   # Reload from DB to get the auto-generated id
        print(f"[PASS] Inserted test document: id={test_doc.id}, title='{test_doc.title}'")
    except Exception as e:
        print(f"[FAIL] Failed to INSERT test document.\n   Error: {e}")
        db.rollback()
        db.close()
        sys.exit(1)

    # ------------------------------------------------------------------
    # Check 4: READ back the document
    # ------------------------------------------------------------------
    try:
        fetched = db.query(Document).filter(Document.id == test_doc.id).first()
        assert fetched is not None, "Document not found after insert!"
        print(f"[PASS] Read back document: '{fetched.title}'")
    except Exception as e:
        print(f"[FAIL] Failed to READ test document.\n   Error: {e}")
        db.close()
        sys.exit(1)

    # ------------------------------------------------------------------
    # Check 5: DELETE the test document (clean up)
    # ------------------------------------------------------------------
    try:
        db.delete(fetched)
        db.commit()
        print("[PASS] Deleted test document (clean up complete).")
    except Exception as e:
        print(f"[FAIL] Failed to DELETE test document.\n   Error: {e}")
        db.close()
        sys.exit(1)

    db.close()
    print("\n[SUCCESS] All database checks passed! Phase 2 is working correctly.\n")


if __name__ == "__main__":
    run_tests()
