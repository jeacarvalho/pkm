"""ChromaDB client wrapper for Obsidian RAG."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api.models.Collection import Collection

from src.utils.config import Settings
from src.utils.exceptions import ChromaDBError


class ChromaClient:
    """Wrapper for ChromaDB operations.

    This class provides a simplified interface for interacting with ChromaDB,
    handling collection management, document storage, and retrieval.

    Attributes:
        settings: Application settings.
        client: ChromaDB persistent client instance.
        collection: Active collection for obsidian notes.
    """

    def __init__(self, settings: Settings):
        """Initialize ChromaDB client.

        Args:
            settings: Application settings containing ChromaDB configuration.
        """
        self.settings = settings
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection: Optional[Collection] = None

        self._init_client()
        self._get_or_create_collection()

    def _init_client(self) -> None:
        """Initialize ChromaDB persistent client."""
        try:
            # Ensure persist directory exists
            self.settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=str(self.settings.chroma_persist_dir)
            )
        except Exception as e:
            raise ChromaDBError(f"Failed to initialize ChromaDB client: {e}") from e

    def _get_or_create_collection(self) -> None:
        """Get or create the obsidian_notes collection."""
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.settings.collection_name,
                metadata={
                    "description": "Obsidian vault notes embeddings",
                    "embedding_model": self.settings.embedding_model,
                    "dimensions": str(self.settings.embedding_dimensions),
                },
            )
        except Exception as e:
            raise ChromaDBError(f"Failed to get/create collection: {e}") from e

    def delete_collection(self) -> None:
        """Delete the obsidian_notes collection.

        This removes all documents and metadata from the collection.
        """
        try:
            self.client.delete_collection(self.settings.collection_name)
            self.collection = None
        except Exception as e:
            raise ChromaDBError(f"Failed to delete collection: {e}") from e

    def upsert_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Upsert documents into the collection.

        This operation will insert new documents or update existing ones
        based on the IDs.

        Args:
            ids: Unique document IDs.
            documents: Text content of documents.
            embeddings: Embedding vectors for documents.
            metadatas: Metadata for each document.

        Raises:
            ChromaDBError: If upsert fails.
        """
        try:
            self.collection.upsert(
                ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
            )
        except Exception as e:
            raise ChromaDBError(f"Failed to upsert documents: {e}") from e

    def query(
        self,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query the collection for similar documents.

        Args:
            query_embeddings: Query embedding vectors (optional if query_texts provided).
            query_texts: Query text strings (optional if query_embeddings provided).
            n_results: Number of results to return.
            where: Metadata filter conditions.
            where_document: Document content filter conditions.

        Returns:
            Query results containing documents, distances, and metadata.

        Raises:
            ChromaDBError: If query fails.
        """
        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document,
            )
            return results
        except Exception as e:
            raise ChromaDBError(f"Failed to query collection: {e}") from e

    def get_collection_count(self) -> int:
        """Get the number of documents in the collection.

        Returns:
            Number of documents in the collection.
        """
        try:
            return self.collection.count()
        except Exception as e:
            raise ChromaDBError(f"Failed to get collection count: {e}") from e

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID.

        Args:
            doc_id: Document ID to retrieve.

        Returns:
            Document data or None if not found.
        """
        try:
            result = self.collection.get(ids=[doc_id])
            if result and result.get("ids") and len(result["ids"]) > 0:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result["documents"] else None,
                    "metadata": result["metadatas"][0] if result["metadatas"] else None,
                    "embedding": result["embeddings"][0]
                    if result.get("embeddings")
                    else None,
                }
            return None
        except Exception:
            return None

    @staticmethod
    def generate_id(file_path: str, chunk_id: int) -> str:
        """Generate a unique ID for a document chunk.

        Args:
            file_path: Path to the source file.
            chunk_id: Chunk identifier within the file.

        Returns:
            MD5 hash as unique document ID.
        """
        content = f"{file_path}_{chunk_id}"
        return hashlib.md5(content.encode()).hexdigest()
