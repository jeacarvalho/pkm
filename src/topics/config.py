"""Configuration for topic extraction module."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class TopicConfig(BaseSettings):
    """Configuration for topic extraction and matching."""

    # Gemini Configuration
    gemini_model: str = Field(
        default="gemini-2.5-flash-lite", description="Gemini model for topic extraction"
    )
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")

    # Topic Extraction Settings
    topics_per_note: int = Field(
        default=10, description="Number of topics to extract per note"
    )
    weight_min: int = Field(default=5, description="Minimum topic weight")
    weight_max: int = Field(default=10, description="Maximum topic weight")
    batch_size: int = Field(
        default=1, description="Notes to process at once (always 1 for safety)"
    )

    # Processing Settings
    max_note_length: int = Field(
        default=5000, description="Maximum characters to send to Gemini per note"
    )
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts on API failure"
    )
    retry_delay: float = Field(
        default=2.0, description="Initial delay between retries (seconds)"
    )
    api_timeout: int = Field(default=90, description="API timeout in seconds")
    api_delay: float = Field(
        default=8.0,
        description="Delay between API calls to avoid rate limiting (seconds)",
    )

    # Sprint 09: Vault Writer Settings
    dry_run: bool = Field(
        default=False, description="Dry-run mode (log only, don't write)"
    )
    limit: int = Field(
        default=0, description="Limit number of notes to process (0 = unlimited)"
    )

    # Sprint 10: Topic Matching Settings
    # Nota: fuzzy_threshold=40 e match_threshold=0.0 foram ajustados para encontrar mais matches
    fuzzy_threshold: int = Field(
        default=40,
        description="Threshold para fuzzy match (0-100). Default: 40 (para encontrar mais matches)",
    )
    match_top_k: int = Field(default=20, description="Top-K matches para retornar")
    match_threshold: float = Field(
        default=0.0,
        description="Score mínimo para match (0-100). Default: 0.0 (para aceitar mais resultados)",
    )

    # Paths
    log_dir: Path = Field(
        default=Path("data/logs/topics"),
        description="Directory for topic extraction logs",
    )

    class Config:
        env_prefix = "TOPICS_"
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure log directory exists
        self.create_log_dir()

    def create_log_dir(self):
        """Create log directory if it doesn't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
topics_config = TopicConfig()
