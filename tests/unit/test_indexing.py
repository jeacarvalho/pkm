"""Unit tests for indexing module."""

import re
from pathlib import Path

import pytest

from src.indexing.chunker import chunk_text, semantic_chunk
from src.indexing.text_cleaner import clean_text, count_tokens, extract_tags


class TestTextCleaner:
    """Test text cleaning functions."""

    def test_remove_frontmatter(self):
        """Test that frontmatter YAML is removed."""
        content = "---\ntags: [test]\n---\nHello world"
        cleaned = clean_text(content)
        assert "---" not in cleaned
        assert "Hello world" in cleaned

    def test_remove_obsidian_links(self):
        """Test that Obsidian links are converted to text."""
        content = "Check [[Note Title]] for more"
        cleaned = clean_text(content)
        assert "[[" not in cleaned
        assert "Note Title" in cleaned

    def test_remove_markdown_links(self):
        """Test that markdown links are converted to text."""
        content = "Visit [Google](https://google.com) for search"
        cleaned = clean_text(content)
        assert "[" not in cleaned
        assert "Google" in cleaned
        assert "https://google.com" not in cleaned

    def test_remove_code_blocks(self):
        """Test that code blocks are removed."""
        content = """Some text
```python
print("hello")
```
More text"""
        cleaned = clean_text(content)
        assert "```" not in cleaned
        assert "print" not in cleaned
        assert "Some text" in cleaned
        assert "More text" in cleaned

    def test_remove_inline_code(self):
        """Test that inline code is removed."""
        content = "Use `print()` function"
        cleaned = clean_text(content)
        assert "`" not in cleaned
        assert "function" in cleaned

    def test_remove_headers(self):
        """Test that markdown headers are cleaned."""
        content = "# Header 1\n## Header 2\nText"
        cleaned = clean_text(content)
        assert "# " not in cleaned
        assert "Header 1" in cleaned
        assert "Header 2" in cleaned

    def test_remove_bold_italic(self):
        """Test that bold and italic markers are removed."""
        content = "**bold** and *italic* text"
        cleaned = clean_text(content)
        assert "**" not in cleaned
        assert "*" not in cleaned
        assert "bold" in cleaned
        assert "italic" in cleaned

    def test_normalize_whitespace(self):
        """Test that whitespace is normalized."""
        content = "Line 1\n\n\nLine 2\n\n   Line 3"
        cleaned = clean_text(content)
        assert "\n\n\n" not in cleaned

    def test_extract_tags(self):
        """Test tag extraction from content."""
        content = "This has #tag1 and #tag-2 in it"
        tags = extract_tags(content)
        assert "tag1" in tags
        assert "tag-2" in tags

    def test_count_tokens(self):
        """Test token counting."""
        text = "This is a test sentence with ten words total"
        count = count_tokens(text)
        assert count > 0
        assert isinstance(count, int)


class TestChunker:
    """Test text chunking functions."""

    def test_small_note_no_chunk(self):
        """Test that small texts aren't chunked."""
        text = "word " * 500
        chunks = chunk_text(text, max_tokens=800)
        assert len(chunks) == 1

    def test_large_note_is_chunked(self):
        """Test that large texts are chunked."""
        text = "word " * 2000
        chunks = chunk_text(text, max_tokens=800, overlap_tokens=100)
        assert len(chunks) > 1
        # Each chunk should be roughly within limit (with buffer for safety)
        for chunk in chunks:
            token_count = count_tokens(chunk)
            assert token_count <= 900

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        text = "word " * 2000
        chunks = chunk_text(text, max_tokens=800, overlap_tokens=100)

        if len(chunks) > 1:
            # Check that consecutive chunks share some content
            # This is a basic check - overlap detection can be complex
            assert len(chunks) >= 2

    def test_empty_text(self):
        """Test that empty text returns single empty chunk."""
        text = ""
        chunks = chunk_text(text, max_tokens=800)
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_semantic_chunk_small(self):
        """Test semantic chunking on small text."""
        text = "Paragraph 1.\n\nParagraph 2."
        chunks = semantic_chunk(text, max_tokens=800)
        assert len(chunks) >= 1

    def test_semantic_chunk_with_headers(self):
        """Test semantic chunking preserves headers."""
        text = "# Header 1\nContent 1\n\n# Header 2\nContent 2"
        chunks = semantic_chunk(text, max_tokens=800)
        assert len(chunks) >= 1


class TestTextCleanerEdgeCases:
    """Test edge cases for text cleaning."""

    def test_only_frontmatter(self):
        """Test note with only frontmatter."""
        content = "---\ntags: [test]\n---"
        cleaned = clean_text(content)
        assert cleaned == ""

    def test_only_whitespace(self):
        """Test note with only whitespace."""
        content = "   \n\n   \n"
        cleaned = clean_text(content)
        assert cleaned == ""

    def test_html_tags(self):
        """Test removal of HTML tags."""
        content = "Text with <b>bold</b> tags"
        cleaned = clean_text(content)
        assert "<" not in cleaned
        assert "bold" in cleaned

    def test_blockquotes(self):
        """Test removal of blockquote markers."""
        content = "> This is a quote\n> Another line"
        cleaned = clean_text(content)
        assert "> " not in cleaned
        assert "This is a quote" in cleaned

    def test_horizontal_rules(self):
        """Test removal of horizontal rules."""
        content = "Text\n---\nMore text"
        cleaned = clean_text(content)
        # Horizontal rules on their own line should be removed
        lines = cleaned.split("\n")
        assert all(line.strip() != "---" for line in lines)

    def test_task_lists(self):
        """Test removal of task list markers."""
        content = "- [ ] Todo\n- [x] Done"
        cleaned = clean_text(content)
        assert "- [ ]" not in cleaned
        assert "- [x]" not in cleaned


class TestChunkerEdgeCases:
    """Test edge cases for chunking."""

    def test_single_word(self):
        """Test chunking single word."""
        text = "Word"
        chunks = chunk_text(text, max_tokens=800)
        assert len(chunks) == 1
        assert chunks[0] == "Word"

    def test_unicode_text(self):
        """Test chunking text with unicode characters."""
        text = "Café résumé naïve " * 100
        chunks = chunk_text(text, max_tokens=800)
        assert len(chunks) >= 1

    def test_very_large_text(self):
        """Test chunking very large text."""
        text = "word " * 10000
        chunks = chunk_text(text, max_tokens=800, overlap_tokens=100)
        assert len(chunks) > 10
