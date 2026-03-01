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
