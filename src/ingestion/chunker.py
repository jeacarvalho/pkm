"""Chunking utilities for PDF text (512 tokens for books)."""

from typing import List

import tiktoken

from src.utils.exceptions import ChunkingError


def chunk_text_for_book(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    model: str = "cl100k_base",
) -> List[str]:
    """Split book text into chunks optimized for RAG.

    Books use smaller chunks (512 tokens) than vault notes (800 tokens)
    for denser semantic content and better retrieval precision.

    Args:
        text: Text to chunk.
        max_tokens: Maximum tokens per chunk (default: 512 for books).
        overlap_tokens: Number of overlapping tokens between chunks.
        model: Tokenizer model to use.

    Returns:
        List of text chunks.

    Raises:
        ChunkingError: If chunking fails.

    Example:
        >>> text = "word " * 1000
        >>> chunks = chunk_text_for_book(text, max_tokens=512)
        >>> len(chunks) > 1
        True
    """
    try:
        encoder = tiktoken.get_encoding(model)
        tokens = encoder.encode(text)

        # If text is small enough, return as is
        if len(tokens) <= max_tokens:
            return [text]

        chunks = []
        start = 0

        while start < len(tokens):
            # Calculate end position
            end = min(start + max_tokens, len(tokens))

            # Decode chunk back to text
            chunk_tokens = tokens[start:end]
            chunk_text = encoder.decode(chunk_tokens)

            # Try to end at a sentence or paragraph boundary
            if end < len(tokens):
                # Look for sentence ending
                last_period = chunk_text.rfind(".")
                last_newline = chunk_text.rfind("\n")

                # Prefer newline, then period
                boundary = -1
                if last_newline > len(chunk_text) * 0.7:
                    boundary = last_newline + 1
                elif last_period > len(chunk_text) * 0.7:
                    boundary = last_period + 1

                if boundary > 0:
                    chunk_text = chunk_text[:boundary].strip()
                    # Recalculate tokens for next start
                    chunk_tokens = encoder.encode(chunk_text)
                    end = start + len(chunk_tokens)

            chunks.append(chunk_text)

            # Move start position forward (accounting for overlap)
            if end < len(tokens):
                # Calculate new start with overlap
                overlap_token_count = min(overlap_tokens, end - start)
                new_start = max(0, end - overlap_token_count)
                start = new_start
            else:
                break

        return chunks

    except Exception as e:
        raise ChunkingError(f"Failed to chunk text for book: {e}") from e


def chunk_book_by_chapters(
    chapters: List[dict], max_tokens: int = 512, overlap_tokens: int = 50
) -> List[dict]:
    """Chunk book chapters into smaller pieces.

    Args:
        chapters: List of chapter dicts with 'title' and 'text' keys.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Number of overlapping tokens.

    Returns:
        List of chunk dicts with chapter info preserved.
    """
    chunked_chapters = []

    for chapter in chapters:
        title = chapter.get("title", "Untitled")
        text = chapter.get("text", "")
        level = chapter.get("level", 1)

        if not text.strip():
            continue

        # Chunk the chapter text
        chunks = chunk_text_for_book(text, max_tokens, overlap_tokens)

        # Create chunk entries
        for chunk_id, chunk_text in enumerate(chunks):
            chunked_chapters.append(
                {
                    "chapter_title": title,
                    "chapter_level": level,
                    "chunk_id": chunk_id,
                    "chunk_count": len(chunks),
                    "text": chunk_text,
                    "token_count": len(chunk_text.split()),
                    "page_start": chapter.get("page_start"),
                    "page_end": chapter.get("page_end"),
                }
            )

    return chunked_chapters
