"""Vault Indexer - Main script for indexing Obsidian vault into ChromaDB.

This module provides the main entry point for indexing Obsidian vault notes,
including text cleaning, chunking, embedding generation, and storage.

Example:
    # Index entire vault
    poetry run python src/indexing/vault_indexer.py

    # Clean and re-index
    poetry run python src/indexing/vault_indexer.py --clean

    # Index specific folder
    poetry run python src/indexing/vault_indexer.py --folder "Notes/Projetos"

    # Dry run (count only)
    poetry run python src/indexing/vault_indexer.py --dry-run
"""

import argparse
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ollama
from tqdm import tqdm

from src.indexing.chroma_client import ChromaClient
from src.indexing.chunker import chunk_text
from src.indexing.text_cleaner import clean_text, extract_tags, count_tokens
from src.utils.config import Settings
from src.utils.exceptions import IndexingError, EmbeddingError
from src.utils.logging import get_logger, get_skipped_logger

logger = get_logger(__name__)
skipped_logger = get_skipped_logger(Path("./data/logs/skipped_notes.log"))


class VaultIndexer:
    """Index Obsidian vault notes into ChromaDB.

    This class orchestrates the entire indexing pipeline, including:
    - Reading markdown files from the vault
    - Cleaning and preprocessing text
    - Chunking large documents
    - Generating embeddings via Ollama
    - Storing in ChromaDB

    Attributes:
        config: Application settings.
        chroma_client: ChromaDB wrapper client.
        stats: Indexing statistics tracker.
    """

    def __init__(self, config: Settings):
        """Initialize the vault indexer.

        Args:
            config: Application settings containing vault path,
                   ChromaDB config, and Ollama settings.
        """
        self.config = config
        self.chroma_client = ChromaClient(config)
        self.stats: Dict[str, int] = {
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "chunks": 0,
        }

    def _generate_id(self, file_path: str, chunk_id: int) -> str:
        """Generate unique ID for a chunk.

        Args:
            file_path: Path to the source markdown file.
            chunk_id: Chunk identifier within the file.

        Returns:
            MD5 hash as unique document ID.
        """
        content = f"{file_path}_{chunk_id}"
        return hashlib.md5(content.encode()).hexdigest()

    def _embed_text(self, text: str, retries: int = 3) -> List[float]:
        """Generate embedding via Ollama with retry logic.

        Args:
            text: Text to embed.
            retries: Number of retry attempts (default: 3).

        Returns:
            Embedding vector as list of floats.

        Raises:
            EmbeddingError: If all retry attempts fail.
        """
        attempt = 0
        while attempt < retries:
            try:
                response = ollama.embeddings(
                    model=self.config.embedding_model, prompt=text
                )
                return response["embedding"]
            except Exception as e:
                attempt += 1
                if attempt < retries:
                    # Exponential backoff: 5s, 10s, 20s
                    wait_time = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"Embedding attempt {attempt} failed, "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise EmbeddingError(
                        f"Failed to generate embedding after {retries} attempts: {e}"
                    ) from e

    def index_vault(
        self, clean: bool = False, folder: Optional[str] = None, dry_run: bool = False
    ) -> Dict[str, int]:
        """Index all notes in vault.

        Args:
            clean: If True, delete existing collection before indexing.
            folder: Optional subfolder to index (relative to vault path).
            dry_run: If True, count files only without actual indexing.

        Returns:
            Statistics dict with counts of indexed, skipped, and error files.
        """
        # Clean mode: delete existing collection
        if clean:
            logger.info("Clean mode: Deleting existing collection...")
            self.chroma_client.delete_collection()
            self.chroma_client._get_or_create_collection()

        # Get target path
        target_path = self.config.vault_path
        if folder:
            target_path = target_path / folder

        # Find all markdown files
        logger.info(f"Scanning {target_path} for markdown files...")
        notes = list(target_path.glob("**/*.md"))

        # Filter out .obsidian folder and templates
        notes = [
            n
            for n in notes
            if ".obsidian" not in str(n)
            and "templates" not in str(n).lower()
            and not n.name.startswith("_")
        ]

        logger.info(f"Found {len(notes)} notes to process")

        if dry_run:
            logger.info(f"DRY RUN: Would index {len(notes)} notes")
            return {"total": len(notes), "indexed": 0, "skipped": 0, "errors": 0}

        # Reset stats
        self.stats = {"indexed": 0, "skipped": 0, "errors": 0, "chunks": 0}

        # Process each note
        for note_path in tqdm(notes, desc="Indexing notes"):
            try:
                self._index_note(note_path)
                self.stats["indexed"] += 1
            except Exception as e:
                error_msg = f"Failed to index {note_path}: {e}"
                logger.error(error_msg)
                skipped_logger.error(f"{note_path}: {e}")
                self.stats["errors"] += 1

        # Log summary
        logger.info(
            f"Indexing complete: {self.stats['indexed']} indexed, "
            f"{self.stats['skipped']} skipped, {self.stats['errors']} errors, "
            f"{self.stats['chunks']} total chunks"
        )

        return self.stats

    def _index_note(self, note_path: Path) -> None:
        """Index a single note.

        Args:
            note_path: Path to the markdown file.

        Raises:
            IndexingError: If indexing fails.
        """
        try:
            # Read file
            content = note_path.read_text(encoding="utf-8")

            # Clean text
            cleaned = clean_text(content)

            # Skip empty notes
            if not cleaned.strip():
                logger.warning(f"Skipping empty note: {note_path}")
                self.stats["skipped"] += 1
                skipped_logger.info(f"{note_path}: Empty content after cleaning")
                return

            # Extract tags
            tags = extract_tags(content)

            # Chunk text
            chunks = chunk_text(
                cleaned,
                max_tokens=self.config.max_tokens,
                overlap_tokens=self.config.overlap_tokens,
            )

            # Prepare batch data
            documents: List[str] = []
            embeddings: List[List[float]] = []
            metadatas: List[Dict[str, Any]] = []
            ids: List[str] = []

            for chunk_id, chunk in enumerate(chunks):
                doc_id = self._generate_id(str(note_path), chunk_id)

                # Generate embedding
                embedding = self._embed_text(chunk)

                # Prepare metadata
                metadata = {
                    "file_path": str(note_path),
                    "note_title": note_path.stem,
                    "tags": ",".join(tags),
                    "chunk_id": chunk_id,
                    "chunk_count": len(chunks),
                    "token_count": count_tokens(chunk),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                documents.append(chunk)
                embeddings.append(embedding)
                metadatas.append(metadata)
                ids.append(doc_id)

            # Upsert to ChromaDB
            self.chroma_client.upsert_documents(
                ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
            )

            self.stats["chunks"] += len(chunks)

        except Exception as e:
            raise IndexingError(f"Failed to index note {note_path}: {e}") from e

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the current collection.

        Returns:
            Dictionary with collection statistics.
        """
        try:
            count = self.chroma_client.get_collection_count()
            return {
                "document_count": count,
                "collection_name": self.config.collection_name,
                "persist_dir": str(self.config.chroma_persist_dir),
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


def main():
    """Main entry point for the vault indexer CLI."""
    parser = argparse.ArgumentParser(
        description="Index Obsidian vault notes into ChromaDB"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing collection before indexing",
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="Index only a specific folder (relative to vault path)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Count files only, don't actually index"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show collection statistics and exit"
    )

    args = parser.parse_args()

    # Load configuration
    config = Settings()

    # Initialize indexer
    indexer = VaultIndexer(config)

    # Show stats and exit
    if args.stats:
        stats = indexer.get_collection_stats()
        print(f"Collection: {stats.get('collection_name')}")
        print(f"Documents: {stats.get('document_count', 'N/A')}")
        print(f"Storage: {stats.get('persist_dir')}")
        return

    # Run indexing
    logger.info("Starting vault indexing...")
    stats = indexer.index_vault(
        clean=args.clean, folder=args.folder, dry_run=args.dry_run
    )

    # Print summary
    print("\n" + "=" * 50)
    print("INDEXING SUMMARY")
    print("=" * 50)
    for key, value in stats.items():
        print(f"{key.capitalize()}: {value}")


if __name__ == "__main__":
    main()
