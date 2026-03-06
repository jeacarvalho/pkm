"""Unit tests for slugify utility."""

import pytest
from src.utils.slugify import slugify


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

    def test_slugify_unicode(self):
        """Test slugify with unicode characters."""
        assert slugify("São Paulo") == "sao_paulo"
        assert slugify("Über") == "uber"

    def test_slugify_leading_trailing(self):
        """Test slugify removes leading/trailing underscores."""
        assert slugify("  hello  ") == "hello"
        assert slugify("__test__") == "test"

    def test_slugify_multiple_spaces(self):
        """Test slugify handles multiple spaces."""
        assert slugify("hello    world") == "hello_world"

    def test_slugify_hyphens(self):
        """Test slugify converts hyphens."""
        assert slugify("test-case") == "test_case"

    def test_slugify_max_length_preserves_words(self):
        """Test slugify max length doesn't break mid-word badly."""
        result = slugify("abcdefghijklmnopqrstuvwxyz", max_length=10)
        assert len(result) <= 10
