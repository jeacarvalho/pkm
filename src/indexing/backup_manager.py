"""Backup and rollback management for ChromaDB."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_directory_size(path: Path) -> str:
    """Calculate directory size in human-readable format."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = Path(dirpath) / filename
            if filepath.exists():
                total_size += filepath.stat().st_size

    # Convert to human readable
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if total_size < 1024.0:
            return f"{total_size:.2f} {unit}"
        total_size /= 1024.0
    return f"{total_size:.2f} PB"


class BackupManager:
    """Manage ChromaDB backup and rollback."""

    def __init__(self, chroma_path: str, backup_dir: str = "data/backups/incremental"):
        self.chroma_path = Path(chroma_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Optional[Path]:
        """Create timestamped backup before modifications."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"pre_incremental_{timestamp}"

        logger.info(f"🔄 Creating backup: {backup_path}")

        if self.chroma_path.exists():
            shutil.copytree(self.chroma_path, backup_path, dirs_exist_ok=True)
            logger.info(f"✅ Backup created: {backup_path}")
            logger.info(f"📊 Backup size: {get_directory_size(backup_path)}")
            return backup_path
        else:
            logger.warning("⚠️ ChromaDB path does not exist, skipping backup")
            return None

    def restore_backup(self, backup_path: Path) -> bool:
        """Restore backup in case of failure."""
        if not backup_path or not backup_path.exists():
            logger.error("❌ No backup available for restore")
            return False

        logger.info(f"🔄 Restoring backup: {backup_path}")

        # Remove current (potentially corrupted) ChromaDB
        if self.chroma_path.exists():
            shutil.rmtree(self.chroma_path)

        # Restore from backup
        shutil.copytree(backup_path, self.chroma_path)
        logger.info(f"✅ Backup restored successfully")
        return True

    def cleanup_old_backups(self, keep_last: int = 3):
        """Keep only last N backups to save space."""
        backups = sorted(self.backup_dir.glob("pre_incremental_*"))

        if len(backups) > keep_last:
            for old_backup in backups[:-keep_last]:
                shutil.rmtree(old_backup)
                logger.info(f"🧹 Cleaned old backup: {old_backup}")
