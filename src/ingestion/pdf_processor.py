"""PDF Processing Pipeline - Main script for Sprint 02 and Sprint 06."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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

logger = get_logger(__name__)


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
        """Process PDF by chapter ranges defined in capitulos.txt."""
        logger.info(f"Processing PDF by chapters: {pdf_path}")

        # Step 1: Parse chapter ranges
        logger.info(f"Parsing chapter file: {self.chapters_file}")
        chapter_parser = ChapterParser()
        chapters = chapter_parser.parse(str(self.chapters_file))
        chapter_parser.validate(chapters)

        logger.info(f"Loaded {len(chapters)} chapters")

        # Step 2: Extract metadata
        try:
            metadata = get_pdf_metadata(pdf_path)
            logger.info(f"PDF Metadata: {metadata.get('title', 'Unknown')}")
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            metadata = {}

        if dry_run:
            logger.info(f"DRY RUN: Would process {len(chapters)} chapters")
            return {"success": True, "chapters": len(chapters), "dry_run": True}

        # Step 4: Initialize cache and prepare chapters
        from src.topics.translation_cache import TranslationCache

        cache = TranslationCache(
            self.vault_path, self.book_name, force_retranslate=self.force_retranslate
        )

        # Prepare chapter information
        all_chapters = [
            {"num": c.num, "start_page": c.start_page, "end_page": c.end_page}
            for c in chapters
        ]

        # Step 5: Extract text for ALL chapters first
        logger.info("Extracting text for chapters...")
        from PyPDF2 import PdfReader

        reader = PdfReader(str(pdf_path))
        chapter_texts = []

        for ch in all_chapters:
            chapter_text = ""
            for page_num in range(
                ch["num"] - 1, min(ch["end_page"], len(reader.pages))
            ):
                chapter_text += reader.pages[page_num].extract_text() + "\n"

            chapter_info = {
                "chapter_num": ch["num"],
                "start_page": ch["start_page"],
                "end_page": ch["end_page"],
                "text": chapter_text,
                "title": f"Chapter {ch['num'] + 1}",
            }
            chapter_texts.append(chapter_info)

        # Step 6: Detect document language
        logger.info("Detecting document language...")
        try:
            doc_language = detect_document_language(chapter_texts, sample_size=5)
            logger.info(f"Detected language: {get_language_name(doc_language)}")
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            doc_language = "en"

        # Step 7: Process all chapters with cache support
        all_chapters_data = []
        cached_count = 0
        translated_count = 0

        for chapter in tqdm(chapter_texts, desc="Processing chapters"):
            try:
                # First check cache
                cached_content = cache.get_cached_translation(chapter["chapter_num"])

                if cached_content:
                    # Use cached content
                    chapter_data = {
                        "chapter_num": chapter["chapter_num"],
                        "start_page": chapter["start_page"],
                        "end_page": chapter["end_page"],
                        "chapter_text": cached_content,
                        "title": chapter["title"],
                        "translated": "true",
                        "was_cached": True,
                    }
                    cached_count += 1
                    logger.debug(
                        f"✅ Using cached translation for chapter {chapter['chapter_num']}"
                    )
                else:
                    # Need to process (translate if needed)
                    if self.enable_translation and doc_language != self.target_language:
                        logger.info(
                            f"🔄 Translating chapter {chapter['chapter_num']}..."
                        )
                        translated_text, was_translated = translate_if_needed(
                            chapter["text"],
                            target_lang=self.target_language,
                            api_key=settings.gemini_api_key,
                        )
                    else:
                        # No translation needed
                        translated_text = chapter["text"]
                        was_translated = False

                    chapter_data = {
                        "chapter_num": chapter["chapter_num"],
                        "start_page": chapter["start_page"],
                        "end_page": chapter["end_page"],
                        "chapter_text": translated_text,
                        "title": chapter["title"],
                        "translated": str(was_translated),
                        "was_cached": False,
                    }
                    translated_count += 1

                    # Small delay to respect rate limits
                    if was_translated:
                        time.sleep(1)

                all_chapters_data.append(chapter_data)

            except Exception as e:
                logger.error(
                    f"Processing failed for chapter {chapter['chapter_num']}: {e}"
                )
                chapter_data = {
                    "chapter_num": chapter["chapter_num"],
                    "start_page": chapter["start_page"],
                    "end_page": chapter["end_page"],
                    "chapter_text": chapter["text"],
                    "title": chapter["title"],
                    "translated": "false",
                    "was_cached": False,
                }
                all_chapters_data.append(chapter_data)

        # Log summary
        logger.info(f"📊 Processed {len(all_chapters_data)} chapters:")
        logger.info(f"   ✅ {cached_count} from cache")
        logger.info(f"   🔄 {translated_count} newly processed")

        # Step 9: Validate chapters if requested
        if self.skip_validation:
            logger.info("Skipping validation (--skip-validation flag)")
            validated_chapters = all_chapters_data
        else:
            logger.info("Validating chapters with Gemini...")
            try:
                from src.validation.gemini_validator import GeminiValidator
                from src.validation.pipeline import deduplicate_candidates
                from src.retrieval.pipeline import RetrievalPipeline
                from src.utils.config import Settings

                config = Settings()
                config.rerank_threshold = (
                    0.0  # Use 0 to get candidates even with low scores
                )

                validator = GeminiValidator(config)
                retrieval = RetrievalPipeline(config)

                validated_chapters = []
                for chapter in tqdm(all_chapters_data, desc="Validating chapters"):
                    # Get candidates from retrieval
                    logger.info(f"🔍 Processing chapter {chapter['chapter_num']}...")
                    candidates = retrieval.retrieve(
                        query_text=chapter["chapter_text"],
                        n_results_initial=20,
                        n_results_final=10,  # Get more for deduplication
                        generate_embedding=True,
                    )

                    # Deduplicate candidates before validation
                    unique_candidates = deduplicate_candidates(
                        candidates, max_unique=10
                    )
                    logger.info(
                        f"🔄 Validating {len(unique_candidates)} unique notes..."
                    )

                    # Validate with Gemini
                    validated = validator.validate_batch(
                        book_chunk=chapter["chapter_text"],
                        candidates=unique_candidates,
                    )

                    chapter["validated_matches"] = validated
                    validated_chapters.append(chapter)

            except Exception as e:
                logger.error(f"Validation failed: {e}")
                # If validation fails, continue with original chapters
                validated_chapters = all_chapters_data

        # Step 7: Extract topics and find thematic connections
        logger.info("Extracting topics and finding thematic connections...")
        chapters_with_topics = []

        try:
            # Initialize topic extractor and matcher
            topic_config = TopicConfig()
            topic_extractor = TopicExtractor(topic_config)
            topic_matcher = TopicMatcher(topic_config)

            for chapter in tqdm(validated_chapters, desc="Extracting topics"):
                try:
                    # Extract topics from chapter content (use chapter-specific prompt for generic topics)
                    logger.info(
                        f"📚 Extracting topics for chapter {chapter['chapter_num']}..."
                    )
                    topic_result = topic_extractor.extract_topics(
                        chapter["chapter_text"], is_chapter=True
                    )

                    # Add topic classification to chapter data
                    chapter["topic_classification"] = {
                        "topics": topic_result.get("topics", []),
                        "cdu_primary": topic_result.get("cdu_primary"),
                        "cdu_secondary": topic_result.get("cdu_secondary", []),
                        "cdu_description": topic_result.get("cdu_description"),
                        "extraction_date": datetime.now().strftime("%Y-%m-%d"),
                    }

                    # Find thematic connections in vault
                    logger.info(
                        f"🔍 Finding thematic connections for chapter {chapter['chapter_num']}..."
                    )

                    # Create temporary JSON file with chapter topics for matcher
                    import tempfile
                    import json

                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    ) as tmp:
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
                        match_result = topic_matcher.run(
                            chapter_topics_path=Path(tmp_path),
                            vault_dir=settings.vault_path,  # Use vault root directory directly
                            output_path=None,  # Don't save to file, we'll use the result directly
                            top_k=5,  # Changed from 20 to 5 per user request
                            threshold=2.0,
                        )

                        # Add thematic connections to chapter data
                        if "matches" in match_result:
                            # Filter out self-references (chapter matching with itself)
                            filtered_matches = []
                            for match in match_result["matches"]:
                                note_path = match.get("note_path", "")
                                # Skip if note_path contains the current book directory
                                book_name_lower = self.book_name.lower()
                                if book_name_lower in note_path.lower():
                                    continue
                                filtered_matches.append(match)

                            chapter["thematic_connections"] = filtered_matches
                            logger.info(
                                f"✅ Found {len(filtered_matches)} thematic connections for chapter {chapter['chapter_num']} (filtered from {len(match_result['matches'])} total)"
                            )
                        else:
                            chapter["thematic_connections"] = []
                            logger.info(
                                f"⚠️ No thematic connections found for chapter {chapter['chapter_num']}"
                            )

                    finally:
                        # Clean up temporary file
                        import os

                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

                except Exception as e:
                    logger.error(
                        f"Topic processing failed for chapter {chapter['chapter_num']}: {e}"
                    )
                    # Add empty topic classification if extraction fails
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

        except Exception as e:
            logger.error(f"Topic processing failed: {e}")
            # Continue without topics
            chapters_with_topics = validated_chapters
            for chapter in chapters_with_topics:
                chapter["topic_classification"] = {
                    "topics": [],
                    "cdu_primary": None,
                    "cdu_secondary": [],
                    "cdu_description": None,
                    "extraction_date": datetime.now().strftime("%Y-%m-%d"),
                    "error": str(e),
                }
                chapter["thematic_connections"] = []

        # Step 8: Save processed data to vault
        if not dry_run:
            try:
                # Import vault writer here to avoid circular imports
                from src.output.vault_writer import VaultWriter

                writer = VaultWriter(self.vault_path, self.book_name)
                chapter_paths = writer.write_all_chapters(chapters_with_topics)

                logger.info(
                    f"Saved chapters to vault: {len(chapter_paths)} files created"
                )
            except Exception as e:
                logger.error(f"Failed to save chapters to vault: {e}")
                return {"success": False, "error": str(e)}

        return {
            "success": True,
            "chapters_processed": len(validated_chapters),
            "language": doc_language,
        }

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
    """Main entry point for PDF processing CLI."""
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
    # New arguments for Sprint 06 - Chapter-based processing
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

    # Initialize processor
    processor = PDFProcessor(
        target_language=args.target_lang,
        enable_translation=not args.no_translate,
        use_chapter_mode=use_chapter_mode,
        chapters_file=args.chapters,
        vault_path=args.vault_path,
        book_name=args.book_name
        or (args.book and Path(args.book).stem.replace(" ", "_")),
        skip_validation=args.skip_validation,
        force_retranslate=args.force_retranslate,
    )

    # Process
    if args.book:
        result = processor.process_pdf(Path(args.book), dry_run=args.dry_run)

        print("\n" + "=" * 50)
        print("PROCESSING RESULT")
        print("=" * 50)
        for key, value in result.items():
            print(f"{key}: {value}")

    elif args.library:
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
