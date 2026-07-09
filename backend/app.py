"""
app.py — FastAPI Application Entry Point
========================================
This is the starting point of the backend server.

What it does:
- Creates the FastAPI app instance.
- Registers all API routers.
- Calls create_tables() on startup so PostgreSQL tables exist.
- Provides health-check endpoints to verify all services are running.

How to run:
    cd backend
    venv\\Scripts\\activate
    venv\\Scripts\\uvicorn app:app --reload --port 8000

Then visit:
    http://localhost:8000/docs          <- Swagger UI (interactive API docs)
    http://localhost:8000/health        <- JSON health check
    http://localhost:8000/health/full   <- Full service connectivity check
"""

import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.postgres import create_tables

from routers.chat      import router as chat_router
from routers.documents import router as documents_router


# ---------------------------------------------------------------------------
# Lifespan — runs once at startup and once at shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- STARTUP ----
    print(f"[STARTUP] Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    create_tables()   # Auto-create DB tables if they don't exist
    print(f"[STARTUP] PostgreSQL tables ready.")
    print(f"[STARTUP] Swagger docs: http://localhost:8000/docs")
    print(f"[STARTUP] Startup complete.")

    yield   # <-- The app runs here (serving requests)

    # ---- SHUTDOWN ----
    print("[SHUTDOWN] Shutting down...")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = (
        "Agentic AI for Administrative Support — NIT Calicut Internship Project\n\n"
        "## API Endpoints\n"
        "- **POST /api/chat/** — Ask a question about NIT Calicut documents\n"
        "- **POST /api/documents/upload** — Upload and ingest a PDF\n"
        "- **GET /api/documents/** — List all ingested documents\n"
        "- **DELETE /api/documents/{id}** — Remove a document\n"
    ),
    lifespan    = lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the React frontend to talk to the backend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.CORS_ORIGINS,   # ["http://localhost:5173"]
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
app.include_router(chat_router)
app.include_router(documents_router)


# ---------------------------------------------------------------------------
# Health check endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    """
    Basic health check — confirms the FastAPI server is running.
    This is the endpoint Render/Railway/etc. use to check if the app is alive.
    """
    return {
        "status":      "ok",
        "app":         settings.APP_NAME,
        "version":     settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/full", tags=["System"])
async def health_check_full():
    """
    Full service connectivity check.
    Tests that PostgreSQL, Qdrant, and Ollama are all reachable.
    Useful for debugging after a machine restart.
    """
    services = {}

    # PostgreSQL
    try:
        from database.postgres import SessionLocal
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        services["postgresql"] = "ok"
    except Exception as e:
        services["postgresql"] = f"error: {str(e)[:80]}"

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=settings.QDRANT_HOST,
                              port=settings.QDRANT_PORT,
                              prefer_grpc=False)
        collections = client.get_collections()
        count = len(collections.collections)
        services["qdrant"] = f"ok ({count} collections)"
    except Exception as e:
        services["qdrant"] = f"error: {str(e)[:80]}"

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                services["ollama"] = f"ok (models: {', '.join(models[:3])})"
            else:
                services["ollama"] = f"error: HTTP {resp.status_code}"
    except Exception as e:
        services["ollama"] = f"error: {str(e)[:80]}"

    overall = "ok" if all(v.startswith("ok") for v in services.values()) else "degraded"
    return {
        "status":   overall,
        "services": services,
    }


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["System"])
async def root():
    """Landing message — useful when you open the server URL in a browser."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API.",
        "docs":    "http://localhost:8000/docs",
        "health":  "http://localhost:8000/health/full",
    }
