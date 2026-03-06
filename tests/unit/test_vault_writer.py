"""Unit tests for vault writer module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import yaml

from src.output.vault_writer import VaultWriter, slugify


class TestSlugify:
    """Test slugify function."""

    def test_slugify_basic(self):
        """Test basic slugify."""
        assert slugify("Hello World") == "hello_world"

    def test_slugify_special_chars(self):
        """Test slugify with special characters."""
        assert slugify("Test@#$%^&*()") == "test"

    def test_slugify_numbers(self):
        """Test slugify with numbers."""
        assert slugify("Chapter 1") == "chapter_1"

    def test_slugify_empty(self):
        """Test slugify with empty string."""
        assert slugify("") == ""

    def test_slugify_max_length(self):
        """Test slugify with max length."""
        result = slugify(
            "This is a very long title that should be truncated", max_length=20
        )
        assert len(result) <= 20


class TestVaultWriter:
    """Test VaultWriter class."""

    def test_init(self):
        """Test initialization."""
        writer = VaultWriter("/test/vault", "TestBook")

        assert writer.book_name == "TestBook"
        assert "TestBook" in str(writer.book_folder)

    def test_create_book_folder(self, tmp_path):
        """Test book folder creation."""
        book_dir = tmp_path / "books" / "TestBook"

        with patch.object(Path, "mkdir", return_value=None):
            writer = VaultWriter(str(book_dir.parent), "TestBook")
            result = writer.create_book_folder()

        assert "TestBook" in str(result)

    def test_generate_filename_with_title(self):
        """Test filename generation with chapter title."""
        writer = VaultWriter("/test/vault", "MyBook")

        chapter_data = {"book_name": "MyBook", "title": "Introduction"}

        filename = writer._generate_filename(0, chapter_data)

        assert "mybook" in filename
        assert "introduction" in filename
        assert filename.endswith(".md")

    def test_generate_filename_default_title(self):
        """Test filename generation with default title."""
        writer = VaultWriter("/test/vault", "MyBook")

        chapter_data = {"book_name": "MyBook", "title": "Chapter 1"}

        filename = writer._generate_filename(0, chapter_data)

        assert "mybook" in filename
        assert "capitulo01" in filename or "chapter" in filename.lower()

    def test_generate_filename_fallback(self):
        """Test filename generation fallback."""
        writer = VaultWriter("/test/vault", "MyBook")

        # No title provided
        chapter_data = {
            "book_name": "MyBook",
        }

        filename = writer._generate_filename(0, chapter_data)

        assert "mybook" in filename
        assert filename.endswith(".md")

    def test_build_markdown_basic(self, tmp_path):
        """Test basic markdown building."""
        with patch.object(Path, "mkdir", return_value=None):
            writer = VaultWriter(str(tmp_path), "TestBook")

        chapter_data = {
            "book_title": "Test Book",
            "author": "Test Author",
            "title": "Chapter 1",
            "start_page": 1,
            "end_page": 10,
            "rerank_threshold": 0.75,
            "was_cached": False,
            "topic_classification": None,
            "thematic_connections": [],
        }

        markdown = writer._build_markdown(0, chapter_data)

        assert "book_title: Test Book" in markdown
        assert "chapter_number: 1" in markdown
        assert "chapter_title: Chapter 1" in markdown

    def test_build_markdown_with_topics(self, tmp_path):
        """Test markdown with topic classification."""
        with patch.object(Path, "mkdir", return_value=None):
            writer = VaultWriter(str(tmp_path), "TestBook")

        chapter_data = {
            "book_title": "Test Book",
            "author": "",
            "title": "Chapter 1",
            "start_page": 1,
            "end_page": 10,
            "rerank_threshold": 0.75,
            "was_cached": True,
            "topic_classification": {
                "topics": [{"name": "test_topic", "weight": 8, "confidence": 0.9}],
                "cdu_primary": "321",
                "cdu_secondary": ["300"],
            },
            "thematic_connections": [],
        }

        markdown = writer._build_markdown(0, chapter_data)

        assert "topic_classification:" in markdown
        assert "test_topic" in markdown
        assert "cdu_primary: 321" in markdown

    def test_build_markdown_with_connections(self, tmp_path):
        """Test markdown with thematic connections."""
        with patch.object(Path, "mkdir", return_value=None):
            writer = VaultWriter(str(tmp_path), "TestBook")

        chapter_data = {
            "book_title": "Test Book",
            "author": "",
            "title": "Chapter 1",
            "start_page": 1,
            "end_page": 10,
            "rerank_threshold": 0.75,
            "was_cached": False,
            "topic_classification": None,
            "thematic_connections": [
                {
                    "note_title": "Related Note",
                    "score": 75.0,
                    "matched_topics": [
                        {"chapter_topic": "topic1", "vault_topic": "topic2"}
                    ],
                }
            ],
        }

        markdown = writer._build_markdown(0, chapter_data)

        # Just verify markdown was generated
        assert len(markdown) > 0
