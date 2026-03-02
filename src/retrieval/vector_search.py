"""Vector search utilities for semantic retrieval."""

from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api.models.Collection import Collection

from src.utils.config import Settings
from src.utils.exceptions import ChromaDBError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VectorSearch:
    """Search vault notes by semantic similarity using ChromaDB.

    This class provides vector similarity search against the obsidian_notes
    collection in ChromaDB, returning candidates for re-ranking.

    Attributes:
        collection: ChromaDB collection instance.
        collection_name: Name of the ChromaDB collection.
    """

    def __init__(
        self,
        chroma_client: Optional[chromadb.PersistentClient] = None,
        collection_name: str = "obsidian_notes",
        config: Optional[Settings] = None,
    ):
        """Initialize vector search.

        Args:
            chroma_client: Pre-initialized ChromaDB client. If None, creates new.
            collection_name: Name of the collection to search.
            config: Application settings.
        """
        self.collection_name = collection_name
        self.config = config or Settings()

        if chroma_client:
            self.client = chroma_client
        else:
            self.client = chromadb.PersistentClient(
                path=str(self.config.chroma_persist_dir)
            )

        self.collection = self._get_collection()

    def _get_collection(self) -> Collection:
        """Get or create the ChromaDB collection."""
        try:
            return self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Obsidian vault notes embeddings",
                    "embedding_model": self.config.embedding_model,
                },
            )
        except Exception as e:
            raise ChromaDBError(f"Failed to get collection: {e}") from e

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar notes using vector similarity.

        Args:
            query_embedding: bge-m3 embedding (1024 dimensions).
            n_results: Number of results to return (default: 20).
            filter_metadata: Optional metadata filters (e.g., {"tags": {"$contains": "tag"}}).

        Returns:
            List of dicts with: id, document, metadata, distance, score.

        Raises:
            ChromaDBError: If search fails.

        Example:
            >>> search = VectorSearch()
            >>> embedding = [0.1] * 1024  # Mock bge-m3 embedding
            >>> results = search.search(embedding, n_results=10)
            >>> len(results) <= 10
            True
        """
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            return self._format_results(results)

        except Exception as e:
            raise ChromaDBError(f"Search failed: {e}") from e

    def _format_results(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format ChromaDB results into standardized dicts.

        Args:
            raw_results: Raw results from ChromaDB query.

        Returns:
            List of formatted result dicts.
        """
        formatted = []

        if not raw_results or not raw_results.get("ids"):
            return formatted

        # Extract lists from results
        ids = raw_results["ids"][0] if raw_results["ids"] else []
        documents = raw_results["documents"][0] if raw_results.get("documents") else []
        metadatas = raw_results["metadatas"][0] if raw_results.get("metadatas") else []
        distances = raw_results["distances"][0] if raw_results.get("distances") else []

        # Build formatted results
        for i, doc_id in enumerate(ids):
            # Convert distance to similarity score (ChromaDB returns L2 distance)
            # Lower distance = higher similarity
            distance = distances[i] if i < len(distances) else float("inf")
            # Normalize score to 0-1 range (approximate)
            score = max(0.0, min(1.0, 1.0 / (1.0 + distance)))

            formatted.append(
                {
                    "id": doc_id,
                    "document": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distance,
                    "score": score,
                }
            )

        return formatted

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.

        Returns:
            Dict with collection statistics.
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": self.config.embedding_model,
                "embedding_dimensions": self.config.embedding_dimensions,
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


class MultiCollectionSearch(VectorSearch):
    """Search across multiple ChromaDB collections.

    This class extends VectorSearch to query multiple collections
    (e.g., obsidian_notes + processed_book_chunks) and combine results.
    """

    def __init__(
        self,
        collection_names: List[str],
        config: Optional[Settings] = None,
    ):
        """Initialize multi-collection search.

        Args:
            collection_names: List of collection names to search.
            config: Application settings.
        """
        self.config = config or Settings()
        self.client = chromadb.PersistentClient(
            path=str(self.config.chroma_persist_dir)
        )
        self.collection_names = collection_names
        self.collections = {
            name: self.client.get_or_create_collection(name)
            for name in collection_names
        }

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all collections.

        Args:
            query_embedding: bge-m3 embedding (1024 dimensions).
            n_results: Number of results per collection.
            filter_metadata: Optional metadata filters.

        Returns:
            Dict mapping collection name to list of results.
        """
        results_by_collection = {}

        for name, collection in self.collections.items():
            try:
                raw_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=filter_metadata,
                    include=["documents", "metadatas", "distances"],
                )

                formatted = self._format_results(raw_results)
                results_by_collection[name] = formatted

                logger.debug(f"Found {len(formatted)} results in {name}")

            except Exception as e:
                logger.error(f"Failed to search collection {name}: {e}")
                results_by_collection[name] = []

        return results_by_collection

    def search_combined(
        self,
        query_embedding: List[float],
        n_results: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search across all collections and combine results.

        Args:
            query_embedding: bge-m3 embedding (1024 dimensions).
            n_results: Total number of results to return.
            filter_metadata: Optional metadata filters.

        Returns:
            Combined list of results from all collections.
        """
        results_by_collection = self.search(query_embedding, n_results, filter_metadata)

        # Combine all results
        combined = []
        for collection_name, results in results_by_collection.items():
            for result in results:
                result["collection"] = collection_name
                combined.append(result)

        # Sort by score (descending)
        combined.sort(key=lambda x: x["score"], reverse=True)

        return combined[:n_results]
