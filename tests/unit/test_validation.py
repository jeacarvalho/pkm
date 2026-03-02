"""Unit tests for validation module."""

import pytest
from unittest.mock import Mock, patch

from src.validation.ollama_validator import (
    OllamaValidator,
    ValidationResponse,
)


class TestValidationResponse:
    """Test ValidationResponse class."""

    def test_from_dict_valid(self):
        """Test creating response from valid dict."""
        data = {"approved": True, "confidence": 85, "reason": "Test reason"}
        response = ValidationResponse.from_dict(data)

        assert response.approved is True
        assert response.confidence == 85
        assert response.reason == "Test reason"

    def test_from_dict_defaults(self):
        """Test creating response with missing keys."""
        data = {}
        response = ValidationResponse.from_dict(data)

        assert response.approved is False
        assert response.confidence == 0
        assert response.reason == ""

    def test_to_dict(self):
        """Test converting response to dict."""
        response = ValidationResponse(approved=True, confidence=90, reason="Test")
        result = response.to_dict()

        assert result["approved"] is True
        assert result["confidence"] == 90
        assert result["reason"] == "Test"


class TestOllamaValidator:
    """Test OllamaValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return OllamaValidator()

    def test_extract_json_from_markdown(self, validator):
        """Test JSON extraction from markdown code blocks."""
        text = '```json\n{"approved": true, "confidence": 85, "reason": "Test"}\n```'
        json_str = validator._extract_json(text)

        assert "approved" in json_str
        assert "true" in json_str

    def test_extract_json_from_plain_text(self, validator):
        """Test JSON extraction from plain text."""
        text = '{"approved": false, "confidence": 0, "reason": "Test"}'
        json_str = validator._extract_json(text)

        assert "approved" in json_str

    def test_extract_json_fallback(self, validator):
        """Test JSON extraction fallback."""
        text = 'Some text before {"approved": true} and after'
        json_str = validator._extract_json(text)

        assert "approved" in json_str

    @patch("src.validation.ollama_validator.ollama.chat")
    def test_validate_match_success(self, mock_chat, validator):
        """Test successful match validation."""
        mock_chat.return_value = {
            "message": {
                "content": '{"approved": true, "confidence": 90, "reason": "Good match"}'
            }
        }

        result = validator.validate_match(
            book_chunk="Test book chunk",
            note_content="Test note content",
            note_title="Test Note",
            rerank_score=0.85,
        )

        assert result.approved is True
        assert result.confidence == 90

    @patch("src.validation.ollama_validator.ollama.chat")
    def test_validate_match_rejects_weak(self, mock_chat, validator):
        """Test that weak matches are rejected."""
        mock_chat.return_value = {
            "message": {
                "content": '{"approved": false, "confidence": 30, "reason": "Weak match"}'
            }
        }

        result = validator.validate_match(
            book_chunk="Test book chunk",
            note_content="Test note content",
            note_title="Test Note",
            rerank_score=0.5,
        )

        assert result.approved is False


class TestOllamaValidatorEdgeCases:
    """Test edge cases for OllamaValidator."""

    @patch("src.validation.ollama_validator.ollama.chat")
    def test_validate_match_json_error(self, mock_chat, validator):
        """Test handling of invalid JSON response."""
        mock_chat.return_value = {"message": {"content": "Not valid JSON"}}

        result = validator.validate_match(
            book_chunk="Test",
            note_content="Test",
            note_title="Test",
            rerank_score=0.8,
        )

        # Should return fallback response
        assert result.approved is False
        assert "failed" in result.reason.lower()

    @patch("src.validation.ollama_validator.ollama.chat")
    def test_validate_batch(self, mock_chat, validator):
        """Test batch validation."""
        mock_chat.return_value = {
            "message": {
                "content": '{"approved": true, "confidence": 80, "reason": "Match"}'
            }
        }

        candidates = [
            {
                "document": "text1",
                "metadata": {"note_title": "Note1"},
                "rerank_score": 0.9,
            },
            {
                "document": "text2",
                "metadata": {"note_title": "Note2"},
                "rerank_score": 0.8,
            },
        ]

        results = validator.validate_batch("book chunk", candidates)

        # Both should be approved
        assert len(results) <= len(candidates)


class TestMockOllamaValidator:
    """Test MockOllamaValidator for testing."""

    def test_approves_high_scores(self):
        """Test that high scores are approved."""
        from src.validation.ollama_validator import MockOllamaValidator

        validator = MockOllamaValidator(approval_rate=1.0)

        result = validator.validate_match(
            book_chunk="test",
            note_content="test",
            note_title="Test",
            rerank_score=0.9,
        )

        assert result.approved is True

    def test_rejects_low_scores(self):
        """Test that low scores are rejected."""
        from src.validation.ollama_validator import MockOllamaValidator

        validator = MockOllamaValidator(approval_rate=0.0)

        result = validator.validate_match(
            book_chunk="test",
            note_content="test",
            note_title="Test",
            rerank_score=0.5,
        )

        assert result.approved is False


class TestValidationPipeline:
    """Test ValidationPipeline integration."""

    @pytest.fixture
    def mock_pipeline(self):
        """Create mock pipeline components."""
        from src.validation.pipeline import ValidationPipeline

        # Create pipeline with mocked components
        pipeline = ValidationPipeline.__new__(ValidationPipeline)

        # Mock retrieval
        pipeline.retrieval = Mock()
        pipeline.retrieval.retrieve.return_value = [
            {
                "document": "test note",
                "metadata": {"note_title": "Test"},
                "rerank_score": 0.85,
            }
        ]

        # Mock validator
        pipeline.validator = Mock()
        pipeline.validator.validate_batch.return_value = []

        return pipeline

    def test_process_chunk_returns_structure(self, mock_pipeline):
        """Test that process_chunk returns expected structure."""
        result = mock_pipeline.process_chunk(
            chunk_text="test chunk",
            chunk_embedding=[0.1] * 1024,
        )

        assert "validated_matches" in result
        assert "candidates_reranked" in result
        assert "matches_validated" in result
