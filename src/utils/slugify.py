"""Utility functions for text processing."""

import re
import unicodedata


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a safe filename slug.

    Args:
        text: Input text to convert
        max_length: Maximum length of the resulting slug

    Returns:
        Safe filename slug in lowercase
    """
    if not text:
        return ""

    # Remove accents
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Replace spaces and special chars with underscore
    text = re.sub(r"[^a-zA-Z0-9]", "_", text)

    # Remove multiple underscores
    text = re.sub(r"_+", "_", text)

    # Remove leading/trailing underscores
    text = text.strip("_")

    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip("_")

    return text.lower()
