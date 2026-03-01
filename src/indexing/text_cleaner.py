"""Text cleaning utilities for Obsidian notes."""

import re
from typing import List, Optional

import tiktoken

from src.utils.exceptions import TextCleaningError


def clean_text(content: str) -> str:
    """Clean Obsidian markdown text by removing frontmatter, links, and formatting.

    Args:
        content: Raw markdown content from an Obsidian note.

    Returns:
        Cleaned text ready for embedding.

    Raises:
        TextCleaningError: If cleaning fails.

    Example:
        >>> content = "---\\ntags: [test]\\n---\\nHello [[World]]"
        >>> clean_text(content)
        'Hello World'
    """
    try:
        # Remove frontmatter YAML
        content = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

        # Remove Obsidian links but keep text [[Link]] -> Link
        content = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", content)

        # Remove markdown links but keep text [text](url) -> text
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

        # Remove code blocks
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

        # Remove inline code
        content = re.sub(r"`[^`]+`", "", content)

        # Remove markdown headers (keep text, remove #)
        content = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)

        # Remove bold/italic markers but keep text
        content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
        content = re.sub(r"\*([^*]+)\*", r"\1", content)
        content = re.sub(r"__([^_]+)__", r"\1", content)
        content = re.sub(r"_([^_]+)_", r"\1", content)

        # Remove HTML tags
        content = re.sub(r"<[^\u003e]+>", "", content)

        # Remove blockquotes markers
        content = re.sub(r"^\s*>\s*", "", content, flags=re.MULTILINE)

        # Remove horizontal rules
        content = re.sub(r"^---\s*$", "", content, flags=re.MULTILINE)

        # Remove task list markers
        content = re.sub(r"^\s*[-*]\s*\[[ x]\]\s*", "", content, flags=re.MULTILINE)

        # Normalize whitespace
        content = re.sub(r"\n+", "\n", content)
        content = re.sub(r" +", " ", content)

        # Strip leading/trailing whitespace
        content = content.strip()

        return content

    except Exception as e:
        raise TextCleaningError(f"Failed to clean text: {e}") from e


def extract_tags(content: str) -> List[str]:
    """Extract tags from Obsidian note content.

    Args:
        content: Raw markdown content.

    Returns:
        List of unique tags found in the content.
    """
    try:
        # Extract #tags (but not inside code blocks)
        # Remove code blocks first
        content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

        # Find hashtags that are not part of markdown headers
        tags = re.findall(r"(?<!\w)#([\w\-]+)(?!\w)", content_no_code)

        # Also check frontmatter for tags
        frontmatter_match = re.search(r"^---\n(.*?)\n---", content, flags=re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            # Look for tags: [tag1, tag2] or tags:\n  - tag1\n  - tag2
            yaml_tags = re.findall(r"tags:\s*\[?([^\]]+)\]?", frontmatter)
            if yaml_tags:
                tags_str = yaml_tags[0]
                yaml_tags_list = [t.strip().strip("\"'") for t in tags_str.split(",")]
                tags.extend(yaml_tags_list)

        return list(set(tag.lower() for tag in tags if tag))

    except Exception:
        return []


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for.
        model: Tokenizer model to use.

    Returns:
        Number of tokens in text.
    """
    try:
        encoder = tiktoken.get_encoding(model)
        return len(encoder.encode(text))
    except Exception:
        # Fallback to approximate count
        return len(text.split())
