"""
test_api.py — Verification tests for Phase 6 (FastAPI Layer)
============================================================
Uses FastAPI TestClient to test:
1. GET /health
2. GET /
3. POST /api/chat (with mocked run_agent or direct integration test)
4. GET /api/documents/
"""

import sys
import os
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

client = TestClient(app)

def run_tests():
    print("[INFO] Testing Phase 6 API Layer...")

    # 1. Health check
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    print(f"  [PASS] GET /health -> status={data['status']}, app={data['app']}")

    # 2. Root check
    resp = client.get("/")
    assert resp.status_code == 200
    print("  [PASS] GET / -> Landing endpoint reachable")

    # 3. List documents check
    resp = client.get("/api/documents/")
    assert resp.status_code == 200
    docs = resp.json()
    print(f"  [PASS] GET /api/documents/ -> returned {len(docs)} documents")

    # 4. Chat endpoint check (testing clarify / short query path for fast verification)
    resp = client.post("/api/chat/", json={"query": "hi"})
    assert resp.status_code == 200
    chat_data = resp.json()
    assert chat_data["intent"] == "clarify"
    print(f"  [PASS] POST /api/chat/ ('hi') -> intent={chat_data['intent']}, answer length={len(chat_data['answer'])}")

    print("\n[SUCCESS] Phase 6 API Layer verification PASSED!")

if __name__ == "__main__":
    run_tests()
