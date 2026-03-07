"""PDF Processor Coordinator - orchestrates the complete PDF processing pipeline.

This is the main entry point for processing PDF books.
It delegates specific tasks to specialized services.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from PyPDF2 import PdfReader
from tqdm import tqdm

from src.ingestion.chapter_parser import ChapterParser
from src.ingestion.chapter_title_extractor import extract_chapter_title
from src.ingestion.translation_service import TranslationService
from src.ingestion.topic_extraction_service import TopicExtractionService
from src.ingestion.topic_matching_service import TopicMatchingService
from src.output.vault_writer import VaultWriter
from src.utils.logging import get_logger
from src.utils.config import settings


logger = get_logger(__name__)


class PDFProcessorCoordinator:
    """Coordinates the complete PDF processing pipeline.

    This class delegates to specialized services:
    - TranslationService: handles translation
    - TopicExtractionService: extracts topics
    - TopicMatchingService: matches to vault notes
    - VaultWriter: writes output files

    Each service can be tested independently.
    """

    def __init__(
        self,
        pdf_path: str,
        vault_path: str,
        book_name: str,
        chapters_file: Optional[str] = None,
        enable_translation: bool = True,
        target_language: str = "pt-br",
        force_retranslate: bool = False,
        skip_validation: bool = True,
    ):
        """Initialize coordinator.

        Args:
            pdf_path: Path to PDF file
            vault_path: Path to Obsidian vault (should be root vault, not Livros folder)
            book_name: Name of the book
            chapters_file: Optional path to chapters file
            enable_translation: Enable translation
            target_language: Target language for translation
            force_retranslate: Force re-translation
            skip_validation: Skip embedding validation (use topic matching)
        """
        self.pdf_path = Path(pdf_path)

        # Determine vault root - should be the root of the Obsidian vault (e.g., /path/to/Minhas_notas)
        vault_path_obj = Path(vault_path)

        # If path ends with "Livros", go up to find vault root
        if vault_path_obj.name == "Livros":
            self.vault_root = vault_path_obj.parent.parent  # .../Minhas_notas
        elif "100 ARQUIVOS E REFERENCIAS" in str(vault_path_obj):
            # Path includes the intermediate folders, go up to vault root
            self.vault_root = vault_path_obj.parent.parent.parent  # .../Minhas_notas
        else:
            # Assume it's already the vault root
            self.vault_root = vault_path_obj

        self.vault_path = str(self.vault_root)
        self.book_name = book_name
        self.chapters_file = chapters_file
        self.enable_translation = enable_translation
        self.target_language = target_language
        self.force_retranslate = force_retranslate
        self.skip_validation = skip_validation

        # Services (initialized lazily)
        self._translation_service: Optional[TranslationService] = None
        self._topic_extraction_service: Optional[TopicExtractionService] = None
        self._topic_matching_service: Optional[TopicMatchingService] = None

        logger.info(f"PDFProcessorCoordinator initialized for: {book_name}")

    # Properties for lazy initialization
    @property
    def translation_service(self) -> TranslationService:
        if self._translation_service is None:
            self._translation_service = TranslationService(
                vault_path=self.vault_path,
                book_name=self.book_name,
                enable_translation=self.enable_translation,
                target_language=self.target_language,
                force_retranslate=self.force_retranslate,
            )
        return self._translation_service

    @property
    def topic_extraction_service(self) -> TopicExtractionService:
        if self._topic_extraction_service is None:
            self._topic_extraction_service = TopicExtractionService()
        return self._topic_extraction_service

    @property
    def topic_matching_service(self) -> TopicMatchingService:
        if self._topic_matching_service is None:
            self._topic_matching_service = TopicMatchingService(
                vault_path=self.vault_path,
                top_k=20,  # Default for topic matching
                threshold=0.0,  # Accept all matches
            )
        return self._topic_matching_service

    def process(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute the complete PDF processing pipeline.

        Args:
            dry_run: If True, don't save output

        Returns:
            Processing result dictionary
        """
        logger.info(f"Starting processing: {self.book_name}")

        # Step 1: Parse chapters
        chapters = self._parse_chapters()
        logger.info(f"Found {len(chapters)} chapters")

        # Step 2: Extract text from PDF
        chapter_texts = self._extract_chapter_texts(chapters)

        # Step 3: Translate chapters
        translated_chapters, translation_stats = (
            self.translation_service.process_chapters(chapter_texts)
        )
        logger.info(f"Translation complete: {translation_stats}")

        # Step 4: Extract topics
        chapters_with_topics = self.topic_extraction_service.process_chapters(
            translated_chapters
        )

        # Step 5: Match to vault (skip validation - using topic matching)
        if not self.skip_validation:
            logger.info("Skipping topic matching")
        else:
            logger.info("Using topic-based matching")

        chapters_with_connections = self.topic_matching_service.process_chapters(
            chapters_with_topics
        )

        # Step 6: Write to vault
        if not dry_run:
            self._write_chapters(chapters_with_connections)

        return {
            "success": True,
            "chapters_processed": len(chapters),
            "translation_stats": translation_stats,
        }

    def _parse_chapters(self) -> List[Dict]:
        """Parse chapter definitions from file."""
        if not self.chapters_file:
            return []

        parser = ChapterParser()
        chapters = parser.parse(self.chapters_file)
        parser.validate(chapters)

        return [
            {"num": c.num, "start_page": c.start_page, "end_page": c.end_page}
            for c in chapters
        ]

    def _extract_chapter_texts(self, chapters: List[Dict]) -> List[Dict]:
        """Extract text for each chapter from PDF."""
        reader = PdfReader(str(self.pdf_path))
        total_pages = len(reader.pages)

        # Validate chapter ranges
        max_chapter_page = max(c["end_page"] for c in chapters)
        if max_chapter_page > total_pages:
            raise ValueError(
                f"Chapter file specifies page {max_chapter_page} but PDF has {total_pages} pages"
            )

        chapter_texts = []

        for ch in tqdm(chapters, desc="Extracting text"):
            chapter_text = ""
            for page_num in range(
                ch["start_page"] - 1, min(ch["end_page"], total_pages)
            ):
                chapter_text += reader.pages[page_num].extract_text() + "\n"

            # Extract title from first page
            first_page = reader.pages[ch["start_page"] - 1].extract_text()
            title = extract_chapter_title(first_page, ch["num"])

            chapter_texts.append(
                {
                    "chapter_num": ch["num"],
                    "start_page": ch["start_page"],
                    "end_page": ch["end_page"],
                    "text": chapter_text,
                    "title": title,
                    "book_name": self.book_name,
                }
            )

        return chapter_texts

    def _write_chapters(self, chapters: List[Dict]) -> None:
        """Write processed chapters to vault."""
        # Ensure we write to the correct location: vault_root/100 ARQUIVOS E REFERENCIAS/Livros/book_name
        livros_path = Path(self.vault_path) / "100 ARQUIVOS E REFERENCIAS" / "Livros"
        livros_path.mkdir(parents=True, exist_ok=True)

        writer = VaultWriter(str(livros_path), self.book_name)
        writer.write_all_chapters(chapters)
        logger.info(f"Wrote {len(chapters)} chapters to {livros_path / self.book_name}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Process PDF books for RAG")
    parser.add_argument("--book", required=True, help="Path to PDF file")
    parser.add_argument("--chapters", help="Path to chapters file")
    parser.add_argument("--book-name", required=True, help="Book name")
    parser.add_argument(
        "--vault-path",
        default="/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros",
        help="Vault path",
    )
    parser.add_argument(
        "--no-translation", action="store_true", help="Disable translation"
    )
    parser.add_argument("--target-lang", default="pt-br", help="Target language")
    parser.add_argument(
        "--force-retranslate", action="store_true", help="Force re-translation"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run")

    args = parser.parse_args()

    coordinator = PDFProcessorCoordinator(
        pdf_path=args.book,
        vault_path=args.vault_path,
        book_name=args.book_name,
        chapters_file=args.chapters,
        enable_translation=not args.no_translation,
        target_language=args.target_lang,
        force_retranslate=args.force_retranslate,
    )

    result = coordinator.process(dry_run=args.dry_run)
    print(f"\nProcessing result: {result}")


if __name__ == "__main__":
    main()
