"""Validation Pipeline - End-to-end validation orchestration."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import ollama
from tqdm import tqdm

from src.retrieval.pipeline import RetrievalPipeline
from src.validation.ollama_validator import OllamaValidator
from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def deduplicate_candidates(candidates: List[Dict], max_unique: int = 10) -> List[Dict]:
    """Remove duplicate notes from candidate list.

    Args:
        candidates: List of retrieved candidates (may have same note multiple times)
        max_unique: Maximum number of unique notes to return

    Returns:
        List of candidates with unique note titles only
    """
    seen_notes = set()
    unique_candidates = []

    for candidate in candidates:
        note_title = candidate.get("metadata", {}).get("note_title", "")
        file_path = candidate.get("metadata", {}).get("file_path", "")

        note_id = file_path if file_path else note_title

        if note_id not in seen_notes:
            seen_notes.add(note_id)
            unique_candidates.append(candidate)

            if len(unique_candidates) >= max_unique:
                break

    if len(candidates) > len(unique_candidates):
        logger.info(
            f"🔄 Deduplicated: {len(candidates)} → {len(unique_candidates)} unique notes"
        )

    return unique_candidates


class ValidationPipeline:
    """End-to-end validation pipeline: Retrieve → Re-Rank → Validate.

    This class orchestrates the complete validation flow:
    1. Retrieval (Sprint 03): Vector Search + Re-Ranking
    2. Validation (Sprint 04): Ollama semantic validation

    The pipeline processes book chunks and returns only validated matches
    that are approved by the LLM (approved == true).

    For Sprint 06, it also supports chapter-based validation where
    the entire chapter text is validated against the vault to find
    top matches for the whole chapter instead of individual chunks.

    Attributes:
        config: Application settings.
        retrieval: RetrievalPipeline instance (Sprint 03).
        validator: OllamaValidator instance (Sprint 04).

    Example:
        >>> pipeline = ValidationPipeline()
        >>> result = pipeline.process_chunk(
        ...     chunk_text="antifragility concept",
        ...     chunk_embedding=[0.1] * 1024,
        ... )
        >>> result["matches_validated"]
        2
    """

    def __init__(self, config: Optional[Settings] = None):
        """Initialize validation pipeline.

        Args:
            config: Application settings. If None, uses default.
        """
        self.config = config or Settings()

        logger.info("Initializing validation pipeline...")

        # Stage 1-2: Retrieval + Re-Ranking (Sprint 03)
        logger.info("Loading retrieval pipeline (Sprint 03)...")
        self.retrieval = RetrievalPipeline(self.config)

        # Stage 3: Ollama Validation (Sprint 04)
        logger.info("Loading Ollama validator (Sprint 04)...")
        self.validator = OllamaValidator(self.config)

        logger.info("Validation pipeline ready")

    def process_chunk(
        self,
        chunk_text: str,
        chunk_embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Process a single book chunk through full validation pipeline.

        Args:
            chunk_text: Book chunk text (for re-ranker + Ollama).
            chunk_embedding: bge-m3 embedding. If None, generates from chunk_text.

        Returns:
            Dict with:
            - chunk_text: Input text (truncated)
            - candidates_retrieved: Number from vector search
            - candidates_reranked: Number after re-ranking
            - matches_validated: Number of approved matches
            - validated_matches: List of approved matches with validation metadata

        Example:
            >>> pipeline = ValidationPipeline()
            >>> result = pipeline.process_chunk("test chunk")
            >>> "validated_matches" in result
            True
        """
        # Generate embedding if not provided
        if chunk_embedding is None:
            logger.info(
                f"🤖 Calling Ollama ({self.config.embedding_model}) for embedding..."
            )
            response = ollama.embeddings(
                model=self.config.embedding_model,
                prompt=chunk_text[:8000],
            )
            chunk_embedding = response["embedding"]
            logger.info(f"✅ Embedding generated: {len(chunk_embedding)} dimensions")

        # Stage 1-2: Retrieval + Re-Ranking (Sprint 03)
        logger.info("🗄️ Querying ChromaDB for candidates...")
        candidates = self.retrieval.retrieve(
            query_text=chunk_text,
            query_embedding=chunk_embedding,
            n_results_initial=self.config.vector_search_top_k,
            n_results_final=self.config.rerank_top_k,
            generate_embedding=False,
        )

        # Deduplicate candidates before validation
        unique_candidates = deduplicate_candidates(candidates, max_unique=10)

        logger.info(f"🔄 Re-ranking {len(unique_candidates)} unique candidates...")

        # Stage 3: Ollama Validation (Sprint 04)
        logger.info(
            f"🤖 Calling Ollama ({self.config.validation_model}) for validation of {len(unique_candidates)} candidates..."
        )
        validated = self.validator.validate_batch(
            book_chunk=chunk_text,
            candidates=unique_candidates,
        )
        logger.info(f"✅ Validation complete: {len(validated)} matches approved")

        return {
            "chunk_text": chunk_text[:500] + "..."
            if len(chunk_text) > 500
            else chunk_text,
            "candidates_retrieved": self.config.vector_search_top_k,
            "candidates_reranked": len(unique_candidates),
            "unique_candidates": len(unique_candidates),
            "matches_validated": len(validated),
            "validated_matches": validated,
        }

    def process_chapter(
        self,
        chapter_text: str,
        chapter_num: int,
        chapter_title: str = "",
        chapter_pages: str = "",
    ) -> Dict[str, Any]:
        """Process an entire chapter through validation pipeline to find top matches.

        Args:
            chapter_text: Full chapter text to validate against vault
            chapter_num: Chapter number for tracking
            chapter_title: Title of the chapter
            chapter_pages: Page range of the chapter

        Returns:
            Dict with:
            - chapter_info: Information about the chapter
            - candidates_retrieved: Number from vector search
            - candidates_reranked: Number after re-ranking
            - matches_validated: Number of approved matches (top-k)
            - validated_matches: List of top-k approved matches with validation metadata
        """
        logger.info(
            f"Processing chapter {chapter_num}: {chapter_title or f'Chapter {chapter_num}'}"
        )

        # Stage 1-2: Retrieval + Re-Ranking (Sprint 03)
        logger.debug("Running retrieval (Sprint 03)...")
        candidates = self.retrieval.retrieve(
            query_text=chapter_text,
            query_embedding=None,  # Will be generated internally
            n_results_initial=self.config.vector_search_top_k,
            n_results_final=self.config.chapter_validation_top_k,  # Use chapter-specific top-k
            generate_embedding=True,
        )

        # Deduplicate candidates before validation
        unique_candidates = deduplicate_candidates(candidates, max_unique=10)

        # Stage 3: Ollama Validation (Sprint 04)
        logger.debug(
            f"Validating {len(unique_candidates)} unique candidates with Ollama..."
        )
        validated = self.validator.validate_batch(
            book_chunk=chapter_text,
            candidates=unique_candidates,
        )

        # Filter to only get the top-k validated matches as specified by config
        validated_matches = sorted(
            validated, key=lambda x: x["rerank_score"], reverse=True
        )
        top_validated = validated_matches[: self.config.chapter_validation_top_k]

        return {
            "chapter_info": {
                "chapter_num": chapter_num,
                "chapter_title": chapter_title or f"Chapter {chapter_num}",
                "chapter_pages": chapter_pages,
            },
            "candidates_retrieved": self.config.vector_search_top_k,
            "candidates_reranked": len(candidates),
            "matches_validated": len(top_validated),
            "validated_matches": top_validated,
        }

    def process_book(
        self,
        book_chunks: List[Dict[str, Any]],
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Process all chunks from a book.

        Args:
            book_chunks: List of chunks from Sprint 02.
                Each should have "text" or "translated_text" key.
            output_path: Path to save validation results JSON.
                If None, results are not saved.

        Returns:
            Summary statistics including:
            - total_chunks: Total chunks processed
            - chunks_with_matches: Chunks with at least one approved match
            - total_validated_matches: Total approved matches
            - total_candidates: Total candidates evaluated

        Example:
            >>> pipeline = ValidationPipeline()
            >>> chunks = [{"text": "chapter 1"}, {"text": "chapter 2"}]
            >>> stats = pipeline.process_book(chunks)
            >>> stats["total_chunks"]
            2
        """
        logger.info(f"Processing {len(book_chunks)} book chunks...")

        results = []
        stats = {
            "total_chunks": len(book_chunks),
            "chunks_with_matches": 0,
            "total_validated_matches": 0,
            "total_candidates": 0,
        }

        start_time = time.time()

        for chunk in tqdm(book_chunks, desc="Validating chunks"):
            chunk_text = chunk.get("translated_text", chunk.get("text", ""))

            if not chunk_text.strip():
                logger.warning(f"Empty chunk {chunk.get('chunk_id')}, skipping")
                continue

            try:
                result = self.process_chunk(chunk_text=chunk_text)

                results.append(
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "chapter_title": chunk.get("chapter_title"),
                        **result,
                    }
                )

                stats["total_candidates"] += result["candidates_reranked"]
                stats["total_validated_matches"] += result["matches_validated"]
                if result["matches_validated"] > 0:
                    stats["chunks_with_matches"] += 1

            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.get('chunk_id')}: {e}")
                results.append(
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "error": str(e),
                        "validated_matches": [],
                    }
                )

        elapsed_time = time.time() - start_time

        output_data = {
            "metadata": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "total_chunks": len(book_chunks),
                "elapsed_time_seconds": elapsed_time,
                "retrieval_model": self.config.embedding_model,
                "validation_model": self.config.validation_model,
                "rerank_threshold": self.config.rerank_threshold,
            },
            "stats": stats,
            "results": results,
        }

        # Save results if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Results saved to: {output_path}")

        logger.info(
            f"Validation complete: {stats['total_validated_matches']} matches "
            f"from {stats['chunks_with_matches']}/{stats['total_chunks']} chunks "
            f"in {elapsed_time:.1f}s"
        )

        return stats


def main():
    """Main entry point for validation pipeline CLI."""
    parser = argparse.ArgumentParser(
        description="Validate book-to-note matches with Ollama"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to validate",
    )
    parser.add_argument(
        "--book-chunks",
        type=str,
        help="Path to book chunks JSON (from Sprint 02)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON path for validation results",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show candidates without calling Ollama",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Override validation model",
    )

    args = parser.parse_args()

    if not args.query and not args.book_chunks:
        parser.error("Must specify --query or --book-chunks")

    # Initialize pipeline
    logger.info("Initializing validation pipeline...")
    pipeline = ValidationPipeline()

    if args.query:
        # Single query
        result = pipeline.process_chunk(chunk_text=args.query)

        print(f"\n📖 Chunk: {result['chunk_text'][:100]}...")
        print(f"🔍 Candidates: {result['candidates_reranked']}")
        print(f"✅ Validated: {result['matches_validated']}")

        for match in result["validated_matches"]:
            print(f"\n--- Match ---")
            print(f"Title: {match['metadata'].get('note_title', 'Unknown')}")
            print(f"Score: {match['rerank_score']:.3f}")
            print(f"Approved: {match['validation']['approved']}")
            print(f"Confidence: {match['validation']['confidence']}%")
            print(f"Reason: {match['validation']['reason'][:100]}...")

    elif args.book_chunks:
        # Load book chunks
        chunk_path = Path(args.book_chunks)
        if not chunk_path.exists():
            parser.error(f"Chunk file not found: {chunk_path}")

        with open(chunk_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chunks = data.get("chunks", [])

        # Process
        output_path = Path(args.output) if args.output else None
        stats = pipeline.process_book(book_chunks=chunks, output_path=output_path)

        print(f"\n📊 Validation Summary:")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Chunks with matches: {stats['chunks_with_matches']}")
        print(f"Total validated matches: {stats['total_validated_matches']}")
        print(f"Total candidates: {stats['total_candidates']}")


if __name__ == "__main__":
    main()
