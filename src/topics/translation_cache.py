"""Translation Cache System for Sprint 11.

Cache logic to avoid re-translating already processed chapters.
Checks if chapter exists in vault and loads content from '## Conteúdo Traduzido' section.
"""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.utils.logging import get_logger

logger = get_logger(__name__)


class TranslationCache:
    """Cache system to avoid re-translating chapters.

    Flow:
    1. Check if chapter exists in vault
    2. IF exists → Load content from '## Conteúdo Traduzido' section
    3. IF not exists → Translate via Gemini + Save to vault

    Attributes:
        vault_path: Path to Obsidian vault.
        book_name: Name of the book.
        force_retranslate: If True, skip cache and always translate.
    """

    def __init__(
        self, vault_path: str, book_name: str, force_retranslate: bool = False
    ):
        """Initialize translation cache.

        Args:
            vault_path: Path to Obsidian vault or books directory.
            book_name: Name of the book.
            force_retranslate: If True, skip cache and always translate.
        """
        self.vault_path = Path(vault_path)
        self.book_name = book_name
        self.force_retranslate = force_retranslate

        # Determine if vault_path is root vault or books directory
        # Check if path ends with "100 ARQUIVOS E REFERENCIAS/Livros"
        if str(self.vault_path).endswith("100 ARQUIVOS E REFERENCIAS/Livros"):
            # Already books directory
            self.book_folder = self.vault_path / book_name
        else:
            # Assume root vault path
            self.book_folder = (
                self.vault_path / "100 ARQUIVOS E REFERENCIAS" / "Livros" / book_name
            )

    def get_cached_translation(self, chapter_num: int) -> Optional[str]:
        """Get cached translation for a chapter if it exists.

        Args:
            chapter_num: Chapter number (0-indexed).

        Returns:
            Cached translation text if found, None otherwise.
        """
        if self.force_retranslate:
            logger.debug(
                f"Force retranslate enabled, skipping cache for chapter {chapter_num}"
            )
            return None

        chapter_file = self._find_chapter_file(chapter_num)
        if not chapter_file or not chapter_file.exists():
            logger.debug(f"No cached file found for chapter {chapter_num}")
            return None

        try:
            content = self._extract_translated_content(chapter_file)
            if content:
                logger.info(f"✅ Using cached translation for chapter {chapter_num}")
                return content
            else:
                logger.warning(
                    f"Cached file exists but no translated content found for chapter {chapter_num}"
                )
                return None
        except Exception as e:
            logger.error(f"Error reading cached file for chapter {chapter_num}: {e}")
            return None

    def _find_chapter_file(self, chapter_num: int) -> Optional[Path]:
        """Find chapter file in book folder.

        Args:
            chapter_num: Chapter number (0-indexed).

        Returns:
            Path to chapter file if found, None otherwise.
        """
        if not self.book_folder.exists():
            return None

        # Try multiple filename patterns
        patterns = [
            f"{chapter_num:02d}_Capitulo_{chapter_num + 1:02d}.md",
            f"capitulo_{chapter_num + 1}.md",
            f"chapter_{chapter_num + 1}.md",
            f"{chapter_num + 1:02d}.md",
        ]

        for pattern in patterns:
            file_path = self.book_folder / pattern
            if file_path.exists():
                return file_path

        return None

    def _extract_translated_content(self, file_path: Path) -> Optional[str]:
        """Extract content from '## Conteúdo Traduzido' section.

        Args:
            file_path: Path to markdown file.

        Returns:
            Extracted translated content, or None if not found.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find the "## Conteúdo Traduzido" section
            # Look for the header and capture everything until next header or end of file
            pattern = r"^##\s+Conteúdo Traduzido\s*\n+(.*?)(?=^##|\Z)"
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted
                else:
                    logger.warning(f"Empty translated content in {file_path}")
                    return None
            else:
                logger.warning(
                    f"No '## Conteúdo Traduzido' section found in {file_path}"
                )
                return None

        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {e}")
            return None

    def mark_as_cached(self, chapter_num: int, file_path: Path) -> None:
        """Mark a chapter as cached by updating frontmatter.

        Args:
            chapter_num: Chapter number.
            file_path: Path to the chapter file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Update frontmatter to mark as cached
            updated_lines = []
            in_frontmatter = False
            for line in lines:
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    updated_lines.append(line)
                elif in_frontmatter and line.strip().startswith("translation_cached:"):
                    updated_lines.append("translation_cached: true\n")
                else:
                    updated_lines.append(line)

            # If translation_cached not found in frontmatter, add it
            if "translation_cached: true" not in "".join(updated_lines):
                # Find the second "---" (end of frontmatter)
                for i, line in enumerate(updated_lines):
                    if line.strip() == "---" and i > 0:
                        updated_lines.insert(i, "translation_cached: true\n")
                        break

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)

            logger.debug(f"Marked chapter {chapter_num} as cached in {file_path}")

        except Exception as e:
            logger.error(f"Error marking chapter {chapter_num} as cached: {e}")

    def check_cache_status(self, chapter_num: int) -> Dict[str, bool | str | None]:
        """Check cache status for a chapter.

        Args:
            chapter_num: Chapter number.

        Returns:
            Dictionary with cache status information.
        """
        chapter_file = self._find_chapter_file(chapter_num)
        exists = chapter_file is not None and chapter_file.exists()

        if not exists:
            return {
                "cached": False,
                "file_exists": False,
                "has_content": False,
                "force_retranslate": self.force_retranslate,
                "file_path": None,
            }

        has_content = False
        content = None
        if exists and chapter_file:
            content = self._extract_translated_content(chapter_file)
            has_content = content is not None and len(content.strip()) > 0

        return {
            "cached": has_content and not self.force_retranslate,
            "file_exists": exists,
            "has_content": has_content,
            "force_retranslate": self.force_retranslate,
            "file_path": str(chapter_file) if chapter_file else None,
        }


def integrate_with_translator(
    translator,
    text: str,
    chapter_num: int,
    vault_path: str,
    book_name: str,
    force_retranslate: bool = False,
    target_lang: str = "pt",
) -> Tuple[str, bool, bool]:
    """Integrate cache with existing translator.

    Args:
        translator: GeminiTranslator instance.
        text: Text to translate.
        chapter_num: Chapter number.
        vault_path: Path to Obsidian vault.
        book_name: Name of the book.
        force_retranslate: If True, skip cache.
        target_lang: Target language.

    Returns:
        Tuple of (translated_text, was_translated, was_cached).
    """
    cache = TranslationCache(vault_path, book_name, force_retranslate)

    # Check cache first
    cached_content = cache.get_cached_translation(chapter_num)
    if cached_content is not None:
        return cached_content, False, True

    # Not cached, need to translate
    logger.info(f"🔄 Translating chapter {chapter_num}...")
    translated, success = translator.translate(text, target_lang)

    if success:
        return translated, True, False
    else:
        logger.error(f"Failed to translate chapter {chapter_num}")
        return text, False, False
