"""Unit tests for output module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.output.markdown_generator import MarkdownGenerator
from src.output.pipeline import OutputPipeline
from src.utils.config import Settings


@pytest.fixture
def config():
    """Create test configuration."""
    return Settings()


@pytest.fixture
def generator(config):
    """Create MarkdownGenerator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield MarkdownGenerator(config, output_dir=tmpdir)


@pytest.fixture
def pipeline(config):
    """Create OutputPipeline instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config.output_dir = tmpdir
        yield OutputPipeline(config)


class TestMarkdownGenerator:
    """Tests for MarkdownGenerator class."""

    def test_generate_frontmatter(self, generator):
        """Test YAML frontmatter generation."""
        frontmatter = generator._generate_frontmatter(
            book_title="Test Book",
            book_path="/path/to/book.pdf",
            validated_chunks=[
                {"validated_matches": [{}]},
                {"validated_matches": [{}, {}]},
            ],
        )

        assert "---" in frontmatter
        # Note: default validation_engine is 'ollama' based on config
        assert "validation_engine:" in frontmatter
        assert "book_title: Test Book" in frontmatter
        assert "total_chunks: 2" in frontmatter
        assert "total_validated_matches: 3" in frontmatter

    def test_generate_body_with_matches(self, generator):
        """Test body generation with validated matches."""
        chunks = [
            {
                "chapter_title": "Chapter 1",
                "chunk_text": "Test chunk content",
                "validated_matches": [
                    {
                        "metadata": {"note_title": "Test Note"},
                        "rerank_score": 0.85,
                        "validation": {
                            "confidence": 90,
                            "reason": "Test reason",
                        },
                    }
                ],
            }
        ]

        body = generator._generate_body("Test Book", chunks)

        assert "# Conexões Validadas: Test Book" in body
        assert "Chapter 1" in body
        assert "Test chunk content" in body
        assert "[[Test Note]]" in body
        assert "Re-Rank Score:" in body
        assert "90/100" in body

    def test_generate_body_without_matches(self, generator):
        """Test body generation without validated matches."""
        chunks = [
            {
                "chapter_title": "Chapter 1",
                "chunk_text": "Test chunk",
                "validated_matches": [],
            }
        ]

        body = generator._generate_body("Test Book", chunks)

        assert "Nenhuma nota validada" in body

    def test_generate_summary_table(self, generator):
        """Test summary table generation."""
        chunks = [
            {
                "validated_matches": [
                    {
                        "metadata": {"note_title": "Note A"},
                        "rerank_score": 0.9,
                        "validation": {"confidence": 95},
                    },
                    {
                        "metadata": {"note_title": "Note A"},
                        "rerank_score": 0.8,
                        "validation": {"confidence": 85},
                    },
                ]
            },
            {
                "validated_matches": [
                    {
                        "metadata": {"note_title": "Note B"},
                        "rerank_score": 0.7,
                        "validation": {"confidence": 75},
                    }
                ]
            },
        ]

        table = generator._generate_summary_table(chunks)

        assert "| Nota |" in table
        assert "[[Note A]]" in table
        assert "[[Note B]]" in table

    def test_generate_book_file(self, generator):
        """Test complete file generation."""
        chunks = [
            {
                "chapter_title": "Chapter 1",
                "chunk_text": "Test content",
                "validated_matches": [
                    {
                        "metadata": {"note_title": "Test Note"},
                        "rerank_score": 0.85,
                        "validation": {
                            "confidence": 90,
                            "reason": "Test reason",
                        },
                    }
                ],
            }
        ]

        output_path = generator.generate_book_file(
            book_title="Test Book",
            book_path="/path/to/book.pdf",
            validated_chunks=chunks,
            output_filename="test_output.md",
        )

        assert output_path.exists()
        assert output_path.name == "test_output.md"

        content = output_path.read_text()
        assert "# Conexões Validadas: Test Book" in content
        assert "[[Test Note]]" in content


class TestOutputPipeline:
    """Tests for OutputPipeline class."""

    def test_process_book_chunks(self, pipeline):
        """Test processing book chunks."""
        book_chunks = [
            {
                "chunk_id": 1,
                "chapter_title": "Chapter 1",
                "text": "Test content 1",
                "validated_matches": [
                    {
                        "metadata": {"note_title": "Note 1"},
                        "rerank_score": 0.85,
                        "validation": {
                            "confidence": 90,
                            "reason": "Match found",
                        },
                    }
                ],
            },
            {
                "chunk_id": 2,
                "chapter_title": "Chapter 1",
                "text": "Test content 2",
                "validated_matches": [],
            },
        ]

        stats = pipeline.process_book_chunks(
            book_chunks=book_chunks,
            book_title="Test Book",
            book_path="/path/to/book.pdf",
        )

        assert stats["total_chunks"] == 2
        assert stats["chunks_with_matches"] == 1
        assert stats["total_validated_matches"] == 1
        assert "output_file" in stats

    def test_process_book_chunks_with_translated_text(self, pipeline):
        """Test processing with translated text."""
        book_chunks = [
            {
                "chunk_id": 1,
                "chapter_title": "Chapter 1",
                "text": "Original",
                "translated_text": "Translated content",
                "validated_matches": [],
            }
        ]

        stats = pipeline.process_book_chunks(
            book_chunks=book_chunks,
            book_title="Test Book",
            book_path="/path/to/book.pdf",
        )

        assert stats["total_chunks"] == 1

    def test_process_book_file_not_found(self, pipeline):
        """Test handling of missing book file."""
        stats = pipeline.process_book_file("/nonexistent/file.json")

        assert "error" in stats

    def test_process_library_no_files(self, pipeline):
        """Test handling of empty library."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = pipeline.process_library(tmpdir)

            assert len(results) == 0
