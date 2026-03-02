"""Retrieval Pipeline - End-to-end retrieval with re-ranking."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import ollama
from tqdm import tqdm

from src.retrieval.reranker import ReRanker
from src.retrieval.vector_search import VectorSearch
from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RetrievalPipeline:
    """End-to-end retrieval pipeline with 3-stage filtering.

    This class orchestrates the complete retrieval process:
    1. Vector Search (Bi-Encoder): Fast retrieval of Top-20 candidates
    2. Re-Ranking (Cross-Encoder): Precise filtering to Top-5
    3. Output: Validated matches ready for Ollama validation (Sprint 04)

    The 3-stage approach balances speed and accuracy:
    - Stage 1 (Vector): Fast but imprecise (cosine similarity)
    - Stage 2 (Re-Rank): Slower but accurate (cross-attention)
    - Stage 3 (Ollama): Human-like validation (Sprint 04)

    Attributes:
        config: Application settings.
        vector_search: VectorSearch instance for initial retrieval.
        reranker: ReRanker instance for precision filtering.

    Example:
        >>> pipeline = RetrievalPipeline()
        >>> query_text = "antifragility concept"
        >>> query_embedding = [0.1] * 1024  # bge-m3 embedding
        >>> results = pipeline.retrieve(query_text, query_embedding)
        >>> len(results) <= 5
        True
        >>> all(r["rerank_score"] >= 0.75 for r in results)
        True
    """

    def __init__(self, config: Optional[Settings] = None):
        """Initialize retrieval pipeline.

        Args:
            config: Application settings. If None, uses default settings.

        Note:
            First initialization loads the cross-encoder model (~500MB).
            This may take 10-30 seconds depending on hardware.
        """
        self.config = config or Settings()

        logger.info("Initializing retrieval pipeline...")

        # Stage 1: Vector Search (fast, imprecise)
        logger.info("Loading vector search...")
        self.vector_search = VectorSearch(config=self.config)

        # Stage 2: Re-Ranking (slow, precise)
        logger.info("Loading re-ranker (this may take a moment)...")
        start_time = time.time()
        self.reranker = ReRanker(config=self.config)
        load_time = time.time() - start_time
        logger.info(f"Re-ranker loaded in {load_time:.2f}s")

        logger.info("Retrieval pipeline ready")

    def retrieve(
        self,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        n_results_initial: int = 20,
        n_results_final: int = 5,
        generate_embedding: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute full 2-stage retrieval pipeline.

        Args:
            query_text: Book chunk text (for re-ranker).
            query_embedding: bge-m3 embedding (for vector search).
                If None and generate_embedding=True, will generate from query_text.
            n_results_initial: Number of candidates from vector search (default: 20).
            n_results_final: Number of results after re-ranking (default: 5).
            generate_embedding: If True and query_embedding is None, generate embedding.

        Returns:
            List of validated matches with metadata and scores.
            Each result includes:
            - id: Document ID
            - document: Note text
            - metadata: Note metadata (file_path, title, tags, etc.)
            - score: Vector similarity score
            - rerank_score: Cross-encoder relevance score
            - distance: L2 distance from ChromaDB

        Raises:
            Exception: If retrieval fails at any stage.

        Example:
            >>> pipeline = RetrievalPipeline()
            >>> results = pipeline.retrieve(
            ...     query_text="resilience in adversity",
            ...     n_results_initial=20,
            ...     n_results_final=5,
            ... )
            >>> len(results) <= 5
            True
        """
        start_time = time.time()

        # Generate embedding if needed
        if query_embedding is None and generate_embedding:
            logger.info("Generating embedding for query...")
            query_embedding = self._generate_embedding(query_text)

        if query_embedding is None:
            raise ValueError(
                "Must provide query_embedding or set generate_embedding=True"
            )

        # Stage 1: Vector Search (fast, imprecise)
        logger.info(f"Stage 1: Vector Search (Top-{n_results_initial})")
        stage1_start = time.time()

        try:
            candidates = self.vector_search.search(
                query_embedding=query_embedding,
                n_results=n_results_initial,
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

        stage1_time = time.time() - stage1_start
        logger.info(
            f"Stage 1 complete: {len(candidates)} candidates in {stage1_time:.2f}s"
        )

        if not candidates:
            logger.warning("No candidates found in vector search")
            return []

        # Stage 2: Re-Ranking (slow, precise)
        logger.info(
            f"Stage 2: Re-Ranking (Top-{n_results_final}, threshold={self.config.rerank_threshold})"
        )
        stage2_start = time.time()

        try:
            ranked = self.reranker.rerank(
                query=query_text,
                documents=candidates,
                top_k=n_results_final,
            )
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            raise

        stage2_time = time.time() - stage2_start
        total_time = time.time() - start_time

        logger.info(f"Stage 2 complete: {len(ranked)} results in {stage2_time:.2f}s")
        logger.info(f"Total retrieval time: {total_time:.2f}s")

        # Add timing metadata
        for result in ranked:
            result["retrieval_time"] = total_time
            result["stage1_time"] = stage1_time
            result["stage2_time"] = stage2_time

        return ranked

    def retrieve_from_chunk_file(
        self,
        chunk_file: Path,
        n_results_initial: int = 20,
        n_results_final: int = 5,
    ) -> Dict[str, Any]:
        """Process a book chunk file and retrieve matches for all chunks.

        Args:
            chunk_file: Path to JSON file with book chunks (from Sprint 02).
            n_results_initial: Number of candidates per chunk.
            n_results_final: Number of results per chunk.

        Returns:
            Dict with metadata and list of chunk results.

        Example:
            >>> pipeline = RetrievalPipeline()
            >>> results = pipeline.retrieve_from_chunk_file(
            ...     Path("data/processed/book_chunks.json")
            ... )
            >>> len(results["chunks"])
            183
        """
        logger.info(f"Processing chunk file: {chunk_file}")

        # Load chunks
        try:
            with open(chunk_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load chunk file: {e}")
            raise

        chunks = data.get("chunks", [])
        metadata = data.get("metadata", {})

        logger.info(f"Found {len(chunks)} chunks to process")

        # Process each chunk
        chunk_results = []
        for chunk in tqdm(chunks, desc="Processing chunks"):
            chunk_text = chunk.get("text", "")
            if not chunk_text.strip():
                logger.warning(f"Empty chunk {chunk.get('chunk_id')}, skipping")
                continue

            try:
                # Generate embedding
                query_embedding = self._generate_embedding(chunk_text)

                # Retrieve matches
                results = self.retrieve(
                    query_text=chunk_text,
                    query_embedding=query_embedding,
                    n_results_initial=n_results_initial,
                    n_results_final=n_results_final,
                    generate_embedding=False,
                )

                chunk_results.append(
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "chapter_title": chunk.get("chapter_title"),
                        "text": chunk_text[:500] + "..."
                        if len(chunk_text) > 500
                        else chunk_text,
                        "matches": results,
                        "match_count": len(results),
                    }
                )

            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.get('chunk_id')}: {e}")
                chunk_results.append(
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "error": str(e),
                        "matches": [],
                    }
                )

        return {
            "metadata": {
                **metadata,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "total_chunks": len(chunks),
                "chunks_with_matches": sum(
                    1 for c in chunk_results if c.get("matches")
                ),
            },
            "chunks": chunk_results,
        }

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate bge-m3 embedding via Ollama.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (1024 dimensions).
        """
        try:
            response = ollama.embeddings(
                model=self.config.embedding_model,
                prompt=text[:8000],  # Limit text length
            )
            return response["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise


def main():
    """Main entry point for retrieval pipeline CLI."""
    parser = argparse.ArgumentParser(description="Retrieve matching notes from vault")
    parser.add_argument(
        "--query",
        type=str,
        help="Search query string",
    )
    parser.add_argument(
        "--chunk-file",
        type=str,
        help="Path to book chunks JSON file (from Sprint 02)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "--initial-k",
        type=int,
        default=20,
        help="Number of initial candidates (default: 20)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Re-rank threshold (default: 0.75)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (JSON)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show results without saving",
    )

    args = parser.parse_args()

    if not args.query and not args.chunk_file:
        parser.error("Must specify --query or --chunk-file")

    # Initialize pipeline
    logger.info("Initializing retrieval pipeline...")
    pipeline = RetrievalPipeline()

    # Show collection stats
    stats = pipeline.vector_search.get_collection_stats()
    print(f"\nCollection: {stats.get('collection_name')}")
    print(f"Documents: {stats.get('document_count')}")
    print(f"Model: {stats.get('embedding_model')}")
    print()

    # Execute retrieval
    if args.query:
        logger.info(f"Processing query: {args.query}")
        # Override threshold if provided
        if args.threshold:
            pipeline.reranker.threshold = args.threshold
            pipeline.config.rerank_threshold = args.threshold
        results = pipeline.retrieve(
            query_text=args.query,
            n_results_initial=args.initial_k,
            n_results_final=args.top_k,
        )

        print(f"\nQuery: {args.query}")
        print(f"Found {len(results)} matches")
        print()

        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Score: {result['rerank_score']:.4f}")
            print(f"Title: {result['metadata'].get('note_title', 'Unknown')}")
            print(f"File: {result['metadata'].get('file_path', 'Unknown')}")
            print(f"Text: {result['document'][:200]}...")

    elif args.chunk_file:
        chunk_path = Path(args.chunk_file)
        if not chunk_path.exists():
            parser.error(f"Chunk file not found: {chunk_path}")

        results = pipeline.retrieve_from_chunk_file(
            chunk_file=chunk_path,
            n_results_initial=args.initial_k,
            n_results_final=args.top_k,
        )

        print(f"\nProcessed {results['metadata']['total_chunks']} chunks")
        print(f"Chunks with matches: {results['metadata']['chunks_with_matches']}")

        # Save results
        if not args.dry_run:
            output_path = (
                args.output
                or f"data/processed/retrieval_results_{int(time.time())}.json"
            )
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
