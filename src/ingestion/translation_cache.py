"""Translation Cache - Manage cached translations for book chapters."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class TranslationCache:
    """Manage translation cache for book chapters.

    Checks if chapter already exists in vault before translating.
    """

    def __init__(self, vault_path: str, book_name: str):
        """Initialize translation cache.

        Args:
            vault_path: Base path to Obsidian vault.
            book_name: Name of the book folder.
        """
        self.vault_path = Path(vault_path)
        self.book_folder = (
            self.vault_path / "100 ARQUIVOS E REFERENCIAS" / "Livros" / book_name
        )

    def chapter_exists(self, chapter_num: int) -> bool:
        """Check if chapter file already exists in vault.

        Args:
            chapter_num: Chapter number (0-indexed).

        Returns:
            bool: True if chapter file exists.
        """
        chapter_file = (
            self.book_folder / f"{chapter_num:02d}_Capitulo_{chapter_num + 1:02d}.md"
        )
        exists = chapter_file.exists()
        logger.info(
            f"📁 Chapter {chapter_num}: {'Found' if exists else 'Not found'} at {chapter_file}"
        )
        return exists

    def load_translated_content(self, chapter_num: int) -> Optional[str]:
        """Load translated content from existing chapter file.

        Args:
            chapter_num: Chapter number (0-indexed).

        Returns:
            str: Translated chapter content, or None if file doesn't exist or is malformed.
        """
        chapter_file = (
            self.book_folder / f"{chapter_num:02d}_Capitulo_{chapter_num + 1:02d}.md"
        )

        if not chapter_file.exists():
            logger.info(f"❌ Chapter {chapter_num}: File not found")
            return None

        try:
            content = chapter_file.read_text(encoding="utf-8")

            # Extract content between "## Conteúdo Traduzido" and "---" (matches section)
            translated = self._extract_translated_content(content)

            if translated:
                logger.info(
                    f"✅ Chapter {chapter_num}: Loaded cached translation ({len(translated)} chars)"
                )
                return translated
            else:
                logger.warning(
                    f"⚠️ Chapter {chapter_num}: No translated content found in file"
                )
                return None

        except Exception as e:
            logger.error(f"❌ Chapter {chapter_num}: Failed to load cache: {e}")
            return None

    def _extract_translated_content(self, markdown_content: str) -> Optional[str]:
        """Extract translated content section from Markdown file."""
        # Look for section between "## Conteúdo Traduzido" and "---" (before matches)
        match = re.search(
            r"## Conteúdo Traduzido\s*\n\s*\n(.*?)\n\s*---\s*\n",
            markdown_content,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return None

    def get_chapters_in_vault(self) -> List[int]:
        """Get list of chapter numbers that already exist in vault.

        Returns:
            List of chapter numbers (0-indexed) that have been processed.
        """
        if not self.book_folder.exists():
            return []

        chapters = []
        for f in self.book_folder.glob("*.md"):
            # Parse filename: 00_Capitulo_01.md -> chapter 0
            match = re.match(r"(\d+)_Capitulo_(\d+)\.md", f.name)
            if match:
                chapters.append(int(match.group(1)))

        logger.info(f"📁 Found {len(chapters)} chapters in vault: {sorted(chapters)}")
        return sorted(chapters)

    def get_missing_chapters(self, total_chapters: List[Dict]) -> List[Dict]:
        """Get list of chapters that need to be processed.

        Args:
            total_chapters: List of chapter dicts with 'num', 'start_page', 'end_page'.

        Returns:
            List of chapters that don't exist in vault yet.
        """
        existing = set(self.get_chapters_in_vault())
        missing = [c for c in total_chapters if c["num"] not in existing]

        if missing:
            logger.info(
                f"🔄 Need to process {len(missing)} chapters: {[c['num'] for c in missing]}"
            )
        else:
            logger.info(f"✅ All {len(total_chapters)} chapters already processed!")

        return missing
