"""Unit tests for topics config module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import os

from src.topics.config import TopicConfig


class TestTopicConfig:
    """Test TopicConfig class."""

    def test_default_values(self, tmp_path):
        """Test default configuration values."""
        with patch.object(Path, "mkdir", return_value=None):
            config = TopicConfig()

        assert config.gemini_model == "gemini-2.5-flash-lite"
        assert config.topics_per_note == 10
        assert config.weight_min == 5
        assert config.weight_max == 10
        assert config.batch_size == 1
        assert config.max_note_length == 5000
        assert config.retry_attempts == 3
        assert config.retry_delay == 2.0
        assert config.dry_run is False
        assert config.limit == 0  # Default is 0, not None

    def test_custom_values(self, tmp_path):
        """Test custom configuration values."""
        with patch.object(Path, "mkdir", return_value=None):
            config = TopicConfig(
                gemini_model="gemini-2.0-flash",
                gemini_api_key="test-key",
                topics_per_note=5,
                weight_min=3,
                weight_max=8,
                batch_size=2,
                max_note_length=3000,
                retry_attempts=5,
                retry_delay=1.0,
                dry_run=True,
                limit=100,
            )

        assert config.gemini_model == "gemini-2.0-flash"
        assert config.gemini_api_key == "test-key"
        assert config.topics_per_note == 5
        assert config.weight_min == 3
        assert config.weight_max == 8
        assert config.batch_size == 2
        assert config.max_note_length == 3000
        assert config.retry_attempts == 5
        assert config.retry_delay == 1.0
        assert config.dry_run is True
        assert config.limit == 100

    def test_log_dir_default(self, tmp_path):
        """Test default log directory."""
        with patch.object(Path, "mkdir", return_value=None):
            config = TopicConfig()

        # Should default to data/logs/topics
        assert "topics" in str(config.log_dir)

    def test_log_dir_custom(self, tmp_path):
        """Test custom log directory."""
        custom_dir = tmp_path / "custom_logs"
        with patch.object(Path, "mkdir", return_value=None):
            config = TopicConfig(log_dir=custom_dir)

        assert config.log_dir == custom_dir
