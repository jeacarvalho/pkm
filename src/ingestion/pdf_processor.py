"""PDF Processing Pipeline - Main script for Sprint 02."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from src.ingestion.chunker import chunk_book_by_chapters
from src.ingestion.language_detector import detect_document_language, get_language_name
from src.ingestion.text_extractor import extract_chapters, get_pdf_metadata
from src.ingestion.translator import GeminiTranslator, translate_if_needed
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """Process PDF books for RAG pipeline.

    This class handles the complete pipeline:
    1. Extract text from PDF (by chapters or pages)
    2. Detect language and translate if needed
    3. Chunk text into smaller pieces (512 tokens)
    4. Generate metadata and save for Sprint 03

    Attributes:
        translator: GeminiTranslator instance.
        target_language: Target language for translation.
        enable_translation: Whether to enable translation.
        output_dir: Directory to save processed chunks.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        target_language: str = "pt",
        enable_translation: bool = True,
        output_dir: Optional[Path] = None,
    ):
        """Initialize PDF processor.

        Args:
            api_key: Gemini API key. If None, uses settings.gemini_api_key.
            target_language: Target language code (default: 'pt').
            enable_translation: Whether to enable translation.
            output_dir: Directory to save processed chunks.
        """
        self.target_language = target_language
        self.enable_translation = enable_translation
        self.output_dir = output_dir or Path("./data/processed")

        if enable_translation:
            self.translator = GeminiTranslator(
                api_key=api_key or settings.gemini_api_key,
                rpm_limit=15,  # Free tier limit
            )
        else:
            self.translator = None
            logger.info("Translation disabled")

        # Ensure output directory exists
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

    args = parser.parse_args()

    if not args.book and not args.library:
        parser.error("Must specify --book or --library")

    # Initialize processor
    processor = PDFProcessor(
        target_language=args.target_lang, enable_translation=not args.no_translate
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
