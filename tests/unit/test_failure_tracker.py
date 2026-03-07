"""Unit tests for the FailureTracker class.

Tests the failure tracking mechanism that implements skip logic for notes
that have failed multiple times within a specified time window.
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.topics.failure_tracker import FailureTracker
from src.topics.constants import MAX_FAILURE_COUNT, SKIP_WINDOW_DAYS


class TestFailureTracker:
    """Test suite for FailureTracker class."""

    @pytest.fixture
    def temp_tracker_file(self):
        """Create a temporary file for failure tracking."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def tracker(self, temp_tracker_file):
        """Create a FailureTracker instance with temporary file."""
        return FailureTracker(tracker_path=temp_tracker_file)

    @pytest.fixture
    def sample_note(self, tmp_path):
        """Create a sample note path for testing."""
        note_path = tmp_path / "test_note.md"
        note_path.write_text("# Test Note\n\nThis is a test.")
        return note_path

    def test_initialization(self, temp_tracker_file):
        """Test FailureTracker initialization."""
        tracker = FailureTracker(tracker_path=temp_tracker_file)
        assert tracker.tracker_path == temp_tracker_file
        assert tracker.failures == {}

    def test_should_skip_empty_tracker(self, tracker, sample_note):
        """Test that notes are not skipped when tracker is empty."""
        assert not tracker.should_skip(sample_note)

    def test_should_skip_below_threshold(self, tracker, sample_note):
        """Test that notes with failures below threshold are not skipped."""
        # Record failures below threshold
        for _ in range(MAX_FAILURE_COUNT - 1):
            tracker.record_failure(sample_note)

        assert not tracker.should_skip(sample_note)

    def test_should_skip_at_threshold(self, tracker, sample_note):
        """Test that notes at failure threshold are skipped."""
        # Record failures at threshold
        for _ in range(MAX_FAILURE_COUNT):
            tracker.record_failure(sample_note)

        assert tracker.should_skip(sample_note)

    def test_should_skip_after_threshold(self, tracker, sample_note):
        """Test that notes above failure threshold are skipped."""
        # Record more failures than threshold
        for _ in range(MAX_FAILURE_COUNT + 2):
            tracker.record_failure(sample_note)

        assert tracker.should_skip(sample_note)

    def test_should_skip_after_window_expires(self, tracker, sample_note):
        """Test that notes are not skipped after skip window expires."""
        # Record failures at threshold
        for _ in range(MAX_FAILURE_COUNT):
            tracker.record_failure(sample_note)

        # Manually set the last failure to be outside the window
        old_date = datetime.now(timezone.utc) - timedelta(days=SKIP_WINDOW_DAYS + 1)
        tracker.failures[str(sample_note)]["last_failure"] = old_date.isoformat()
        tracker._save()

        # Reload to verify
        tracker2 = FailureTracker(tracker_path=tracker.tracker_path)
        assert not tracker2.should_skip(sample_note)

    def test_record_failure_increments_count(self, tracker, sample_note):
        """Test that recording failure increments the failure count."""
        tracker.record_failure(sample_note)
        assert tracker.get_failure_count(sample_note) == 1

        tracker.record_failure(sample_note)
        assert tracker.get_failure_count(sample_note) == 2

    def test_record_success_clears_failures(self, tracker, sample_note):
        """Test that recording success clears failure history."""
        # Record some failures
        for _ in range(3):
            tracker.record_failure(sample_note)

        assert tracker.get_failure_count(sample_note) == 3

        # Record success
        tracker.record_success(sample_note)

        assert tracker.get_failure_count(sample_note) == 0
        assert str(sample_note) not in tracker.failures

    def test_persistence(self, temp_tracker_file, sample_note):
        """Test that failures are persisted to disk."""
        # Create tracker and record failure
        tracker1 = FailureTracker(tracker_path=temp_tracker_file)
        tracker1.record_failure(sample_note)

        # Create new tracker instance (simulates restart)
        tracker2 = FailureTracker(tracker_path=temp_tracker_file)

        assert tracker2.get_failure_count(sample_note) == 1

    def test_get_stats_empty(self, tracker):
        """Test getting stats when tracker is empty."""
        stats = tracker.get_stats()

        assert stats["total_tracked"] == 0
        assert stats["high_failure_notes"] == 0
        assert stats["max_failures"] == MAX_FAILURE_COUNT
        assert stats["skip_window_days"] == SKIP_WINDOW_DAYS

    def test_get_stats_with_failures(self, tracker, sample_note, tmp_path):
        """Test getting stats with multiple notes."""
        note2 = tmp_path / "note2.md"
        note2.write_text("# Note 2")

        # Record failures
        tracker.record_failure(sample_note)
        tracker.record_failure(sample_note)
        tracker.record_failure(sample_note)  # At threshold

        tracker.record_failure(note2)

        stats = tracker.get_stats()

        assert stats["total_tracked"] == 2
        assert stats["high_failure_notes"] == 1  # Only sample_note at threshold

    def test_reset_single_note(self, tracker, sample_note, tmp_path):
        """Test resetting a single note."""
        note2 = tmp_path / "note2.md"
        note2.write_text("# Note 2")

        # Record failures for both notes
        tracker.record_failure(sample_note)
        tracker.record_failure(note2)

        # Reset only sample_note
        tracker.reset(sample_note)

        assert tracker.get_failure_count(sample_note) == 0
        assert tracker.get_failure_count(note2) == 1

    def test_reset_all(self, tracker, sample_note, tmp_path):
        """Test resetting all notes."""
        note2 = tmp_path / "note2.md"
        note2.write_text("# Note 2")

        # Record failures
        tracker.record_failure(sample_note)
        tracker.record_failure(note2)

        # Reset all
        tracker.reset()

        assert tracker.get_failure_count(sample_note) == 0
        assert tracker.get_failure_count(note2) == 0
        assert len(tracker.failures) == 0

    def test_invalid_date_format(self, tracker, sample_note):
        """Test handling of invalid date format in tracker."""
        # Record failures
        for _ in range(MAX_FAILURE_COUNT):
            tracker.record_failure(sample_note)

        # Corrupt the date format
        tracker.failures[str(sample_note)]["last_failure"] = "invalid-date"
        tracker._save()

        # Should not crash and should not skip (fail open)
        assert not tracker.should_skip(sample_note)

    def test_concurrent_access_simulation(self, temp_tracker_file, sample_note):
        """Test that concurrent modifications are handled gracefully."""
        tracker1 = FailureTracker(tracker_path=temp_tracker_file)
        tracker2 = FailureTracker(tracker_path=temp_tracker_file)

        # Both record failures
        tracker1.record_failure(sample_note)
        tracker2.record_failure(sample_note)

        # Reload and verify (one of them will win, but no corruption)
        tracker3 = FailureTracker(tracker_path=temp_tracker_file)
        count = tracker3.get_failure_count(sample_note)
        assert count >= 1  # At least one was saved


class TestFailureTrackerIntegration:
    """Integration tests for FailureTracker with real file system."""

    def test_file_format(self, tmp_path):
        """Test that the JSON file has the expected format."""
        tracker_file = tmp_path / "failures.json"
        note_path = tmp_path / "test.md"
        note_path.write_text("test")

        tracker = FailureTracker(tracker_path=tracker_file)
        tracker.record_failure(note_path)

        # Read and verify file format
        with open(tracker_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        note_key = str(note_path)
        assert note_key in data
        assert "count" in data[note_key]
        assert "last_failure" in data[note_key]
        assert data[note_key]["count"] == 1
        assert isinstance(data[note_key]["last_failure"], str)
