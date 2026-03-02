"""Output pipeline - End-to-end validation and generation."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.output.markdown_generator import MarkdownGenerator
from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OutputPipeline:
    """End-to-end pipeline: Validate → Generate Markdown.

    This pipeline combines the validation (Sprint 04) with
    Markdown generation (Sprint 05) to produce Obsidian-ready
    output files.

    Attributes:
        config: Application settings.
        generator: MarkdownGenerator instance.

    Example:
        >>> pipeline = OutputPipeline()
        >>> stats = pipeline.process_book_chunks(
        ...     book_chunks=[...],
        ...     book_title="Rhythms for Life",
        ...     book_path="/path/to/book.pdf",
        ... )
        >>> print(stats)
    """

    def __init__(self, config: Optional[Settings] = None):
        """Initialize output pipeline.

        Args:
            config: Application settings. If None, uses default.
        """
        self.config = config or Settings()
        self.generator = MarkdownGenerator(
            config=self.config,
            output_dir=str(self.config.output_dir),
        )

        logger.info("OutputPipeline initialized")

    def process_book_chunks(
        self,
        book_chunks: List[Dict[str, Any]],
        book_title: str,
        book_path: str,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process book chunks and generate Markdown.

        Note: This method expects pre-validated chunks from Sprint 04.
        For full validation, use ValidationPipeline separately.

        Args:
            book_chunks: List of book chunks (from Sprint 02).
            book_title: Title of the book.
            book_path: Path to original PDF.
            output_filename: Optional custom output filename.

        Returns:
            Summary statistics including output path and size.

        Example:
            >>> pipeline = OutputPipeline()
            >>> with open("data/processed/book_chunks.json") as f:
            ...     data = json.load(f)
            >>> stats = pipeline.process_book_chunks(
            ...     book_chunks=data["chunks"],
            ...     book_title=data["book_title"],
            ...     book_path=data["book_path"],
            ... )
            >>> print(f"Generated: {stats['output_file']}")
        """
        validated_results = []
        stats: Dict[str, Any] = {
            "total_chunks": len(book_chunks),
            "chunks_with_matches": 0,
            "total_validated_matches": 0,
        }

        for chunk in book_chunks:
            chunk_text = chunk.get("translated_text", chunk.get("text", ""))

            if not chunk_text.strip():
                logger.warning(f"Skipping empty chunk: {chunk.get('chunk_id')}")
                continue

            validated_result = {
                "chunk_id": chunk.get("chunk_id"),
                "chapter_title": chunk.get("chapter_title", "Capítulo Desconhecido"),
                "chunk_text": chunk_text[:500],
                "validated_matches": chunk.get("validated_matches", []),
            }

            validated_results.append(validated_result)

            if validated_result["validated_matches"]:
                stats["chunks_with_matches"] += 1
                stats["total_validated_matches"] += len(
                    validated_result["validated_matches"]
                )

        output_file = self.generator.generate_book_file(
            book_title=book_title,
            book_path=book_path,
            validated_chunks=validated_results,
            output_filename=output_filename,
        )

        stats["output_file"] = str(output_file)
        stats["output_size"] = (
            int(output_file.stat().st_size) if output_file.exists() else 0
        )

        logger.info(
            f"Processed {stats['total_chunks']} chunks, "
            f"{stats['chunks_with_matches']} with matches, "
            f"{stats['total_validated_matches']} total validated"
        )

        return stats

    def process_book_file(
        self,
        chunks_file: str,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process book from chunks JSON file.

        Args:
            chunks_file: Path to chunks JSON file (from Sprint 02).
            output_filename: Optional custom output filename.

        Returns:
            Summary statistics.

        Example:
            >>> pipeline = OutputPipeline()
            >>> stats = pipeline.process_book_file(
            ...     "data/processed/Rhythms_for_Life_chunks.json"
            ... )
        """
        chunks_path = Path(chunks_file)

        if not chunks_path.exists():
            logger.error(f"Chunks file not found: {chunks_file}")
            return {"error": f"File not found: {chunks_file}"}

        with open(chunks_path, "r", encoding="utf-8") as f:
            book_data = json.load(f)

        return self.process_book_chunks(
            book_chunks=book_data.get("chunks", []),
            book_title=book_data.get("book_title", chunks_path.stem),
            book_path=book_data.get("book_path", str(chunks_path)),
            output_filename=output_filename,
        )

    def process_library(
        self,
        library_path: str,
        output_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Process multiple books from a library folder.

        Args:
            library_path: Path to folder with processed chunk JSON files.
            output_dir: Optional output directory.

        Returns:
            List of stats for each book.

        Example:
            >>> pipeline = OutputPipeline()
            >>> results = pipeline.process_library("data/processed/")
        """
        lib_path = Path(library_path)

        if not lib_path.exists():
            logger.error(f"Library path not found: {library_path}")
            return [{"error": f"Path not found: {library_path}"}]

        chunk_files = list(lib_path.glob("*_chunks.json"))

        if not chunk_files:
            logger.warning(f"No chunk files found in: {library_path}")
            return []

        results = []

        for chunks_file in chunk_files:
            logger.info(f"Processing: {chunks_file.name}")

            try:
                stats = self.process_book_file(
                    chunks_file=str(chunks_file),
                    output_filename=None,
                )
                results.append(stats)
                logger.info(f"✅ Processed: {chunks_file.name}")

            except Exception as e:
                logger.error(f"❌ Failed: {chunks_file.name}: {e}")
                results.append(
                    {
                        "file": str(chunks_file),
                        "error": str(e),
                    }
                )

        return results


def main():
    """Main entry point for output pipeline CLI."""
    parser = argparse.ArgumentParser(
        description="Generate Obsidian Markdown from validated book chunks"
    )
    parser.add_argument(
        "--book-chunks",
        type=str,
        help="Path to book chunks JSON file (from Sprint 02)",
    )
    parser.add_argument(
        "--library",
        type=str,
        help="Path to folder with multiple chunk files",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Custom output filename",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Output directory (default: data/processed)",
    )
    parser.add_argument(
        "--import-to-vault",
        action="store_true",
        help="Import generated file to Obsidian vault",
    )

    args = parser.parse_args()

    if not args.book_chunks and not args.library:
        parser.error("Must specify --book-chunks or --library")

    config = Settings()
    if args.output_dir:
        config.output_dir = args.output_dir

    pipeline = OutputPipeline(config)

    if args.book_chunks:
        stats = pipeline.process_book_file(
            chunks_file=args.book_chunks,
            output_filename=args.output,
        )

        print("\n" + "=" * 50)
        print("OUTPUT GENERATION COMPLETE")
        print("=" * 50)
        print(f"Total chunks: {stats.get('total_chunks', 0)}")
        print(f"Chunks with matches: {stats.get('chunks_with_matches', 0)}")
        print(f"Total validated: {stats.get('total_validated_matches', 0)}")
        print(f"Output file: {stats.get('output_file', 'N/A')}")

        if args.import_to_vault and "output_file" in stats:
            import_path = pipeline.generator.import_to_vault(Path(stats["output_file"]))
            print(f"Imported to vault: {import_path}")

    elif args.library:
        results = pipeline.process_library(
            library_path=args.library,
            output_dir=args.output_dir,
        )

        print("\n" + "=" * 50)
        print("LIBRARY PROCESSING COMPLETE")
        print("=" * 50)
        print(f"Books processed: {len(results)}")

        successful = sum(1 for r in results if "error" not in r)
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")


if __name__ == "__main__":
    main()
