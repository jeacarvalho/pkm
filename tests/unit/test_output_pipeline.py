"""Unit tests for output pipeline module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.output.pipeline import OutputPipeline
from src.output.markdown_generator import MarkdownGenerator


class TestOutputPipeline:
    """Test OutputPipeline class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.output_dir = Path("/tmp/test_output")
        settings.include_translations = True
        settings.include_validation_status = True
        return settings

    @pytest.fixture
    def mock_generator(self):
        """Create mock markdown generator."""
        with patch("src.output.pipeline.MarkdownGenerator"):
            return Mock(spec=MarkdownGenerator)

    def test_init(self, mock_settings):
        """Test pipeline initialization."""
        with patch("src.output.pipeline.MarkdownGenerator"):
            pipeline = OutputPipeline(config=mock_settings)
            assert pipeline.config == mock_settings

    def test_init_default_config(self):
        """Test initialization with default config."""
        with patch("src.output.pipeline.MarkdownGenerator"):
            pipeline = OutputPipeline()
            assert pipeline.config is not None


class TestOutputPipelineEdgeCases:
    """Test edge cases for output pipeline."""

    def test_init_with_none_config(self):
        """Test initialization with None config."""
        with patch("src.output.pipeline.MarkdownGenerator"):
            pipeline = OutputPipeline(config=None)
            assert pipeline.config is not None
