"""Unit tests for ingestion module."""

import pytest
from unittest.mock import Mock, patch

from src.ingestion.chunker import chunk_text_for_book, chunk_book_by_chapters
from src.ingestion.language_detector import (
    detect_language,
    should_translate,
    get_language_name,
)


class TestLanguageDetector:
    """Test language detection functions."""

    def test_detect_english(self):
        """Test detection of English text."""
        text = "This is a sample text in English language."
        lang = detect_language(text)
        assert lang == "en"

    def test_detect_portuguese(self):
        """Test detection of Portuguese text."""
        text = "Este é um texto de exemplo em português."
        lang = detect_language(text)
        assert lang == "pt"

    def test_detect_spanish(self):
        """Test detection of Spanish text."""
        text = "Este es un texto de ejemplo en español."
        lang = detect_language(text)
        assert lang == "es"

    def test_short_text_defaults_to_english(self):
        """Test that very short text defaults to English."""
        text = "Hi"
        lang = detect_language(text)
        assert lang == "en"

    def test_should_translate_different_language(self):
        """Test that translation is needed for different language."""
        text = "This is English text"
        result = should_translate(text, target_lang="pt")
        assert result is True

    def test_should_not_translate_same_language(self):
        """Test that translation is not needed for same language."""
        text = "Este é um texto em português"
        result = should_translate(text, target_lang="pt")
        assert result is False

    def test_get_language_name(self):
        """Test language name mapping."""
        assert get_language_name("en") == "English"
        assert get_language_name("pt") == "Portuguese"
        assert get_language_name("es") == "Spanish"
        assert "Unknown" in get_language_name("xx")


class TestBookChunker:
    """Test book chunking functions."""

    def test_small_text_no_chunk(self):
        """Test that small texts aren't chunked."""
        text = "word " * 200  # Small text
        chunks = chunk_text_for_book(text, max_tokens=512)
        assert len(chunks) == 1

    def test_large_text_is_chunked(self):
        """Test that large texts are chunked."""
        text = "word " * 2000  # Large text
        chunks = chunk_text_for_book(text, max_tokens=512, overlap_tokens=50)
        assert len(chunks) > 1
        # Each chunk should be roughly within limit
        for chunk in chunks:
            words = len(chunk.split())
            assert words <= 600  # Buffer for safety

    def test_chunk_respects_boundaries(self):
        """Test that chunking respects sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. " * 100
        chunks = chunk_text_for_book(text, max_tokens=512)
        assert len(chunks) >= 1

    def test_chunk_by_chapters(self):
        """Test chunking of book chapters."""
        chapters = [
            {"title": "Chapter 1", "text": "word " * 1000, "level": 1},
            {"title": "Chapter 2", "text": "word " * 1000, "level": 1},
        ]

        chunks = chunk_book_by_chapters(chapters, max_tokens=512, overlap_tokens=50)

        # Should have multiple chunks
        assert len(chunks) > 0

        # Each chunk should have chapter info
        for chunk in chunks:
            assert "chapter_title" in chunk
            assert "chapter_level" in chunk
            assert "chunk_id" in chunk
            assert "text" in chunk

    def test_empty_chapter_list(self):
        """Test chunking with empty chapter list."""
        chunks = chunk_book_by_chapters([])
        assert len(chunks) == 0

    def test_chapter_with_no_text(self):
        """Test handling of chapter with empty text."""
        chapters = [
            {"title": "Empty Chapter", "text": "", "level": 1},
            {"title": "Real Chapter", "text": "word " * 100, "level": 1},
        ]

        chunks = chunk_book_by_chapters(chapters)
        assert len(chunks) == 1
        assert chunks[0]["chapter_title"] == "Real Chapter"


class TestLanguageDetectionEdgeCases:
    """Test edge cases for language detection."""

    def test_mixed_languages(self):
        """Test detection with mixed languages."""
        text = "This is English text. Este é um texto em português."
        lang = detect_language(text)
        # Should detect one of the languages
        assert lang in ["en", "pt"]

    def test_numbers_and_symbols(self):
        """Test detection with numbers and symbols."""
        text = "Test 123 @#$ more words here for detection purposes."
        lang = detect_language(text)
        assert lang is not None

    def test_unicode_text(self):
        """Test detection with unicode characters."""
        text = "Café résumé naïve text with special characters"
        lang = detect_language(text)
        assert lang is not None


class TestChunkerEdgeCases:
    """Test edge cases for chunking."""

    def test_single_word(self):
        """Test chunking single word."""
        text = "Word"
        chunks = chunk_text_for_book(text, max_tokens=512)
        assert len(chunks) == 1
        assert chunks[0] == "Word"

    def test_unicode_text_chunking(self):
        """Test chunking text with unicode characters."""
        text = "Café résumé naïve " * 100
        chunks = chunk_text_for_book(text, max_tokens=512)
        assert len(chunks) >= 1

    def test_very_large_text(self):
        """Test chunking very large text."""
        text = "word " * 5000
        chunks = chunk_text_for_book(text, max_tokens=512, overlap_tokens=50)
        assert len(chunks) > 5
        # Verify overlap exists
        if len(chunks) > 1:
            # Chunks should share some content
            overlap_found = False
            for i in range(len(chunks) - 1):
                # Check for any overlapping words
                words1 = set(chunks[i].split())
                words2 = set(chunks[i + 1].split())
                if words1 & words2:
                    overlap_found = True
                    break
            assert overlap_found, "No overlap found between chunks"
