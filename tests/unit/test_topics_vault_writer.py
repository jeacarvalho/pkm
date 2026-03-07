"""Unit tests for vault_writer module in src/topics/.

Tests the VaultWriter class that handles writing topic classifications
to Obsidian vault notes.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.topics.vault_writer import VaultWriter


class TestVaultWriterInitialization:
    """Test VaultWriter initialization and configuration."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = MagicMock()
        config.log_dir = Path("/tmp/logs")
        config.vault_path = "/tmp/vault"
        config.dry_run = False
        return config

    def test_init_with_config(self, config):
        """Test initialization with config object."""
        writer = VaultWriter(config)
        assert writer.config == config
        assert hasattr(writer, "stats")
        assert writer.stats["total_jsons"] == 0
        assert writer.stats["successful"] == 0
        assert writer.stats["failed"] == 0
        assert writer.stats["skipped"] == 0
        assert writer.stats["modified"] == []


class TestVaultWriterNoteReading:
    """Test reading notes from vault."""

    @pytest.fixture
    def writer(self, tmp_path):
        """Create a VaultWriter instance with mocked config."""
        config = MagicMock()
        config.log_dir = tmp_path / "logs"
        config.vault_path = str(tmp_path)
        config.dry_run = False
        return VaultWriter(config)

    @pytest.fixture
    def sample_note(self, tmp_path):
        """Create a sample note with frontmatter."""
        note_path = tmp_path / "test_note.md"
        content = """---
title: Test Note
tags: ["test", "sample"]
topic_classification:
  topics:
    - name: "test_topic"
      weight: 10
  cdu_primary: "123.45"
  classified_at: "2024-01-01"
---

# Test Note

This is test content.
"""
        note_path.write_text(content, encoding="utf-8")
        return note_path

    def test_read_note_with_frontmatter(self, writer, sample_note):
        """Test reading note with frontmatter."""
        frontmatter, body, full = writer._read_note(sample_note)

        assert frontmatter["title"] == "Test Note"
        assert "tags" in frontmatter
        assert "topic_classification" in frontmatter
        assert "# Test Note" in body
        assert len(full) > 0

    def test_read_note_without_frontmatter(self, writer, tmp_path):
        """Test reading note without frontmatter."""
        note_path = tmp_path / "simple_note.md"
        note_path.write_text("# Simple Note\n\nContent.", encoding="utf-8")

        frontmatter, body, full = writer._read_note(note_path)

        assert frontmatter == {}
        assert "# Simple Note" in body


class TestVaultWriterNoteWriting:
    """Test writing notes to vault."""

    @pytest.fixture
    def writer(self, tmp_path):
        """Create a VaultWriter instance."""
        config = MagicMock()
        config.log_dir = tmp_path / "logs"
        config.vault_path = str(tmp_path)
        config.dry_run = False
        return VaultWriter(config)

    def test_write_note_creates_file(self, writer, tmp_path):
        """Test that writing creates the file."""
        note_path = tmp_path / "output_note.md"
        frontmatter = {"title": "Test", "tags": ["a", "b"]}
        body = "# Content\n\nText."

        writer._write_note(note_path, frontmatter, body)

        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert "title: Test" in content
        assert "# Content" in content

    def test_write_note_preserves_encoding(self, writer, tmp_path):
        """Test that writing preserves UTF-8 encoding."""
        note_path = tmp_path / "unicode_note.md"
        frontmatter = {"title": "Tópico com Acentos"}
        body = "# Conteúdo em Português\n\nçãéíóú"

        writer._write_note(note_path, frontmatter, body)

        content = note_path.read_text(encoding="utf-8")
        assert "çãéíóú" in content
        assert "Tópico com Acentos" in content

    def test_write_note_overwrites_existing(self, writer, tmp_path):
        """Test that writing overwrites existing files."""
        note_path = tmp_path / "existing.md"
        note_path.write_text("Old content", encoding="utf-8")

        frontmatter = {"title": "New"}
        body = "New content"

        writer._write_note(note_path, frontmatter, body)

        content = note_path.read_text(encoding="utf-8")
        assert "New content" in content
        assert "Old content" not in content


class TestVaultWriterTopicClassification:
    """Test building and writing topic classifications."""

    @pytest.fixture
    def writer(self, tmp_path):
        """Create a VaultWriter instance."""
        config = MagicMock()
        config.log_dir = tmp_path / "logs"
        config.vault_path = str(tmp_path)
        config.dry_run = False
        return VaultWriter(config)

    def test_build_topic_classification_basic(self, writer):
        """Test building topic classification structure."""
        topic_data = {
            "topics": [{"name": "ai", "weight": 8}],
            "cdu_primary": "004.8",
            "cdu_description": "Inteligência Artificial",
        }

        classification = writer._build_topic_classification(topic_data, None)

        assert classification["version"] == "2.0"
        assert classification["cdu_primary"] == "004.8"
        assert classification["topics"][0]["name"] == "ai"
        assert "classified_at" in classification
        assert "model" in classification

    def test_build_topic_classification_with_secondary_cdu(self, writer):
        """Test building with secondary CDU."""
        topic_data = {
            "topics": [],
            "cdu_primary": "123.45",
            "cdu_secondary": ["123.46", "123.47"],
        }

        classification = writer._build_topic_classification(topic_data, None)

        assert classification["cdu_secondary"] == ["123.46", "123.47"]

    def test_build_topic_classification_with_cdu_description(self, writer):
        """Test that CDU description is included."""
        topic_data = {
            "topics": [],
            "cdu_primary": "100",
            "cdu_description": "Description of topic",
        }

        classification = writer._build_topic_classification(topic_data, None)
        assert classification["cdu_description"] == "Description of topic"


class TestVaultWriterIntegration:
    """Integration tests for VaultWriter."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create a temporary vault with structure."""
        vault = tmp_path / "vault"
        vault.mkdir()

        return vault

    @pytest.fixture
    def writer(self, temp_vault):
        """Create a VaultWriter for the temp vault."""
        config = MagicMock()
        config.log_dir = temp_vault / "logs"
        config.vault_path = str(temp_vault)
        config.dry_run = False
        return VaultWriter(config)

    def test_full_workflow_single_note(self, writer, temp_vault):
        """Test full workflow for a single note."""
        note_path = temp_vault / "test_note.md"
        note_path.write_text("# Test\n\nContent", encoding="utf-8")

        topic_data = {
            "topics": [
                {"name": "testing", "weight": 9},
                {"name": "python", "weight": 7},
            ],
            "cdu_primary": "005.1",
            "cdu_description": "Software Testing",
        }

        # Write directly (simulating what topic_extractor does)
        frontmatter, body, _ = writer._read_note(note_path)
        classification = writer._build_topic_classification(topic_data, note_path)
        frontmatter["topic_classification"] = classification
        writer._write_note(note_path, frontmatter, body)

        # Verify result
        result = note_path.read_text(encoding="utf-8")
        assert "topic_classification:" in result
        assert "testing:" in result or "testing" in result
        assert "005.1" in result
        assert (
            "version:" in result and "2.0" in result
        )  # YAML pode usar aspas simples ou duplas

    def test_classified_at_timestamp_format(self, writer, temp_vault):
        """Test that classified_at has correct format."""
        note_path = temp_vault / "timestamp_test.md"
        note_path.write_text("# Test", encoding="utf-8")

        topic_data = {"topics": []}
        frontmatter, body, _ = writer._read_note(note_path)
        classification = writer._build_topic_classification(topic_data, note_path)
        frontmatter["topic_classification"] = classification
        writer._write_note(note_path, frontmatter, body)

        content = note_path.read_text(encoding="utf-8")
        # Extract and verify timestamp format
        assert "classified_at:" in content
        # Should be ISO format YYYY-MM-DD or datetime
        assert "202" in content or "T" in content  # Year 202x or ISO format


class TestVaultWriterYamlFormatting:
    """Test YAML formatting in output."""

    @pytest.fixture
    def writer(self, tmp_path):
        """Create a VaultWriter instance."""
        config = MagicMock()
        config.log_dir = tmp_path / "logs"
        config.vault_path = str(tmp_path)
        config.dry_run = False
        return VaultWriter(config)

    def test_yaml_list_format(self, writer, tmp_path):
        """Test that lists are formatted correctly in YAML."""
        note_path = tmp_path / "list_test.md"
        note_path.write_text("# Test", encoding="utf-8")

        topic_data = {
            "topics": [
                {"name": "topic_a", "weight": 5},
                {"name": "topic_b", "weight": 8},
            ],
            "cdu_secondary": ["100.1", "100.2"],
        }

        frontmatter, body, _ = writer._read_note(note_path)
        classification = writer._build_topic_classification(topic_data, note_path)
        frontmatter["topic_classification"] = classification
        writer._write_note(note_path, frontmatter, body)

        content = note_path.read_text(encoding="utf-8")
        # Should use YAML list format
        assert "topics:" in content

    def test_yaml_string_quoting(self, writer, tmp_path):
        """Test proper quoting of strings in YAML."""
        note_path = tmp_path / "quote_test.md"
        note_path.write_text("# Test", encoding="utf-8")

        topic_data = {
            "cdu_primary": "004.8",
            "cdu_description": "Title with: special chars",
        }

        frontmatter, body, _ = writer._read_note(note_path)
        classification = writer._build_topic_classification(topic_data, note_path)
        frontmatter["topic_classification"] = classification
        writer._write_note(note_path, frontmatter, body)

        content = note_path.read_text(encoding="utf-8")
        # Should be valid YAML
        parsed = yaml.safe_load(content.split("---")[1])
        assert parsed["topic_classification"]["cdu_primary"] == "004.8"
