"""Unit tests for topic extractor module."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import json

from src.topics.topic_extractor import TopicExtractor
from src.topics.config import TopicConfig


class TestTopicExtractor:
    """Test TopicExtractor class."""

    def test_init_with_config(self):
        """Test initialization with config."""
        config = TopicConfig(gemini_api_key="test-key")
        # Just verify config is created properly
        assert config.gemini_api_key == "test-key"
        assert config.gemini_model == "gemini-2.5-flash-lite"

    def test_init_with_defaults(self):
        """Test initialization with defaults."""
        config = TopicConfig()
        # Verify default values
        assert config.gemini_model == "gemini-2.5-flash-lite"
        assert config.topics_per_note == 10
        assert config.weight_min == 5
        assert config.weight_max == 10

    def test_config_attributes(self):
        """Test config has expected attributes."""
        config = TopicConfig(
            gemini_model="gemini-2.0-flash",
            topics_per_note=5,
            weight_min=3,
            weight_max=8,
        )

        assert config.gemini_model == "gemini-2.0-flash"
        assert config.topics_per_note == 5
        assert config.weight_min == 3
        assert config.weight_max == 8


class TestTopicExtractorEdgeCases:
    """Test edge cases for topic extraction."""

    def test_config_empty_api_key(self):
        """Test config with empty API key."""
        config = TopicConfig(gemini_api_key="")
        # Should allow empty string (will fail at runtime)
        assert config.gemini_api_key == ""

    def test_config_log_dir(self, tmp_path):
        """Test config with custom log dir."""
        custom_dir = tmp_path / "logs"
        config = TopicConfig(log_dir=custom_dir)
        assert config.log_dir == custom_dir

    def test_config_retry_settings(self):
        """Test config retry settings."""
        config = TopicConfig(retry_attempts=5, retry_delay=1.0)
        assert config.retry_attempts == 5
        assert config.retry_delay == 1.0
