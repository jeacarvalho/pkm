"""Incremental indexer for Obsidian vault.

This module provides incremental indexing capabilities, detecting only
new, modified, or deleted notes since the last run.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import ollama

from src.indexing.chroma_client import ChromaClient
from src.indexing.chunker import chunk_text
from src.indexing.text_cleaner import clean_text
from src.utils.config import Settings
from src.utils.exceptions import EmbeddingError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IncrementalIndexer:
    """Index only new or modified notes since last run."""

    def __init__(
        self, config: Settings, state_file: str = "data/state/vault_state.json"
    ):
        """Initialize incremental indexer.

        Args:
            config: Application settings.
            state_file: Path to state file for tracking changes.
        """
        self.config = config
        self.state_file = Path(state_file)
        self.chroma_client = ChromaClient(config)

    def load_previous_state(self) -> Dict:
        """Load previous vault state (file hashes)."""
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"files": {}, "last_scan": None}

    def save_current_state(self, state: Dict):
        """Save current vault state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        try:
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Error hashing {file_path}: {e}")
            return ""

    def detect_changes(self) -> Dict:
        """Detect new, modified, and deleted notes."""
        previous_state = self.load_previous_state()
        previous_files = previous_state.get("files", {})

        # Scan current vault
        current_files = {}

        vault_path = Path(self.config.vault_path)
        for md_file in vault_path.rglob("*.md"):
            if ".obsidian" in str(md_file):
                continue

            file_path_str = str(md_file)
            file_hash = self.get_file_hash(md_file)

            current_files[file_path_str] = {
                "hash": file_hash,
                "mtime": md_file.stat().st_mtime,
            }

        # Detect new and modified
        new_files = []
        modified_files = []

        for file_path, file_info in current_files.items():
            if file_path not in previous_files:
                new_files.append(file_path)
            elif file_info["hash"] != previous_files[file_path]["hash"]:
                modified_files.append(file_path)

        # Detect deleted
        deleted_files = []
        for file_path in previous_files:
            if file_path not in current_files:
                deleted_files.append(file_path)

        # Save current state
        new_state = {
            "files": current_files,
            "last_scan": datetime.now(timezone.utc).isoformat(),
        }
        self.save_current_state(new_state)

        return {
            "new": new_files,
            "modified": modified_files,
            "deleted": deleted_files,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_id(self, file_path: str, chunk_id: int) -> str:
        """Generate unique ID for a chunk."""
        content = f"{file_path}_{chunk_id}"
        return hashlib.md5(content.encode()).hexdigest()

    def _embed_text(self, text: str, retries: int = 3) -> List[float]:
        """Generate embedding via Ollama with retry logic."""
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
                    wait_time = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"Embedding attempt {attempt} failed, "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise EmbeddingError(f"Failed to generate embedding: {e}") from e
        # This line is unreachable but satisfies type checker
        raise EmbeddingError("Failed to generate embedding after all retries")

    def index_new_note(self, file_path: str) -> Dict:
        """Index a single new or modified note."""
        try:
            note_path = Path(file_path)
            content = note_path.read_text(encoding="utf-8")
            cleaned = clean_text(content)
            chunks = chunk_text(cleaned, max_tokens=800, overlap_tokens=100)

            documents = []
            embeddings = []
            metadatas = []
            ids = []

            for chunk_id, chunk in enumerate(chunks):
                doc_id = self._generate_id(file_path, chunk_id)
                embedding = self._embed_text(chunk)

                documents.append(chunk)
                embeddings.append(embedding)
                metadatas.append(
                    {
                        "file_path": file_path,
                        "note_title": note_path.stem,
                        "chunk_id": chunk_id,
                        "token_count": len(chunk.split()),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                ids.append(doc_id)

            self.chroma_client.upsert_documents(
                ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
            )

            return {
                "status": "success",
                "file": file_path,
                "chunks_indexed": len(chunks),
            }
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            return {"status": "error", "file": file_path, "error": str(e)}

    def remove_deleted_notes(self, deleted_files: List[str]) -> Dict:
        """Remove deleted notes from ChromaDB."""
        removed_count = 0
        errors = []

        for file_path in deleted_files:
            try:
                count = self.chroma_client.delete_by_file_path(file_path)
                removed_count += count
                if count > 0:
                    logger.info(f"🗑️ Removed {count} chunks for {file_path}")
            except Exception as e:
                error_msg = f"Error removing {file_path}: {e}"
                logger.error(error_msg)
                errors.append({"file": file_path, "error": str(e)})

        return {
            "status": "complete",
            "chunks_removed": removed_count,
            "files_processed": len(deleted_files),
            "errors": errors,
        }
