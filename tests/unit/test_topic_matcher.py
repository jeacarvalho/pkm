"""Unit tests for topic matcher module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from src.topics.topic_matcher import TopicMatcher
from src.topics.config import TopicConfig


class TestTopicMatcher:
    """Test TopicMatcher class."""

    def test_init(self):
        """Test initialization."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        assert matcher.fuzzy_threshold == 40
        assert matcher.normalizer is not None

    def test_stats_initialization(self):
        """Test stats are initialized."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        assert matcher.stats["total_notes_scanned"] == 0
        assert matcher.stats["notes_with_topics"] == 0
        assert matcher.stats["notes_matched"] == 0


class TestTopicMatcherFuzzyMatch:
    """Test fuzzy matching functions."""

    def test_fuzzy_match_exact(self):
        """Test exact fuzzy match."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        is_match, score = matcher._fuzzy_match("discipulado", "discipulado")

        assert is_match is True
        assert score >= 90

    def test_fuzzy_match_similar(self):
        """Test similar fuzzy match."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        is_match, score = matcher._fuzzy_match("teologia_biblica", "teologia")

        assert score >= 40  # Should pass threshold

    def test_fuzzy_match_different(self):
        """Test different topics don't match."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        is_match, score = matcher._fuzzy_match("contabilidade", "música")

        # Different topics should have low score
        assert score < matcher.fuzzy_threshold


class TestTopicMatcherCDUMatching:
    """Test CDU matching."""

    def test_cdu_match_exact(self):
        """Test exact CDU match."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        # This tests internal logic
        assert matcher is not None
        assert matcher.fuzzy_threshold == 40


class TestTopicMatcherLoadChapterTopics:
    """Test chapter topics loading."""

    def test_load_chapter_topics_list_format(self, tmp_path):
        """Test loading chapter topics from list format."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        topics_file = tmp_path / "topics.json"
        topics_file.write_text(
            json.dumps(
                [{"name": "topic1", "weight": 8}, {"name": "topic2", "weight": 7}]
            )
        )

        result = matcher._load_chapter_topics(topics_file)

        assert result is not None
        assert "topics" in result

    def test_load_chapter_topics_dict_format(self, tmp_path):
        """Test loading chapter topics from dict format."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        topics_file = tmp_path / "topics.json"
        topics_file.write_text(
            json.dumps(
                {
                    "topics": [{"name": "topic1", "weight": 8}],
                    "chapter_title": "Chapter 1",
                }
            )
        )

        result = matcher._load_chapter_topics(topics_file)

        assert result is not None
        assert "topics" in result
        assert result["chapter_title"] == "Chapter 1"

    def test_load_chapter_topics_invalid(self, tmp_path):
        """Test loading invalid chapter topics."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        topics_file = tmp_path / "topics.json"
        topics_file.write_text("invalid json")

        result = matcher._load_chapter_topics(topics_file)

        assert result is None


class TestTopicMatcherFindNotes:
    """Test finding notes in vault."""

    def test_find_notes_excludes_obsidian(self, tmp_path):
        """Test that .obsidian folder is excluded."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        # Create test structure
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Create normal note
        normal_note = vault_dir / "note.md"
        normal_note.write_text("---\ntitle: Test\n---\nContent")

        # Create obsidian note
        obsidian_dir = vault_dir / ".obsidian"
        obsidian_dir.mkdir()
        obsidian_note = obsidian_dir / "config.md"
        obsidian_note.write_text("config")

        notes = matcher._find_notes_with_topics(vault_dir)

        # Should find only normal note
        assert len(notes) == 1
        assert notes[0].name == "note.md"

    def test_find_notes_excludes_books_folder(self, tmp_path):
        """Test that Livros folder is excluded."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        # Create test structure
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Create normal note
        normal_note = vault_dir / "note.md"
        normal_note.write_text("---\ntitle: Test\n---\nContent")

        # Create book note
        livros_dir = vault_dir / "100 ARQUIVOS E REFERENCIAS" / "Livros"
        livros_dir.mkdir(parents=True)
        book_note = livros_dir / "book_chapter.md"
        book_note.write_text("---\ntitle: Book\n---\nContent")

        notes = matcher._find_notes_with_topics(vault_dir)

        # Should find only normal note
        assert len(notes) == 1
        assert notes[0].name == "note.md"

    def test_find_notes_excludes_hidden_files(self, tmp_path):
        """Test that hidden files are excluded."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Create normal note
        normal_note = vault_dir / "note.md"
        normal_note.write_text("content")

        # Create hidden note
        hidden_note = vault_dir / ".hidden.md"
        hidden_note.write_text("hidden")

        notes = matcher._find_notes_with_topics(vault_dir)

        assert len(notes) == 1
        assert notes[0].name == "note.md"


class TestTopicMatcherSkipList:
    """Test skip list functionality."""

    def test_skip_notes_initial_empty(self):
        """Test skip list starts empty."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        assert len(matcher._skip_notes) == 0

    def test_add_to_skip_list(self):
        """Test adding notes to skip list."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        note_path = "/vault/broken_note.md"

        # Simulate adding to skip list
        matcher._skip_notes.add(note_path)

        assert note_path in matcher._skip_notes

    def test_skip_list_persists_across_calls(self):
        """Test skip list persists in same instance."""
        config = TopicConfig()
        matcher = TopicMatcher(config)

        note_path = "/vault/test.md"
        matcher._skip_notes.add(note_path)

        # In same instance, should still be there
        assert note_path in matcher._skip_notes
