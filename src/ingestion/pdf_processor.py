"""PDF Processing Pipeline - Main script for Sprint 02 and Sprint 06."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

from src.ingestion.chunker import chunk_book_by_chapters
from src.ingestion.chapter_parser import ChapterParser
from src.ingestion.language_detector import detect_document_language, get_language_name
from src.ingestion.text_extractor import extract_chapters, get_pdf_metadata
from src.ingestion.translator import GeminiTranslator, translate_if_needed
from src.topics.topic_extractor import TopicExtractor
from src.topics.topic_matcher import TopicMatcher
from src.topics.config import TopicConfig
from src.utils.config import settings
from src.utils.logging import get_logger
import re
import unicodedata

logger = get_logger(__name__)


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a safe filename slug."""
    # Remove accents
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Replace spaces and special chars with underscore
    text = re.sub(r"[^a-zA-Z0-9]", "_", text)
    # Remove multiple underscores
    text = re.sub(r"_+", "_", text)
    # Remove leading/trailing underscores
    text = text.strip("_")
    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip("_")
    return text.lower()


class ChapterProcessingError(Exception):
    """Exception raised when chapter processing fails."""

    pass


class ChapterTextExtractor:
    """Extracts text from PDF chapters."""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.reader = self._load_pdf()

    def _load_pdf(self) -> Any:
        """Load PDF file."""
        from PyPDF2 import PdfReader

        return PdfReader(str(self.pdf_path))

    def get_total_pages(self) -> int:
        """Get total number of pages in PDF."""
        return len(self.reader.pages)

    def extract_chapter_text(self, start_page: int, end_page: int) -> str:
        """Extract text from a range of pages."""
        chapter_text = ""
        for page_num in range(start_page - 1, min(end_page, self.get_total_pages())):
            chapter_text += self.reader.pages[page_num].extract_text() + "\n"
        return chapter_text

    def extract_chapter_title(self, chapter_num: int, start_page: int) -> str:
        """Extract chapter title from first page."""
        first_page_text = self.reader.pages[start_page - 1].extract_text()
        return extract_chapter_title(first_page_text, chapter_num)


class ChapterCacheManager:
    """Manages caching of translated chapter content."""

    def __init__(
        self,
        vault_path: Path,
        book_name: str,
        force_retranslate: bool = False,
    ):
        from src.topics.translation_cache import TranslationCache

        self.cache = TranslationCache(str(vault_path), book_name, force_retranslate)

    def get_cached_content(self, chapter_num: int) -> Optional[str]:
        """Get cached translation if available."""
        return self.cache.get_cached_translation(chapter_num)

    def save_translation(
        self, chapter_num: int, translated_text: str, was_translated: bool
    ) -> None:
        """Save translation to cache if it was translated."""
        if was_translated:
            self.cache.save_to_local_cache(chapter_num, translated_text)


class ChapterTopicExtractor:
    """Extracts topics and finds thematic connections for chapters."""

    def __init__(self, vault_path: Path, book_name: str, skip_validation: bool = False):
        self.vault_path = vault_path
        self.book_name = book_name
        self.skip_validation = skip_validation
        topic_config = TopicConfig()
        self.topic_extractor = TopicExtractor(topic_config)
        self.topic_matcher = TopicMatcher(topic_config)

    def extract_topics_and_connections(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        """Extract topics and find thematic connections for a chapter."""
        try:
            # Extract topics
            topic_result = self.topic_extractor.extract_topics(
                chapter["chapter_text"], is_chapter=True
            )

            # Add topic classification
            chapter["topic_classification"] = {
                "topics": topic_result.get("topics", []),
                "cdu_primary": topic_result.get("cdu_primary"),
                "cdu_secondary": topic_result.get("cdu_secondary", []),
                "cdu_description": topic_result.get("cdu_description"),
                "extraction_date": datetime.now().strftime("%Y-%m-%d"),
            }

            # Find thematic connections
            thematic_connections = self._find_thematic_connections(
                topic_result, chapter
            )
            chapter["thematic_connections"] = thematic_connections

        except Exception as e:
            logger.error(f"Topic processing failed for chapter: {e}")
            chapter["topic_classification"] = self._create_empty_classification(str(e))
            chapter["thematic_connections"] = []

        return chapter

    def _find_thematic_connections(
        self, topic_result: Dict[str, Any], chapter: Dict[str, Any]
    ) -> List[Dict]:
        """Find thematic connections in vault for chapter topics."""
        import tempfile
        import json

        # Create temporary JSON with chapter topics
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(
                {
                    "topics": topic_result.get("topics", []),
                    "chapter_title": chapter.get(
                        "title", f"Chapter {chapter['chapter_num']}"
                    ),
                    "chapter_number": chapter["chapter_num"],
                },
                tmp,
                ensure_ascii=False,
                indent=2,
            )
            tmp_path = tmp.name

        try:
            # Run topic matcher
            match_result = self.topic_matcher.run(
                chapter_topics_path=Path(tmp_path),
                vault_dir=settings.vault_path,
                output_path=None,
                top_k=20,
                threshold=0.0,
            )

            # Filter self-references
            return self._filter_self_references(match_result.get("matches", []))

        finally:
            import os

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _filter_self_references(self, matches: List[Dict]) -> List[Dict]:
        """Filter out matches that refer to the book itself."""
        filtered = []
        book_name_lower = self.book_name.lower()

        for match in matches:
            note_path = match.get("note_path", "")
            if book_name_lower not in note_path.lower():
                filtered.append(match)

        return filtered

    def _create_empty_classification(self, error: str = "") -> Dict:
        """Create empty topic classification structure."""
        classification = {
            "topics": [],
            "cdu_primary": None,
            "cdu_secondary": [],
            "cdu_description": None,
            "extraction_date": datetime.now().strftime("%Y-%m-%d"),
        }
        if error:
            classification["error"] = error
        return classification


def extract_chapter_title(first_page_text: str, chapter_num: int) -> str:
    """Extract chapter title from first page text.

    Looks for patterns like:
    - "CHAPTER X: Title" or "Chapter X"
    - Lines in UPPERCASE at the beginning
    - First significant line of text

    Returns:
        Chapter title string or "Chapter X" if not found
    """
    if not first_page_text:
        return f"Chapter {chapter_num + 1}"

    lines = first_page_text.strip().split("\n")

    # Clean up lines
    lines = [line.strip() for line in lines if line.strip()]

    if not lines:
        return f"Chapter {chapter_num + 1}"

    # Strategy 1: Look for "CHAPTER X" pattern
    for line in lines[:5]:
        # Check for "CHAPTER X" or "Chapter X" followed by text
        match = re.match(
            r"^(?:CHAPTER|Capítulo|Cap[ií]tulo)\s+\d+[:\s]+(.+)", line, re.IGNORECASE
        )
        if match:
            title = match.group(1).strip()
            if len(title) > 3:
                return title

    # Strategy 2: Look for first line that's not a page number or single word
    for line in lines[:3]:
        line = line.strip()
        # Skip if too short or looks like a page number
        if len(line) < 5 or line.isdigit() or re.match(r"^\d+\.\d+$", line):
            continue
        # Skip if it's all uppercase short text (likely a header)
        if len(line) < 20 and line.isupper():
            continue
        return line

    # Default: return "Chapter X"
    return f"Chapter {chapter_num + 1}"


class PDFProcessor:
    """Process PDF books for RAG pipeline.

    This class handles the complete pipeline:
    1. Extract text from PDF (by chapters or pages)
    2. Detect language and translate if needed
    3. Chunk text into smaller pieces (512 tokens) - Legacy mode
    4. OR Process by chapter ranges defined in capitulos.txt - Sprint 06 mode
    5. Generate metadata and save for Sprint 03

    Attributes:
        translator: GeminiTranslator instance.
        target_language: Target language for translation.
        enable_translation: Whether to enable translation.
        output_dir: Directory to save processed chunks.
        use_chapter_mode: Whether to process by chapter ranges instead of chunks.
        chapters_file: Path to capitulos.txt file.
        vault_path: Path to Obsidian vault for output.
        book_name: Name of the book for folder creation in vault.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        target_language: str = "pt",
        enable_translation: bool = True,
        output_dir: Optional[Path] = None,
        use_chapter_mode: bool = False,
        chapters_file: Optional[str] = None,
        vault_path: Optional[str] = None,
        book_name: Optional[str] = None,
        skip_validation: bool = False,
        force_retranslate: bool = False,
    ):
        """Initialize PDF processor.

        Args:
            api_key: Gemini API key. If None, uses settings.gemini_api_key.
            target_language: Target language code (default: 'pt').
            enable_translation: Whether to enable translation.
            output_dir: Directory to save processed chunks.
            use_chapter_mode: Whether to process by chapter ranges instead of chunks.
            chapters_file: Path to capitulos.txt file.
            vault_path: Path to Obsidian vault for output.
            book_name: Name of the book for folder creation in vault.
            skip_validation: Skip Ollama validation (for testing).
            force_retranslate: Force retranslation even if chapter exists in cache.
        """
        self.target_language = target_language
        self.enable_translation = enable_translation
        self.output_dir = output_dir or Path("./data/processed")
        self.use_chapter_mode = use_chapter_mode
        self.chapters_file = chapters_file
        vault_path_str = (
            str(vault_path)
            if vault_path
            else str(settings.vault_path / "100 ARQUIVOS E REFERENCIAS/Livros")
        )
        self.vault_path = vault_path_str
        self.book_name = book_name or ""
        self.skip_validation = skip_validation
        self.force_retranslate = force_retranslate

        if enable_translation:
            self.translator = GeminiTranslator(
                api_key=api_key or settings.gemini_api_key,
                rpm_limit=15,  # Free tier limit
            )
        else:
            self.translator = None
            logger.info("Translation disabled")

        # Ensure output directory exists
        if not use_chapter_mode:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_pdf(self, pdf_path: Path, dry_run: bool = False) -> Dict[str, Any]:
        """Process a single PDF file.

        Args:
            pdf_path: Path to PDF file.
            dry_run: If True, don't save output.

        Returns:
            Processing result with metadata and chunks.
        """
        logger.info(f"Processing PDF: {pdf_path}")

        # Check if we're using chapter-based processing
        if self.use_chapter_mode and self.chapters_file:
            return self._process_by_chapters(pdf_path, dry_run)
        else:
            return self._process_by_chunks(pdf_path, dry_run)

    def _process_by_chapters(
        self, pdf_path: Path, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process PDF by chapter ranges defined in capitulos.txt.

        This method orchestrates the chapter processing pipeline by delegating
        to specialized helper methods and classes for each responsibility.
        """
        logger.info(f"Processing PDF by chapters: {pdf_path}")

        # Parse and validate chapters
        chapters = self._parse_chapter_ranges()
        text_extractor = ChapterTextExtractor(pdf_path)
        self._validate_chapter_ranges(chapters, text_extractor.get_total_pages())

        # Extract metadata
        metadata = self._extract_pdf_metadata(pdf_path)

        if dry_run:
            return self._create_dry_run_result(chapters)

        # Extract chapter texts
        chapter_texts = self._extract_all_chapter_texts(chapters, text_extractor)

        # Detect document language
        doc_language = self._detect_document_language(chapter_texts)

        # Process chapters with caching
        cache_manager = ChapterCacheManager(
            Path(self.vault_path), self.book_name, self.force_retranslate
        )
        all_chapters_data = self._process_chapters_with_cache(
            chapter_texts, doc_language, cache_manager
        )

        # Extract topics and find connections
        topic_extractor = ChapterTopicExtractor(
            Path(self.vault_path), self.book_name, self.skip_validation
        )
        chapters_with_topics = self._extract_topics_for_all_chapters(
            all_chapters_data, topic_extractor
        )

        # Save to vault
        if not dry_run:
            self._save_chapters_to_vault(chapters_with_topics)

        return {
            "success": True,
            "chapters_processed": len(all_chapters_data),
            "language": doc_language,
        }

    def _parse_chapter_ranges(self) -> List[Any]:
        """Parse chapter ranges from chapters file."""
        logger.info(f"Parsing chapter file: {self.chapters_file}")
        chapter_parser = ChapterParser()
        chapters = chapter_parser.parse(str(self.chapters_file))
        chapter_parser.validate(chapters)
        logger.info(f"Loaded {len(chapters)} chapters")
        return chapters

    def _validate_chapter_ranges(self, chapters: List[Any], total_pages: int) -> None:
        """Validate chapter ranges against PDF page count."""
        max_chapter_page = max(c.end_page for c in chapters)
        if max_chapter_page > total_pages:
            raise ChapterProcessingError(
                f"Chapter file specifies page {max_chapter_page} "
                f"but PDF has only {total_pages} pages!"
            )
        logger.info(f"✅ PDF has {total_pages} pages - all chapter ranges are valid")

    def _extract_pdf_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF file."""
        try:
            metadata = get_pdf_metadata(pdf_path)
            logger.info(f"PDF Metadata: {metadata.get('title', 'Unknown')}")
            return metadata
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            return {}

    def _create_dry_run_result(self, chapters: List[Any]) -> Dict[str, Any]:
        """Create result for dry run mode."""
        logger.info(f"DRY RUN: Would process {len(chapters)} chapters")
        return {"success": True, "chapters": len(chapters), "dry_run": True}

    def _extract_all_chapter_texts(
        self, chapters: List[Any], text_extractor: ChapterTextExtractor
    ) -> List[Dict[str, Any]]:
        """Extract text for all chapters from PDF."""
        logger.info("Extracting text for chapters...")
        chapter_texts = []

        for chapter in chapters:
            chapter_text = text_extractor.extract_chapter_text(
                chapter.start_page, chapter.end_page
            )
            chapter_title = text_extractor.extract_chapter_title(
                chapter.num, chapter.start_page
            )

            chapter_info = {
                "chapter_num": chapter.num,
                "start_page": chapter.start_page,
                "end_page": chapter.end_page,
                "text": chapter_text,
                "title": chapter_title,
                "book_name": self.book_name,
            }
            chapter_texts.append(chapter_info)

        return chapter_texts

    def _detect_document_language(self, chapter_texts: List[Dict[str, Any]]) -> str:
        """Detect document language from sample chapters."""
        logger.info("Detecting document language...")
        try:
            doc_language = detect_document_language(chapter_texts, sample_size=5)
            logger.info(f"Detected language: {get_language_name(doc_language)}")
            return doc_language
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "en"

    def _process_chapters_with_cache(
        self,
        chapter_texts: List[Dict[str, Any]],
        doc_language: str,
        cache_manager: ChapterCacheManager,
    ) -> List[Dict[str, Any]]:
        """Process all chapters with cache support."""
        all_chapters_data = []
        cached_count = 0
        translated_count = 0

        for chapter in tqdm(chapter_texts, desc="Processing chapters"):
            try:
                chapter_data, was_cached = self._process_single_chapter(
                    chapter, doc_language, cache_manager
                )

                if was_cached:
                    cached_count += 1
                else:
                    translated_count += 1

                all_chapters_data.append(chapter_data)

            except Exception as e:
                logger.error(
                    f"Processing failed for chapter {chapter['chapter_num']}: {e}"
                )
                all_chapters_data.append(self._create_fallback_chapter_data(chapter))

        logger.info(f"📊 Processed {len(all_chapters_data)} chapters:")
        logger.info(f"   ✅ {cached_count} from cache")
        logger.info(f"   🔄 {translated_count} newly processed")

        return all_chapters_data

    def _process_single_chapter(
        self,
        chapter: Dict[str, Any],
        doc_language: str,
        cache_manager: ChapterCacheManager,
    ) -> Tuple[Dict[str, Any], bool]:
        """Process a single chapter with caching."""
        # Check cache first
        cached_content = cache_manager.get_cached_content(chapter["chapter_num"])

        if cached_content:
            logger.debug(
                f"✅ Using cached translation for chapter {chapter['chapter_num']}"
            )
            return {
                "chapter_num": chapter["chapter_num"],
                "start_page": chapter["start_page"],
                "end_page": chapter["end_page"],
                "chapter_text": cached_content,
                "title": chapter["title"],
                "book_name": chapter.get("book_name", "unknown"),
                "translated": "true",
                "was_cached": True,
            }, True

        # Need to translate
        return self._translate_and_cache_chapter(chapter, doc_language, cache_manager)

    def _translate_and_cache_chapter(
        self,
        chapter: Dict[str, Any],
        doc_language: str,
        cache_manager: ChapterCacheManager,
    ) -> Tuple[Dict[str, Any], bool]:
        """Translate chapter and save to cache."""
        if self.enable_translation and doc_language != self.target_language:
            logger.info(f"🔄 Translating chapter {chapter['chapter_num']}...")
            translated_text, was_translated = translate_if_needed(
                chapter["text"],
                target_lang=self.target_language,
                api_key=settings.gemini_api_key,
            )
        else:
            translated_text = chapter["text"]
            was_translated = False

        # Save to cache if translated
        if was_translated:
            cache_manager.save_translation(
                chapter["chapter_num"], translated_text, was_translated
            )
            time.sleep(1)  # Rate limit delay

        return {
            "chapter_num": chapter["chapter_num"],
            "start_page": chapter["start_page"],
            "end_page": chapter["end_page"],
            "chapter_text": translated_text,
            "title": chapter["title"],
            "book_name": chapter.get("book_name", "unknown"),
            "translated": str(was_translated),
            "was_cached": False,
        }, False

    def _create_fallback_chapter_data(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback chapter data when processing fails."""
        return {
            "chapter_num": chapter["chapter_num"],
            "start_page": chapter["start_page"],
            "end_page": chapter["end_page"],
            "chapter_text": chapter["text"],
            "title": chapter["title"],
            "book_name": chapter.get("book_name", "unknown"),
            "translated": "false",
            "was_cached": False,
        }

    def _extract_topics_for_all_chapters(
        self,
        chapters: List[Dict[str, Any]],
        topic_extractor: ChapterTopicExtractor,
    ) -> List[Dict[str, Any]]:
        """Extract topics and find connections for all chapters."""
        logger.info("Extracting topics and finding thematic connections...")
        chapters_with_topics = []

        for chapter in tqdm(chapters, desc="Extracting topics"):
            try:
                chapter_with_topics = topic_extractor.extract_topics_and_connections(
                    chapter
                )
                chapters_with_topics.append(chapter_with_topics)
            except Exception as e:
                logger.error(f"Topic extraction failed for chapter: {e}")
                chapter["topic_classification"] = {
                    "topics": [],
                    "cdu_primary": None,
                    "cdu_secondary": [],
                    "cdu_description": None,
                    "extraction_date": datetime.now().strftime("%Y-%m-%d"),
                    "error": str(e),
                }
                chapter["thematic_connections"] = []
                chapters_with_topics.append(chapter)

        return chapters_with_topics

    def _save_chapters_to_vault(
        self, chapters_with_topics: List[Dict[str, Any]]
    ) -> None:
        """Save processed chapters to vault."""
        try:
            from src.output.vault_writer import VaultWriter

            writer = VaultWriter(self.vault_path, self.book_name)
            chapter_paths = writer.write_all_chapters(chapters_with_topics)
            logger.info(f"Saved chapters to vault: {len(chapter_paths)} files created")
        except Exception as e:
            logger.error(f"Failed to save chapters to vault: {e}")
            raise ChapterProcessingError(f"Failed to save chapters: {e}")

    def _process_by_chunks(
        self, pdf_path: Path, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process a single PDF file using the original chunk-based approach.

        Args:
            pdf_path: Path to PDF file.
            dry_run: If True, don't save output.

        Returns:
            Processing result with metadata and chunks.
        """
        logger.info(f"Processing PDF: {pdf_path}")

        # Step 1: Extract metadata
        try:
            metadata = get_pdf_metadata(pdf_path)
            logger.info(f"PDF Metadata: {metadata.get('title', 'Unknown')}")
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            metadata = {}

        # Step 2: Extract text by chapters
        logger.info("Extracting chapters...")
        try:
            chapters = extract_chapters(pdf_path)
            logger.info(f"Extracted {len(chapters)} chapters/pages")
        except Exception as e:
            logger.error(f"Failed to extract chapters: {e}")
            return {"success": False, "error": str(e)}

        if dry_run:
            logger.info(f"DRY RUN: Would process {len(chapters)} chapters")
            return {"success": True, "chapters": len(chapters), "dry_run": True}

        # Step 3: Detect document language
        logger.info("Detecting document language...")
        try:
            # Sample pages for language detection
            doc_language = detect_document_language(chapters, sample_size=5)
            logger.info(f"Detected language: {get_language_name(doc_language)}")
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            doc_language = "en"

        # Step 4: Translate if needed
        translated_chapters = []

        if self.enable_translation and doc_language != self.target_language:
            logger.info(
                f"Translating from {get_language_name(doc_language)} to "
                f"{get_language_name(self.target_language)}..."
            )

            for chapter in tqdm(chapters, desc="Translating chapters"):
                try:
                    translated_text, was_translated = translate_if_needed(
                        chapter["text"],
                        target_lang=self.target_language,
                        api_key=settings.gemini_api_key,
                    )

                    chapter_copy = chapter.copy()
                    chapter_copy["text"] = translated_text
                    chapter_copy["translated"] = str(was_translated)
                    chapter_copy["original_language"] = doc_language
                    translated_chapters.append(chapter_copy)

                    # Small delay to respect rate limits
                    time.sleep(1)

                except Exception as e:
                    logger.error(
                        f"Translation failed for chapter '{chapter.get('title', 'Unknown')}': {e}"
                    )
                    # Keep original text on failure
                    chapter_copy = chapter.copy()
                    chapter_copy["translated"] = "false"
                    chapter_copy["translation_error"] = str(e)
                    translated_chapters.append(chapter_copy)
        else:
            # No translation needed
            translated_chapters = [
                {**ch, "translated": "false", "original_language": doc_language}
                for ch in chapters
            ]

        # Step 5: Chunk the chapters
        logger.info("Chunking chapters...")
        chunked_data = chunk_book_by_chapters(
            translated_chapters, max_tokens=512, overlap_tokens=50
        )

        logger.info(f"Created {len(chunked_data)} chunks")

        # Step 6: Save processed data
        output_file = self.output_dir / f"{pdf_path.stem}_chunks.json"

        result = {
            "metadata": {
                **metadata,
                "original_file": str(pdf_path),
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "language": doc_language,
                "translated": self.enable_translation
                and doc_language != self.target_language,
                "total_chunks": len(chunked_data),
            },
            "chunks": chunked_data,
        }

        if not dry_run:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved processed chunks to: {output_file}")
            except Exception as e:
                logger.error(f"Failed to save output: {e}")
                return {"success": False, "error": str(e)}

        return {
            "success": True,
            "output_file": str(output_file) if not dry_run else None,
            "chunks": len(chunked_data),
            "language": doc_language,
        }

    def process_library(
        self, library_path: Path, dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Process all PDFs in a library directory.

        Args:
            library_path: Path to directory containing PDFs.
            dry_run: If True, count only.

        Returns:
            List of processing results.
        """
        # Find all PDF files
        pdf_files = list(library_path.glob("**/*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {library_path}")

        if dry_run:
            logger.info("DRY RUN: Would process all PDFs")
            return [{"file": str(pdf), "dry_run": True} for pdf in pdf_files]

        # Process each PDF
        results = []
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                result = self.process_pdf(pdf_file, dry_run=False)
                results.append({"file": str(pdf_file), **result})
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                results.append(
                    {"file": str(pdf_file), "success": False, "error": str(e)}
                )

        return results


def main():
    """Main entry point for PDF processing CLI.

    This now uses PDFProcessorCoordinator which delegates to specialized services.
    For backwards compatibility, the old PDFProcessor is still available.
    """
    from src.ingestion.pdf_processor_coordinator import PDFProcessorCoordinator

    parser = argparse.ArgumentParser(description="Process PDF books for Obsidian RAG")
    parser.add_argument("--book", type=str, help="Path to single PDF file to process")
    parser.add_argument("--library", type=str, help="Path to directory containing PDFs")
    parser.add_argument(
        "--dry-run", action="store_true", help="Count only, don't process"
    )
    parser.add_argument(
        "--no-translate", action="store_true", help="Skip translation (for testing)"
    )
    parser.add_argument(
        "--target-lang",
        type=str,
        default="pt",
        help="Target language for translation (default: pt)",
    )
    parser.add_argument(
        "--chapters", type=str, help="Path to capitulos.txt file with chapter ranges"
    )
    parser.add_argument(
        "--vault-path",
        type=str,
        default=str(settings.vault_path / "100 ARQUIVOS E REFERENCIAS/Livros"),
        help="Path to Obsidian vault for output (default from config)",
    )
    parser.add_argument(
        "--book-name", type=str, help="Name of the book for folder creation in vault"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Ollama validation (for testing)",
    )
    parser.add_argument(
        "--force-retranslate",
        action="store_true",
        help="Force retranslation even if chapter exists in cache",
    )

    args = parser.parse_args()

    if not args.book and not args.library:
        parser.error("Must specify --book or --library")

    # Determine if we're using chapter-based processing
    use_chapter_mode = bool(args.chapters)

    # Initialize coordinator (new refactored version)
    coordinator = PDFProcessorCoordinator(
        pdf_path=args.book if args.book else args.library,
        vault_path=args.vault_path,
        book_name=args.book_name
        or (args.book and Path(args.book).stem.replace(" ", "_")),
        chapters_file=args.chapters,
        enable_translation=not args.no_translate,
        target_language=args.target_lang,
        force_retranslate=args.force_retranslate,
        skip_validation=args.skip_validation,
    )

    # Process
    if args.book:
        result = coordinator.process(dry_run=args.dry_run)

        print("\n" + "=" * 50)
        print("PROCESSING RESULT")
        print("=" * 50)
        for key, value in result.items():
            print(f"{key}: {value}")

    elif args.library:
        # For library processing, still use old processor
        processor = PDFProcessor(
            target_language=args.target_lang,
            enable_translation=not args.no_translate,
            use_chapter_mode=False,
            vault_path=args.vault_path,
            book_name="library",
        )
        results = processor.process_library(Path(args.library), dry_run=args.dry_run)

        print("\n" + "=" * 50)
        print("LIBRARY PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Total files: {len(results)}")
        successful = sum(1 for r in results if r.get("success"))
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")

        total_chunks = sum(r.get("chunks", 0) for r in results)
        print(f"Total chunks: {total_chunks}")


if __name__ == "__main__":
    main()
