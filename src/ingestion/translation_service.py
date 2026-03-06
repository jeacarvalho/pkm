"""Translation service for PDF chapter translation."""

from typing import Dict, List, Optional, Tuple

from src.ingestion.translator import translate_if_needed
from src.ingestion.language_detector import detect_document_language, get_language_name
from src.topics.translation_cache import TranslationCache
from src.utils.logging import get_logger
from src.utils.config import settings


logger = get_logger(__name__)


class TranslationService:
    """Service responsible only for translating chapter text.

    Responsibilities:
    - Detect document language
    - Translate chapters using cache
    - Save translations to cache
    """

    def __init__(
        self,
        vault_path: str,
        book_name: str,
        enable_translation: bool = True,
        target_language: str = "pt-br",
        force_retranslate: bool = False,
    ):
        """Initialize translation service.

        Args:
            vault_path: Path to vault
            book_name: Name of the book being processed
            enable_translation: Whether to enable translation
            target_language: Target language code
            force_retranslate: Force re-translation even if cached
        """
        self.vault_path = vault_path
        self.book_name = book_name
        self.enable_translation = enable_translation
        self.target_language = target_language
        self.force_retranslate = force_retranslate

        # Initialize cache
        self.cache = TranslationCache(
            vault_path, book_name, force_retranslate=force_retranslate
        )

        logger.info(f"TranslationService initialized for book: {book_name}")

    def detect_language(self, chapters: List[Dict]) -> str:
        """Detect the language of the document.

        Args:
            chapters: List of chapter data

        Returns:
            Language code
        """
        try:
            doc_language = detect_document_language(chapters, sample_size=5)
            logger.info(f"Detected language: {get_language_name(doc_language)}")
            return doc_language
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "en"

    def translate_chapter(
        self, chapter: Dict, chapter_num: int, doc_language: str
    ) -> Tuple[str, bool, bool]:
        """Translate a single chapter.

        Args:
            chapter: Chapter data with 'text' and 'chapter_num'
            chapter_num: Chapter number (0-indexed)
            doc_language: Detected document language

        Returns:
            Tuple of (translated_text, was_translated, was_cached)
        """
        # Check cache first
        cached_content = self.cache.get_cached_translation(chapter_num)

        if cached_content:
            logger.debug(f"Using cached translation for chapter {chapter_num}")
            return cached_content, False, True

        # Need to translate
        if self.enable_translation and doc_language != self.target_language:
            logger.info(f"Translating chapter {chapter_num}...")
            translated_text, was_translated = translate_if_needed(
                chapter["text"],
                target_lang=self.target_language,
                api_key=settings.gemini_api_key,
            )

            # Save to local cache immediately
            if was_translated:
                self.cache.save_to_local_cache(chapter_num, translated_text)

            return translated_text, was_translated, False

        # No translation needed
        return chapter["text"], False, False

    def process_chapters(
        self, chapters: List[Dict]
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """Process all chapters for translation.

        Args:
            chapters: List of chapter data

        Returns:
            Tuple of (processed chapters, stats)
        """
        # Detect language
        doc_language = self.detect_language(chapters)

        # Process each chapter
        processed = []
        stats = {"cached": 0, "translated": 0, "no_translation_needed": 0}

        for chapter in chapters:
            translated_text, was_translated, was_cached = self.translate_chapter(
                chapter, chapter["chapter_num"], doc_language
            )

            processed_chapter = {
                "chapter_num": chapter["chapter_num"],
                "start_page": chapter["start_page"],
                "end_page": chapter["end_page"],
                "chapter_text": translated_text,
                "title": chapter.get("title", f"Chapter {chapter['chapter_num'] + 1}"),
                "book_name": chapter.get("book_name", self.book_name),
                "translated": str(was_translated),
                "was_cached": was_cached,
            }

            # Update stats
            if was_cached:
                stats["cached"] += 1
            elif was_translated:
                stats["translated"] += 1
            else:
                stats["no_translation_needed"] += 1

            processed.append(processed_chapter)

        logger.info(f"Translation stats: {stats}")
        return processed, stats
