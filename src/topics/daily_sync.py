"""Daily Sync System for Topic Classification v2.1.

Runs once per day (at night) to:
1. Detect new notes created today without topic_classification and index them
2. Detect modified notes today WITH topic_classification and reindex them (since content may have changed)
3. Implement incremental processing (don't reprocess notes already classified and not modified)
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import yaml

from src.topics.config import TopicConfig
from src.topics.failure_tracker import FailureTracker
from src.topics.topic_extractor import TopicExtractor
from src.topics.vault_writer import VaultWriter
from src.topics.constants import (
    MIN_NOTE_LENGTH,
    API_RATE_LIMIT_DELAY,
    FRONTMATTER_DELIMITER,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DailySync:
    """Daily sync system for topic classification."""

    def __init__(self, config: TopicConfig):
        self.config = config
        self._setup_logger()

        # Initialize components
        self.extractor = TopicExtractor(config)
        self.writer = VaultWriter(config)
        self.failure_tracker = FailureTracker()

        # Statistics
        self.stats = {
            "date": datetime.now(timezone.utc).isoformat(),
            "total_notes_scanned": 0,
            "new_notes_found": 0,
            "modified_notes_found": 0,
            "notes_to_process": 0,
            "notes_processed": 0,
            "notes_skipped": 0,
            "notes_failed": 0,
            "notes_skipped_due_to_failures": 0,
            "new_notes_processed": [],
            "modified_notes_reindexed": [],
            "notes_failed_list": [],
            "notes_skipped_list": [],
        }

        # Time thresholds (for today) - timezone-aware
        self.today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.today_end = self.today_start + timedelta(days=1)

        # Time thresholds for yesterday
        self.yesterday_start = self.today_start - timedelta(days=1)
        self.yesterday_end = self.today_start

    def _setup_logger(self):
        """Configure logging for daily sync."""
        # Create daily sync log directory
        daily_sync_log_dir = self.config.log_dir / "daily_sync"
        daily_sync_log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file with date
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file = daily_sync_log_dir / f"daily_sync_{today_str}.log"

        # File handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)

        # Add handler to module logger
        logger.addHandler(file_handler)

    def _get_note_metadata(self, note_path: Path) -> Dict:
        """Get metadata for a note file."""
        frontmatter = {}  # Initialize early to ensure it's always defined
        try:
            # Get filesystem timestamps (make them timezone-aware)
            stat = note_path.stat()
            created_time = datetime.fromtimestamp(stat.st_ctime, timezone.utc)
            modified_time = datetime.fromtimestamp(stat.st_mtime, timezone.utc)

            # Read frontmatter
            content = ""
            try:
                with open(note_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter_raw = parts[1]
                        try:
                            frontmatter = yaml.safe_load(frontmatter_raw)
                        except yaml.YAMLError:
                            frontmatter = {}
            except Exception as e:
                logger.debug(f"Error reading frontmatter for {note_path}: {e}")

            # CRITICAL: Ensure frontmatter is always a dict before using 'in' operator
            if frontmatter is None:
                frontmatter = {}
            elif not isinstance(frontmatter, dict):
                logger.debug(
                    f"Frontmatter for {note_path.name} is not a dict (type: {type(frontmatter).__name__}), using empty dict"
                )
                frontmatter = {}

            # Now it's safe to use 'in' operator
            has_tc = "topic_classification" in frontmatter

            return {
                "path": note_path,
                "created_time": created_time,
                "modified_time": modified_time,
                "frontmatter": frontmatter,
                "has_topic_classification": has_tc,
                "last_classification_time": self._get_last_classification_time(
                    frontmatter
                ),
            }
        except Exception as e:
            import traceback

            logger.error(f"Error getting metadata for {note_path}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return {}

    def _get_last_classification_time(self, frontmatter: Dict) -> Optional[datetime]:
        """Get the last classification time from frontmatter."""
        if (
            not frontmatter
            or not isinstance(frontmatter, dict)
            or "topic_classification" not in frontmatter
        ):
            return None

        tc = frontmatter.get("topic_classification", {})
        classified_at = tc.get("classified_at")

        if not classified_at:
            return None

        # If already a datetime object, return it directly
        if isinstance(classified_at, datetime):
            return classified_at

        try:
            # Try to parse ISO format (string)
            if isinstance(classified_at, str):
                if "Z" in classified_at:
                    # UTC timezone
                    return datetime.fromisoformat(classified_at.replace("Z", "+00:00"))
                else:
                    # Local timezone or naive
                    return datetime.fromisoformat(classified_at)
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse classification time: {classified_at}")
            return None

    def _is_note_created_today(self, note_metadata: Dict) -> bool:
        """Check if note was created today."""
        created_time = note_metadata.get("created_time")
        if not created_time:
            return False

        return self.today_start <= created_time < self.today_end

    def _is_note_modified_today(self, note_metadata: Dict) -> bool:
        """Check if note was modified today."""
        modified_time = note_metadata.get("modified_time")
        if not modified_time:
            return False

        return self.today_start <= modified_time < self.today_end

    def _is_note_modified_yesterday(self, note_metadata: Dict) -> bool:
        """Check if note was modified yesterday."""
        modified_time = note_metadata.get("modified_time")
        if not modified_time:
            return False

        return self.yesterday_start <= modified_time < self.yesterday_end

    def _needs_reindexing(self, note_metadata: Dict) -> bool:
        """Check if note needs reindexing (modified after last classification)."""
        if not note_metadata.get("has_topic_classification"):
            return False

        modified_time = note_metadata.get("modified_time")
        last_classification_time = note_metadata.get("last_classification_time")

        if not modified_time or not last_classification_time:
            return False

        # Needs reindexing if modified after last classification
        return modified_time > last_classification_time

    def scan_vault(
        self, vault_dir: Path, production_mode: bool = False
    ) -> Tuple[List[Path], List[Path]]:
        """Scan vault to find notes that need processing.

        Args:
            vault_dir: Path to Obsidian vault
            production_mode: If True, process all unclassified notes and notes modified yesterday.
                           If False, process only today's new notes and today's modified notes.

        Returns:
            Tuple of (new_notes, modified_notes)
            - new_notes: Notes without topic_classification
            - modified_notes: Notes with topic_classification that need reindexing
        """
        new_notes = []
        modified_notes = []

        if production_mode:
            logger.info(f"🔍 Scanning vault in PRODUCTION mode: {vault_dir}")
            logger.info("   - Will process ALL notes without topic_classification")
            logger.info("   - Will reindex notes modified YESTERDAY")
        else:
            logger.info(f"🔍 Scanning vault in NORMAL mode: {vault_dir}")
            logger.info("   - Will process only TODAY's new notes")
            logger.info("   - Will reindex notes modified TODAY")

        # Scan all markdown files
        for md_file in vault_dir.rglob("*.md"):
            if md_file.name.startswith("."):
                continue
            if ".obsidian" in str(md_file):
                continue

            self.stats["total_notes_scanned"] += 1

            # Get metadata
            metadata = self._get_note_metadata(md_file)
            if not metadata:
                continue

            if production_mode:
                # PRODUCTION MODE: Process ALL notes without classification
                if not metadata["has_topic_classification"]:
                    new_notes.append(md_file)
                    self.stats["new_notes_found"] += 1
                    logger.debug(f"📝 Unclassified note found: {md_file.name}")

                # PRODUCTION MODE: Reindex notes modified YESTERDAY
                elif self._is_note_modified_yesterday(
                    metadata
                ) and self._needs_reindexing(metadata):
                    modified_notes.append(md_file)
                    self.stats["modified_notes_found"] += 1
                    logger.debug(
                        f"🔄 Note modified yesterday needs reindexing: {md_file.name}"
                    )
            else:
                # NORMAL MODE: Process only today's new notes
                if (
                    self._is_note_created_today(metadata)
                    and not metadata["has_topic_classification"]
                ):
                    new_notes.append(md_file)
                    self.stats["new_notes_found"] += 1
                    logger.debug(f"📝 New note found: {md_file.name}")

                # NORMAL MODE: Reindex notes modified TODAY
                elif self._is_note_modified_today(metadata) and self._needs_reindexing(
                    metadata
                ):
                    modified_notes.append(md_file)
                    self.stats["modified_notes_found"] += 1
                logger.debug(f"🔄 Modified note needs reindexing: {md_file.name}")

        logger.info(
            f"📊 Scan complete: {self.stats['total_notes_scanned']} notes scanned"
        )
        logger.info(f"📝 New notes found: {len(new_notes)}")
        logger.info(f"🔄 Modified notes needing reindexing: {len(modified_notes)}")

        return new_notes, modified_notes

    def extract_topics_for_notes(self, note_paths: List[Path]) -> Dict[Path, Dict]:
        """Extract topics for a list of notes."""
        results = {}

        if not note_paths:
            return results

        # Apply limit if specified
        if self.config.limit:
            note_paths = note_paths[: self.config.limit]
            logger.info(f"📏 Limiting to {len(note_paths)} notes")

        logger.info(f"🧠 Extracting topics for {len(note_paths)} notes")

        for i, note_path in enumerate(note_paths, 1):
            logger.info(f"[{i}/{len(note_paths)}] Extracting topics: {note_path.name}")

            # Check if note should be skipped due to repeated failures
            if self.failure_tracker.should_skip(note_path):
                logger.warning(
                    f"⏭️ Skipping {note_path.name} - too many previous failures"
                )
                self.stats["notes_skipped"] += 1
                self.stats["notes_skipped_due_to_failures"] += 1
                self.stats["notes_skipped_list"].append(str(note_path))
                continue

            try:
                # Extract topics using the existing TopicExtractor
                result, error = self.extractor.process_note(note_path)

                if result and not error:
                    results[note_path] = result
                    self.failure_tracker.record_success(note_path)
                    logger.info(f"✅ Topics extracted for {note_path.name}")
                else:
                    logger.warning(
                        f"⚠️ Failed to extract topics for {note_path.name}: {error}"
                    )
                    self.failure_tracker.record_failure(note_path)
                    self.stats["notes_failed"] += 1
                    self.stats["notes_failed_list"].append(str(note_path))
            except Exception as e:
                logger.error(f"❌ Error extracting topics for {note_path.name}: {e}")
                self.failure_tracker.record_failure(note_path)
                self.stats["notes_failed"] += 1
                self.stats["notes_failed_list"].append(str(note_path))

            # Add delay between API calls to avoid rate limiting
            # Only add delay if not the last note
            if i < len(note_paths):
                logger.debug(
                    f"⏳ Waiting {API_RATE_LIMIT_DELAY}s before next API call..."
                )
                time.sleep(API_RATE_LIMIT_DELAY)

        return results

    def _write_topics_directly(self, note_path: Path, topic_data: Dict) -> bool:
        """Write topics directly to note without needing JSON files.

        This is a simplified version of VaultWriter.write_properties that works
        with in-memory topic data instead of loading from JSON files.
        """
        try:
            # Read note
            frontmatter, content_body, _ = self.writer._read_note(note_path)

            # Build topic classification
            topic_classification = self.writer._build_topic_classification(
                topic_data, note_path
            )

            # Update or add frontmatter
            frontmatter["topic_classification"] = topic_classification

            # Dry-run: only log, don't write
            if self.config.dry_run:
                logger.info(f"📝 [DRY-RUN] Would update: {note_path.name}")
                logger.info(f"   Topics: {len(topic_classification['topics'])}")
                logger.info(f"   CDU: {topic_classification['cdu_primary']}")
                return True

            # Write updated note
            self.writer._write_note(note_path, frontmatter, content_body)
            logger.info(
                f"✅ Updated: {note_path.name} - {len(topic_classification['topics'])} topics"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error writing topics for {note_path.name}: {e}")
            return False

    def write_topics_to_notes(self, note_results: Dict[Path, Dict]) -> List[Path]:
        """Write extracted topics to notes."""
        modified_notes = []

        if not note_results:
            return modified_notes

        logger.info(f"📝 Writing topics to {len(note_results)} notes")

        for note_path, topic_data in note_results.items():
            try:
                # Write topics directly
                success = self._write_topics_directly(note_path, topic_data)

                if success:
                    modified_notes.append(note_path)
                    self.stats["notes_processed"] += 1

                    # Track in appropriate list
                    note_name = note_path.name
                    if note_name in [
                        p.name for p in self.stats.get("new_notes_processed", [])
                    ]:
                        self.stats["new_notes_processed"].append(str(note_path))
                    else:
                        self.stats["modified_notes_reindexed"].append(str(note_path))
                else:
                    logger.warning(f"⚠️ Failed to write topics for {note_path.name}")
                    self.stats["notes_failed"] += 1
                    self.stats["notes_failed_list"].append(str(note_path))
            except Exception as e:
                logger.error(f"❌ Error writing topics for {note_path.name}: {e}")
                self.stats["notes_failed"] += 1
                self.stats["notes_failed_list"].append(str(note_path))

        return modified_notes

    def process_notes(
        self,
        vault_dir: Path,
        force_all: bool = False,
        only_missing: bool = False,
        production_mode: bool = False,
    ) -> List[Path]:
        """Main processing method for daily sync.

        Args:
            vault_dir: Path to Obsidian vault
            force_all: If True, process all notes without topic_classification (not just today's)
            only_missing: If True, process only notes without topic_classification (skip reindexing modified notes)
            production_mode: If True, process ALL unclassified notes + notes modified YESTERDAY

        Returns:
            List of modified note paths
        """
        logger.info("🚀 Starting Daily Sync v2.1")
        logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        logger.info(f"📁 Vault: {vault_dir}")
        logger.info(f"🔧 Force all: {force_all}")
        logger.info(f"🔧 Only missing: {only_missing}")
        logger.info(f"🔧 Production mode: {production_mode}")

        # Scan vault with appropriate mode
        new_notes, modified_notes = self.scan_vault(
            vault_dir, production_mode=production_mode
        )

        # If force_all, find all notes without topic_classification
        all_notes_to_process = []
        if force_all:
            logger.info(
                "🔧 Force-all mode: Finding all notes without topic_classification"
            )
            all_notes_without_tc = self._find_all_notes_without_tc(vault_dir)
            all_notes_to_process = list(set(new_notes + all_notes_without_tc))
            logger.info(
                f"📝 Found {len(all_notes_without_tc)} notes without topic_classification"
            )
        elif only_missing:
            # Process only notes without topic_classification (skip reindexing)
            logger.info(
                "🔧 Only-missing mode: Processing only notes without topic_classification"
            )
            all_notes_without_tc = self._find_all_notes_without_tc(vault_dir)
            all_notes_to_process = all_notes_without_tc
            logger.info(
                f"📝 Found {len(all_notes_without_tc)} notes without topic_classification"
            )
            logger.info(
                f"   (Skipping {len(modified_notes)} modified notes that already have classification)"
            )
        else:
            all_notes_to_process = new_notes + modified_notes

        self.stats["notes_to_process"] = len(all_notes_to_process)

        if not all_notes_to_process:
            logger.info("✅ No notes need processing today")
            self._save_stats()
            return []

        logger.info(f"🎯 Processing {len(all_notes_to_process)} notes")

        # Check for dry-run mode
        if self.config.dry_run:
            logger.info("🧪 DRY-RUN MODE: Would extract topics for notes:")
            for i, note_path in enumerate(all_notes_to_process[:10], 1):
                logger.info(f"  [{i}] {note_path.name}")
            if len(all_notes_to_process) > 10:
                logger.info(f"  ... and {len(all_notes_to_process) - 10} more")

            # In dry-run mode, return empty list
            self._save_stats()
            return []

        # Extract topics
        note_results = self.extract_topics_for_notes(all_notes_to_process)

        # Write topics to notes
        modified_notes = self.write_topics_to_notes(note_results)

        # Log completion
        logger.info("=" * 60)
        logger.info("📊 DAILY SYNC COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total notes scanned: {self.stats['total_notes_scanned']}")
        logger.info(f"New notes found: {self.stats['new_notes_found']}")
        logger.info(
            f"Modified notes needing reindexing: {self.stats['modified_notes_found']}"
        )
        logger.info(f"Notes to process: {self.stats['notes_to_process']}")
        logger.info(f"Notes processed: {self.stats['notes_processed']}")
        logger.info(f"Notes failed: {self.stats['notes_failed']}")
        logger.info(
            f"Notes skipped: {self.stats['notes_skipped']} (due to failures: {self.stats['notes_skipped_due_to_failures']})"
        )

        # Save statistics
        self._save_stats()

        return modified_notes

    def _find_all_notes_without_tc(self, vault_dir: Path) -> List[Path]:
        """Find all notes without topic_classification (for force-all mode)."""
        notes_without_tc = []

        logger.info("🔍 Finding all notes without topic_classification")

        for md_file in vault_dir.rglob("*.md"):
            if md_file.name.startswith("."):
                continue
            if ".obsidian" in str(md_file):
                continue

            try:
                # Read frontmatter
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                has_tc = False
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter_raw = parts[1]
                        try:
                            frontmatter = yaml.safe_load(frontmatter_raw) or {}
                            # Ensure frontmatter is a dict before checking
                            if (
                                isinstance(frontmatter, dict)
                                and "topic_classification" in frontmatter
                            ):
                                has_tc = True
                        except yaml.YAMLError:
                            pass

                if not has_tc:
                    notes_without_tc.append(md_file)

            except Exception as e:
                logger.debug(f"Error checking {md_file}: {e}")

        return notes_without_tc

    def _save_stats(self):
        """Save statistics to JSON file."""
        stats_dir = self.config.log_dir / "daily_sync"
        stats_dir.mkdir(parents=True, exist_ok=True)

        today_str = datetime.now().strftime("%Y-%m-%d")
        stats_file = stats_dir / f"daily_sync_stats_{today_str}.json"

        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 Statistics saved to: {stats_file}")


def main():
    """CLI entry point for daily sync."""
    parser = argparse.ArgumentParser(
        description="Daily Sync System for Topic Classification v2.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run daily sync (process today's new/modified notes only)
  python -m src.topics.daily_sync --vault-dir "/path/to/vault"

  # Force process all notes without topic_classification
  python -m src.topics.daily_sync --vault-dir "/path/to/vault" --force-all

  # Process only notes without topic_classification (skip reindexing)
  python -m src.topics.daily_sync --vault-dir "/path/to/vault" --only-missing

  # Dry run (only scan, don't process)
  python -m src.topics.daily_sync --vault-dir "/path/to/vault" --dry-run

  # Limit number of notes to process
  python -m src.topics.daily_sync --vault-dir "/path/to/vault" --limit 10
        """,
    )

    parser.add_argument(
        "--vault-dir",
        type=str,
        required=True,
        help="Path to Obsidian vault (required)",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Process all notes without topic_classification (not just today's)",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        dest="only_missing",
        help="Process only notes without topic_classification (skip reindexing modified notes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only scan and log, don't extract or write topics",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of notes to process",
    )

    args = parser.parse_args()

    # Configure
    config = TopicConfig()
    config.dry_run = args.dry_run
    config.limit = args.limit

    # Create daily sync instance
    daily_sync = DailySync(config)

    # Run
    vault_dir = Path(args.vault_dir)
    modified_notes = daily_sync.process_notes(
        vault_dir, args.force_all, args.only_missing
    )

    # Exit code
    if daily_sync.stats["notes_failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
