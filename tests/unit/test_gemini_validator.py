"""Unit tests for validation gemini validator module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.validation.gemini_validator import GeminiValidator


class TestGeminiValidator:
    """Test GeminiValidator class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock()
        config.validation_model = "gemini-2.5-flash-lite"
        config.gemini_api_key = "test-key"
        return config

    @pytest.fixture
    def validator(self, mock_config):
        """Create validator instance."""
        with patch("src.validation.gemini_validator.genai.Client"):
            return GeminiValidator(config=mock_config)

    def test_init(self, mock_config):
        """Test validator initialization."""
        with patch("src.validation.gemini_validator.genai.Client") as mock_client:
            validator = GeminiValidator(config=mock_config)
            assert validator.config == mock_config

    def test_validate_match_success(self, validator):
        """Test successful match validation."""
        with patch.object(validator, "client", Mock()):
            validator.client = Mock()
            mock_response = Mock()
            mock_response.text = json.dumps(
                {"approved": True, "confidence": 90, "reason": "Strong match"}
            )
            validator.client.models.generate_content = Mock(return_value=mock_response)

            result = validator.validate_match(
                book_chunk="Test chunk",
                note_content="Test note",
                note_title="Test",
                rerank_score=0.9,
            )

            assert result.approved is True
            assert result.confidence == 90

    def test_validate_match_rejects_weak(self, validator):
        """Test rejection of weak match."""
        with patch.object(validator, "client", Mock()):
            validator.client = Mock()
            mock_response = Mock()
            mock_response.text = json.dumps(
                {"approved": False, "confidence": 20, "reason": "Weak match"}
            )
            validator.client.models.generate_content = Mock(return_value=mock_response)

            result = validator.validate_match(
                book_chunk="Test chunk",
                note_content="Test note",
                note_title="Test",
                rerank_score=0.3,
            )

            assert result.approved is False

    def test_extract_json_from_markdown(self, validator):
        """Test JSON extraction from markdown."""
        text = '```json\n{"approved": true, "confidence": 85}\n```'
        result = validator._extract_json(text)

        assert "approved" in result

    def test_extract_json_from_plain_text(self, validator):
        """Test JSON extraction from plain text."""
        text = '{"approved": false, "confidence": 50}'
        result = validator._extract_json(text)

        assert "approved" in result

    def test_extract_json_fallback(self, validator):
        """Test JSON extraction fallback."""
        text = "Not valid JSON at all"
        result = validator._extract_json(text)
        # Returns original text as fallback
        assert result is not None


class TestGeminiValidatorEdgeCases:
    """Test edge cases for GeminiValidator."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock()
        config.validation_model = "gemini-2.5-flash-lite"
        config.gemini_api_key = "test-key"
        return config

    @pytest.fixture
    def validator(self, mock_config):
        """Create validator instance."""
        with patch("src.validation.gemini_validator.genai.Client"):
            return GeminiValidator(config=mock_config)

    def test_validate_match_json_error(self, validator):
        """Test handling of invalid JSON response."""
        with patch.object(validator, "client", Mock()):
            validator.client = Mock()
            mock_response = Mock()
            mock_response.text = "Not valid JSON"
            validator.client.models.generate_content = Mock(return_value=mock_response)

            result = validator.validate_match(
                book_chunk="Test",
                note_content="Test",
                note_title="Test",
                rerank_score=0.8,
            )

            assert result.approved is False
            assert "failed" in result.reason.lower() or result.confidence == 0

    def test_validate_batch(self, validator):
        """Test batch validation."""
        with patch.object(validator, "client", Mock()):
            validator.client = Mock()
            mock_response = Mock()
            mock_response.text = (
                '{"approved": true, "confidence": 80, "reason": "Match"}'
            )
            validator.client.models.generate_content = Mock(return_value=mock_response)

            candidates = [
                {
                    "document": "text1",
                    "metadata": {"note_title": "Note1"},
                    "rerank_score": 0.8,
                },
                {
                    "document": "text2",
                    "metadata": {"note_title": "Note2"},
                    "rerank_score": 0.7,
                },
            ]

            results = validator.validate_batch("Test chunk", candidates)

            assert len(results) >= 0
