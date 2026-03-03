#!/usr/bin/env python3
"""Incremental Indexing CLI - Manual and Automated Execution."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.indexing.backup_manager import BackupManager
from src.indexing.incremental_indexer import IncrementalIndexer
from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Incremental Indexing for Obsidian RAG"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Detect changes without indexing"
    )
    parser.add_argument(
        "--force-backup",
        action="store_true",
        help="Create backup even if no changes detected",
    )
    parser.add_argument(
        "--skip-rollback",
        action="store_true",
        help="Skip rollback on error (use with caution)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Load config
    config = Settings()

    # Initialize backup manager
    backup_manager = BackupManager(str(config.chroma_persist_dir))

    # Create backup BEFORE any operation
    backup_path = None
    try:
        backup_path = backup_manager.create_backup()
        logger.info("✅ Backup completed successfully")
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        if not args.skip_rollback:
            sys.exit(1)

    # Initialize incremental indexer
    indexer = IncrementalIndexer(config)

    # Detect changes
    try:
        changes = indexer.detect_changes()
        logger.info(
            f"📊 Changes detected: {len(changes['new'])} new, "
            f"{len(changes['modified'])} modified, "
            f"{len(changes['deleted'])} deleted"
        )
    except Exception as e:
        logger.error(f"❌ Change detection failed: {e}")
        # Rollback if backup exists
        if backup_path and not args.skip_rollback:
            backup_manager.restore_backup(backup_path)
            logger.warning("🔄 Rolled back to previous state")
        sys.exit(1)

    # Index new and modified notes
    if args.dry_run:
        logger.info("🔍 Dry run - no indexing performed")
        sys.exit(0)

    indexing_results = []
    try:
        files_to_index = changes["new"] + changes["modified"]
        for file_path in files_to_index:
            result = indexer.index_new_note(file_path)
            indexing_results.append(result)
            if result["status"] == "error":
                logger.error(f"❌ Failed to index {file_path}")

        success_count = sum(1 for r in indexing_results if r["status"] == "success")
        logger.info(f"✅ Indexed {success_count}/{len(files_to_index)} files")
    except Exception as e:
        logger.error(f"❌ Indexing failed: {e}")
        # Rollback if backup exists
        if backup_path and not args.skip_rollback:
            backup_manager.restore_backup(backup_path)
            logger.warning("🔄 Rolled back to previous state")
        sys.exit(1)

    # Remove deleted notes
    removal_result = {"chunks_removed": 0, "errors": []}
    try:
        removal_result = indexer.remove_deleted_notes(changes["deleted"])
        logger.info(
            f"🗑️ Removed {removal_result['chunks_removed']} chunks from deleted notes"
        )
    except Exception as e:
        logger.error(f"❌ Deletion failed: {e}")
        # Rollback if backup exists
        if backup_path and not args.skip_rollback:
            backup_manager.restore_backup(backup_path)
            logger.warning("🔄 Rolled back to previous state")
        sys.exit(1)

    # Cleanup old backups
    backup_manager.cleanup_old_backups(keep_last=3)

    # Generate execution report
    report = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "indexing": {
            "total_processed": len(indexing_results),
            "successful": sum(1 for r in indexing_results if r["status"] == "success"),
            "failed": sum(1 for r in indexing_results if r["status"] == "error"),
            "details": indexing_results,
        },
        "deletion": removal_result,
        "backup": {
            "created": str(backup_path) if backup_path else None,
            "retained_backups": len(
                list(backup_manager.backup_dir.glob("pre_incremental_*"))
            ),
        },
    }

    # Save report
    report_path = Path(
        f"data/logs/incremental_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Incremental indexing completed successfully")

    # Print summary
    print("\n" + "=" * 60)
    print("INCREMENTAL INDEXING REPORT")
    print("=" * 60)
    print(f"Status: {report['status'].upper()}")
    print(f"Timestamp: {report['timestamp']}")
    print(f"\nChanges:")
    print(f"  New files: {len(changes['new'])}")
    print(f"  Modified files: {len(changes['modified'])}")
    print(f"  Deleted files: {len(changes['deleted'])}")
    print(f"\nIndexing:")
    print(f"  Processed: {report['indexing']['total_processed']}")
    print(f"  Successful: {report['indexing']['successful']}")
    print(f"  Failed: {report['indexing']['failed']}")
    print(f"\nDeletion:")
    print(f"  Chunks removed: {report['deletion']['chunks_removed']}")
    print(f"\nBackup:")
    print(f"  Created: {report['backup']['created']}")
    print(f"  Retained: {report['backup']['retained_backups']}")
    print("=" * 60 + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
