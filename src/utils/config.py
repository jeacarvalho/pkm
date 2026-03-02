"""Configuration settings for Obsidian RAG using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    Attributes:
        vault_path: Path to Obsidian vault directory.
        chroma_persist_dir: Directory for ChromaDB persistence.
        ollama_host: Ollama API endpoint URL.
        embedding_model: Name of the embedding model to use.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Path to log file.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Number of overlapping tokens between chunks.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Vault Configuration
    vault_path: Path = Field(
        default=Path("/home/s015533607/MEGAsync/Minhas_notas"),
        description="Path to Obsidian vault directory",
    )

    # ChromaDB Configuration
    chroma_persist_dir: Path = Field(
        default=Path("./data/vectors/chroma_db"),
        description="Directory for ChromaDB persistence",
    )

    # Ollama Configuration
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama API endpoint URL"
    )
    embedding_model: str = Field(
        default="bge-m3", description="Name of the embedding model to use"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(
        default=Path("./data/logs/indexing.log"), description="Path to log file"
    )

    # Chunking Configuration
    max_tokens: int = Field(default=800, description="Maximum tokens per chunk")
    overlap_tokens: int = Field(
        default=100, description="Number of overlapping tokens between chunks"
    )

    # Gemini API Configuration
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for translation",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model for translation",
    )

    # PDF Configuration
    pdf_library_path: Path = Field(
        default=Path("/home/s015533607/Calibre Library"),
        description="Path to PDF library directory",
    )
    translation_target_language: str = Field(
        default="pt",
        description="Target language for translation (ISO 639-1 code)",
    )

    # Retrieval & Re-Rank Configuration (Sprint 03)
    rerank_model: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        description="Cross-encoder model for re-ranking",
    )
    rerank_threshold: float = Field(
        default=0.75,
        description="Minimum re-rank score to retain (0.0-1.0)",
    )
    rerank_max_length: int = Field(
        default=512,
        description="Max token length for re-ranker document truncation",
    )
    rerank_device: Optional[str] = Field(
        default=None,
        description="Device for re-ranker ('cuda', 'cpu', or None for auto)",
    )
    vector_search_top_k: int = Field(
        default=20,
        description="Number of initial results from vector search",
    )
    rerank_top_k: int = Field(
        default=5,
        description="Number of final results after re-ranking",
    )

    # Validation Configuration (Sprint 04)
    validation_model: str = Field(
        default="llama3.2",
        description="Ollama model for validation",
    )
    validation_temperature: float = Field(
        default=0.0,
        description="Temperature for validation (0.0 = deterministic)",
    )
    validation_timeout: int = Field(
        default=60,
        description="Timeout for validation API calls in seconds",
    )
    validation_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts on validation failure",
    )

    # Output Configuration (Sprint 05)
    output_dir: Path = Field(
        default=Path("./data/processed"),
        description="Output directory for generated Markdown files",
    )

    @property
    def collection_name(self) -> str:
        """Return the ChromaDB collection name."""
        return "obsidian_notes"

    @property
    def embedding_dimensions(self) -> int:
        """Return the embedding dimensions for the model."""
        return 1024


# Global settings instance
settings = Settings()
