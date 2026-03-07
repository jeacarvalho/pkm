"""Failure tracking system for topic classification.

Tracks note processing failures to implement skip logic and prevent
wasting API calls on consistently problematic notes.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from src.topics.constants import (
    FAILURE_TRACKER_FILE,
    MAX_FAILURE_COUNT,
    SKIP_WINDOW_DAYS,
)

logger = logging.getLogger(__name__)


class FailureTracker:
    """Tracks processing failures with skip logic.

    Implements a failure tracking mechanism that skips notes which have
    failed multiple times within a specified time window to prevent
    wasting API calls on problematic notes.

    Attributes:
        tracker_path: Path to the JSON file storing failure data
        failures: Dictionary mapping note paths to failure metadata
    """

    def __init__(self, tracker_path: Optional[Path] = None):
        """Initialize the failure tracker.

        Args:
            tracker_path: Path to the JSON file for persistence.
                         Defaults to ~/.pkm_failure_tracker.json
        """
        self.tracker_path = tracker_path or Path.home() / FAILURE_TRACKER_FILE
        self.failures: Dict[str, Dict] = self._load()

    def _load(self) -> Dict[str, Dict]:
        """Load failure data from disk.

        Returns:
            Dictionary mapping note paths to failure metadata
        """
        try:
            if self.tracker_path.exists():
                with open(self.tracker_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load failure tracker: {e}")
        return {}

    def _save(self) -> None:
        """Persist failure data to disk."""
        try:
            with open(self.tracker_path, "w", encoding="utf-8") as f:
                json.dump(self.failures, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save failure tracker: {e}")

    def should_skip(self, note_path: Path) -> bool:
        """Check if a note should be skipped due to repeated failures.

        A note is skipped if it has failed MAX_FAILURE_COUNT or more times
        within the last SKIP_WINDOW_DAYS days.

        Args:
            note_path: Path to the note file

        Returns:
            True if the note should be skipped, False otherwise
        """
        note_str = str(note_path)

        if note_str not in self.failures:
            return False

        failure_data = self.failures[note_str]
        failure_count = failure_data.get("count", 0)

        if failure_count < MAX_FAILURE_COUNT:
            return False

        last_failure_str = failure_data.get("last_failure")
        if not last_failure_str:
            return False

        try:
            last_failure = datetime.fromisoformat(last_failure_str)
            days_since = (datetime.now(timezone.utc) - last_failure).days

            if days_since < SKIP_WINDOW_DAYS:
                logger.info(
                    f"⏭️ Skipping {note_path.name} - "
                    f"failed {failure_count} times (last: {days_since} days ago)"
                )
                return True
        except Exception:
            # If date parsing fails, don't skip (fail open)
            pass

        return False

    def record_failure(self, note_path: Path) -> None:
        """Record a processing failure for a note.

        Args:
            note_path: Path to the note that failed processing
        """
        note_str = str(note_path)

        if note_str not in self.failures:
            self.failures[note_str] = {"count": 0, "last_failure": None}

        self.failures[note_str]["count"] += 1
        self.failures[note_str]["last_failure"] = datetime.now(timezone.utc).isoformat()

        self._save()
        logger.debug(f"Recorded failure for {note_path.name}")

    def record_success(self, note_path: Path) -> None:
        """Clear failure history for a note after successful processing.

        Args:
            note_path: Path to the note that was successfully processed
        """
        note_str = str(note_path)

        if note_str in self.failures:
            del self.failures[note_str]
            self._save()
            logger.debug(f"Cleared failure history for {note_path.name}")

    def get_failure_count(self, note_path: Path) -> int:
        """Get the current failure count for a note.

        Args:
            note_path: Path to the note

        Returns:
            Number of recorded failures (0 if not in tracker)
        """
        note_str = str(note_path)
        return self.failures.get(note_str, {}).get("count", 0)

    def get_stats(self) -> Dict:
        """Get statistics about current failures.

        Returns:
            Dictionary with total tracked notes and high-failure notes
        """
        total = len(self.failures)
        high_failure = sum(
            1 for f in self.failures.values() if f.get("count", 0) >= MAX_FAILURE_COUNT
        )

        return {
            "total_tracked": total,
            "high_failure_notes": high_failure,
            "max_failures": MAX_FAILURE_COUNT,
            "skip_window_days": SKIP_WINDOW_DAYS,
        }

    def reset(self, note_path: Optional[Path] = None) -> None:
        """Reset failure tracking.

        Args:
            note_path: If provided, reset only this note. Otherwise reset all.
        """
        if note_path:
            note_str = str(note_path)
            if note_str in self.failures:
                del self.failures[note_str]
                logger.info(f"Reset failure tracking for {note_path.name}")
        else:
            self.failures.clear()
            logger.info("Reset all failure tracking")

        self._save()
