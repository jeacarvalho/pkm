"""Custom exceptions for Obsidian RAG."""


class ObsidianRAGError(Exception):
    """Base exception for Obsidian RAG."""

    pass


class VaultNotFoundError(ObsidianRAGError):
    """Raised when vault path does not exist."""

    pass


class EmbeddingError(ObsidianRAGError):
    """Raised when embedding generation fails."""

    pass


class ChromaDBError(ObsidianRAGError):
    """Raised when ChromaDB operation fails."""

    pass


class TextCleaningError(ObsidianRAGError):
    """Raised when text cleaning fails."""

    pass


class ChunkingError(ObsidianRAGError):
    """Raised when text chunking fails."""

    pass


class IndexingError(ObsidianRAGError):
    """Raised when note indexing fails."""

    pass
