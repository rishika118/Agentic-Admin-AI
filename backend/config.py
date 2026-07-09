"""
config.py — Centralised Configuration
======================================
What it does:
- Reads all environment variables from the .env file using Pydantic's BaseSettings.
- Exposes a single `settings` object that every other module imports.

Why it exists:
- Nothing should be hard-coded. By centralising config here we can change
  values in .env without touching source code.

How it connects:
- app.py imports `settings` for the app title and CORS.
- database/postgres.py will import it for the DB connection string.
- agents and RAG modules will import it for model names, Qdrant URL, etc.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Agentic Admin AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"          # development | production
    DEBUG: bool = True

    # Allowed origins for CORS (React dev server default)
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # ------------------------------------------------------------------ #
    # PostgreSQL
    # ------------------------------------------------------------------ #
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "agentic_admin"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"

    # Convenience property — assembled from the fields above
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------ #
    # Qdrant (Vector Database)
    # ------------------------------------------------------------------ #
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "admin_documents"

    # ------------------------------------------------------------------ #
    # Ollama (Local LLM)
    # ------------------------------------------------------------------ #
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:latest"

    # ------------------------------------------------------------------ #
    # Embeddings
    # ------------------------------------------------------------------ #
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384              # dimension for bge-small-en-v1.5

    # ------------------------------------------------------------------ #
    # File Storage
    # ------------------------------------------------------------------ #
    UPLOAD_FOLDER: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ------------------------------------------------------------------ #
    # Text Chunking
    # ------------------------------------------------------------------ #
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # ------------------------------------------------------------------ #
    # (Reserved for future phases)
    # OPENAI_API_KEY: str = ""
    # ------------------------------------------------------------------ #

    # Pydantic v2 — read from .env file automatically
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # ignore any extra keys in .env
    )


# Single shared instance — import this everywhere
settings = Settings()
