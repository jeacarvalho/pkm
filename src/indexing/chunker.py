"""Text chunking utilities for Obsidian notes."""

import re
from typing import List

import tiktoken

from src.utils.exceptions import ChunkingError
from src.indexing.text_cleaner import count_tokens


def chunk_text(
    text: str,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
    model: str = "cl100k_base",
) -> List[str]:
    """Split text into chunks based on token count with overlap.

    For small texts (< max_tokens), returns the text as a single chunk.
    For large texts, splits into chunks of approximately max_tokens with overlap.

    Args:
        text: Text to chunk.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Number of overlapping tokens between chunks.
        model: Tokenizer model to use.

    Returns:
        List of text chunks.

    Raises:
        ChunkingError: If chunking fails.

    Example:
        >>> text = "word " * 2000
        >>> chunks = chunk_text(text, max_tokens=800, overlap_tokens=100)
        >>> len(chunks) > 1
        True
    """
    try:
        # Get encoder
        encoder = tiktoken.get_encoding(model)

        # Encode text to tokens
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
            chunk_text_str = encoder.decode(chunk_tokens)

            # Try to end at a sentence or paragraph boundary
            if end < len(tokens):
                # Look for sentence ending
                last_period = chunk_text_str.rfind(".")
                last_newline = chunk_text_str.rfind("\n")

                # Prefer newline, then period, but only if we're not too far back
                boundary = -1
                if last_newline > len(chunk_text_str) * 0.7:
                    boundary = last_newline + 1
                elif last_period > len(chunk_text_str) * 0.7:
                    boundary = last_period + 1

                if boundary > 0:
                    chunk_text_str = chunk_text_str[:boundary].strip()
                    # Recalculate tokens for next start
                    chunk_tokens = encoder.encode(chunk_text_str)
                    end = start + len(chunk_tokens)

            chunks.append(chunk_text_str)

            # Move start position forward (accounting for overlap)
            if end < len(tokens):
                # Calculate new start with overlap
                overlap_chars = int(overlap_tokens * len(text) / len(tokens))
                new_start = max(0, end - overlap_tokens)
                start = new_start
            else:
                break

        return chunks

    except Exception as e:
        raise ChunkingError(f"Failed to chunk text: {e}") from e


def semantic_chunk(
    text: str, max_tokens: int = 800, overlap_tokens: int = 100
) -> List[str]:
    """Create semantic chunks by splitting on headers and paragraphs.

    This function attempts to preserve semantic boundaries (headers, paragraphs)
    when chunking text.

    Args:
        text: Text to chunk.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Number of overlapping tokens between chunks.

    Returns:
        List of text chunks preserving semantic boundaries.
    """
    try:
        # Split by headers first
        sections = re.split(r"\n(?=#{1,6}\s)", text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for section in sections:
            section_tokens = count_tokens(section)

            # If this section alone exceeds max_tokens, chunk it
            if section_tokens > max_tokens:
                # Flush current chunk first
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Chunk the large section
                section_chunks = chunk_text(section, max_tokens, overlap_tokens)
                chunks.extend(section_chunks)
                continue

            # Check if adding this section exceeds limit
            if current_tokens + section_tokens > max_tokens and current_chunk:
                # Flush current chunk
                chunks.append("\n".join(current_chunk))

                # Start new chunk with overlap
                # Take last section(s) for overlap
                overlap_chunk = []
                overlap_tokens_count = 0
                for prev_section in reversed(current_chunk):
                    prev_tokens = count_tokens(prev_section)
                    if overlap_tokens_count + prev_tokens <= overlap_tokens:
                        overlap_chunk.insert(0, prev_section)
                        overlap_tokens_count += prev_tokens
                    else:
                        break

                current_chunk = overlap_chunk + [section]
                current_tokens = overlap_tokens_count + section_tokens
            else:
                current_chunk.append(section)
                current_tokens += section_tokens

        # Flush remaining content
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks if chunks else [text]

    except Exception as e:
        raise ChunkingError(f"Failed to semantic chunk: {e}") from e
