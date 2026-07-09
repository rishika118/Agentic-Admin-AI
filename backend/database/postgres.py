"""
database/postgres.py — PostgreSQL Engine, Session & ORM Models
===============================================================

What it does:
    1. Creates a SQLAlchemy engine that connects to PostgreSQL.
    2. Provides a `get_db()` function that FastAPI uses to give each
       API request its own database session (and close it when done).
    3. Defines the ORM models — Python classes that map to DB tables:
           Document  →  `documents` table
           Chunk     →  `chunks` table
           Template  →  `templates` table
    4. Exposes `create_tables()` which app.py calls on startup to
       auto-create any missing tables.

Why it exists:
    We need a structured, relational store for document metadata and
    chunk records. SQLAlchemy ORM keeps DB code readable and Pythonic —
    you work with Python objects instead of raw SQL strings.

How it connects:
    - app.py       → calls create_tables() at startup
    - ingestion/*  → uses `get_db()` to INSERT document + chunk records
    - agents/*     → reads chunk metadata to build citations
    - tools/*      → reads/writes templates
"""

from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config import settings

# ---------------------------------------------------------------------------
# 1. ENGINE
#    The engine is the core object that knows HOW to talk to PostgreSQL.
#    We create it once and reuse it for the entire app lifetime.
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping=True makes SQLAlchemy test the connection before using it.
    # This avoids "connection gone away" errors after the DB is idle.
    pool_pre_ping=True,
    echo=settings.DEBUG,   # When DEBUG=True in .env, SQL queries are printed to the console.
                           # Very useful for learning and debugging — set to False in production.
)

# ---------------------------------------------------------------------------
# 2. SESSION FACTORY
#    A session is a temporary "conversation" with the database.
#    Every database read/write happens inside a session.
#    SessionLocal() creates a new session each time it is called.
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # We control when to commit (save) changes ourselves.
    autoflush=False,    # We control when to flush (send SQL) ourselves.
)


# ---------------------------------------------------------------------------
# 3. BASE CLASS
#    All ORM models (Document, Chunk, Template) inherit from this Base.
#    SQLAlchemy uses it to track which classes map to which tables.
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 4. ORM MODELS (Python class → PostgreSQL table)
# ---------------------------------------------------------------------------

class Document(Base):
    """
    Represents a single administrative PDF document.

    Table name: documents

    Each row = one uploaded PDF file.
    The `chunks` relationship lets us write:
        doc.chunks   →  list of all Chunk objects for this document
    """
    __tablename__ = "documents"

    # Primary key — auto-incremented integer
    id = Column(Integer, primary_key=True, index=True)

    # Basic document identity
    title           = Column(String(500), nullable=False)
    department      = Column(String(200), nullable=True)   # e.g. "Academic Section"
    category        = Column(String(100), nullable=True)   # e.g. "Circular", "Office Order"
    document_number = Column(String(100), nullable=True)   # e.g. "NITC/AC/2024/001"
    date            = Column(String(50),  nullable=True)   # Store as string for flexibility
    version         = Column(String(20),  nullable=True)   # e.g. "v1", "Rev 2"
    status          = Column(String(50),  nullable=True, default="active")  # active | archived

    # File tracking
    source_url = Column(String(1000), nullable=True)   # Original URL on NIT Calicut website
    file_path  = Column(String(1000), nullable=False)  # Local path to the saved PDF
    file_hash  = Column(String(64),   nullable=True, unique=True)  # SHA-256 hash for dedup check

    # Processing info
    is_scanned = Column(Boolean, default=False)  # True if PaddleOCR was needed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship — lets us do: document.chunks to get all related chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document id={self.id} title='{self.title[:40]}...'>"


class Chunk(Base):
    """
    Represents one text chunk from a document.

    Table name: chunks

    A single Document is split into many Chunks for embedding.
    Each Chunk stores:
      - The raw text (for display in citations)
      - The page number it came from (for linking back to the PDF)
      - Which embedding model was used (for future model changes)

    NOTE: The actual embedding vector is stored in Qdrant, NOT here.
          We store the Qdrant vector ID (chunk_id) so we can link
          a Qdrant search result back to this PostgreSQL record.
    """
    __tablename__ = "chunks"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    # chunk_id = the UUID we assign in Qdrant (so we can cross-reference)
    chunk_id    = Column(String(100), nullable=False, unique=True)
    chunk_index = Column(Integer,     nullable=False)  # 0-based order within the document
    page_no     = Column(Integer,     nullable=True)   # Page this chunk came from
    chunk_text  = Column(Text,        nullable=False)  # The actual text content

    embedding_model = Column(String(200), nullable=True)  # e.g. "BAAI/bge-small-en-v1.5"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Reverse relationship — lets us do: chunk.document to get the parent Document
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk id={self.id} doc_id={self.document_id} page={self.page_no} idx={self.chunk_index}>"


class Template(Base):
    """
    Stores letter and report templates used by the Task Agent.

    Table name: templates

    The Task Agent loads these templates when drafting letters or reports.
    Templates are plain-text skeletons with placeholder variables.

    Example:
        template_name = "leave_request"
        template_type = "letter"
        content = "To,\nThe Director,\nNIT Calicut\n\nSub: Leave Request\n\nRespected Sir,\n..."
    """
    __tablename__ = "templates"

    id            = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(200), nullable=False, unique=True)  # e.g. "leave_request"
    template_type = Column(String(100), nullable=False)               # e.g. "letter" | "report"
    content       = Column(Text,        nullable=False)               # The template text body

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Template id={self.id} name='{self.template_name}' type='{self.template_type}'>"


# ---------------------------------------------------------------------------
# 5. TABLE CREATION
#    Called once when FastAPI starts up (see app.py).
#    SQLAlchemy checks if the tables exist — if not, it creates them.
#    If they already exist, it does nothing (safe to call multiple times).
# ---------------------------------------------------------------------------
def create_tables() -> None:
    """
    Create all database tables that don't exist yet.
    This is called from app.py on server startup.
    """
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created (or already exist).")


# ---------------------------------------------------------------------------
# 6. DATABASE SESSION DEPENDENCY
#    FastAPI's dependency injection system calls get_db() for every
#    route that declares `db: Session = Depends(get_db)`.
#
#    The `yield` pattern ensures:
#      - A new session is opened for each request.
#      - The session is ALWAYS closed when the request finishes
#        (even if an error occurred).
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage in a route:
        from fastapi import Depends
        from database.postgres import get_db

        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            docs = db.query(Document).all()
            return docs
    """
    db = SessionLocal()
    try:
        yield db        # The route function gets the `db` session here
    finally:
        db.close()      # Always close the session when the request is done
