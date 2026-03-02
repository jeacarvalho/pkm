"""Re-ranking utilities using cross-encoder for precision filtering."""

from typing import Dict, List, Optional

import numpy as np
from sentence_transformers import CrossEncoder

from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ReRanker:
    """Re-rank search results using cross-encoder for precision filtering.

    This class uses a cross-encoder model (bge-reranker-v2-m3) to compute
    semantic relevance between queries and documents, filtering out false
    positives from initial vector search.

    The cross-encoder is slower but more accurate than bi-encoders,
    making it ideal for the final filtering stage (3-stage pipeline).

    Attributes:
        model: CrossEncoder model instance.
        threshold: Minimum score to retain a document (default: 0.75).
        model_name: Name of the cross-encoder model.

    Example:
        >>> reranker = ReRanker()
        >>> query = "antifragility concept"
        >>> docs = [{"document": "relevant text"}, {"document": "irrelevant"}]
        >>> results = reranker.rerank(query, docs, top_k=5)
        >>> all(r["rerank_score"] >= 0.75 for r in results)
        True
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        threshold: Optional[float] = None,
        config: Optional[Settings] = None,
    ):
        """Initialize re-ranker with cross-encoder model.

        Args:
            model_name: Cross-encoder model name. If None, uses config.
            threshold: Minimum score to retain. If None, uses config.
            config: Application settings.

        Note:
            First initialization downloads the model (~500MB).
            Subsequent loads use cached model.
        """
        self.config = config or Settings()
        self.model_name = model_name or self.config.rerank_model
        self.threshold = threshold or self.config.rerank_threshold

        logger.info(f"Loading cross-encoder: {self.model_name}")
        try:
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder: {e}")
            raise

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, any]],
        top_k: int = 5,
    ) -> List[Dict[str, any]]:
        """Re-rank documents by semantic relevance to query.

        Args:
            query: The search query (book chunk text).
            documents: List of documents from vector search. Each dict must
                have a "document" key with text content.
            top_k: Number of results to return after re-ranking.

        Returns:
            List of re-ranked documents with "rerank_score" added.
            Documents with score < threshold are filtered out.
            Results sorted by score descending.

        Raises:
            ValueError: If documents is empty.

        Example:
            >>> reranker = ReRanker()
            >>> query = "resilience in adversity"
            >>> docs = [{"document": "Note about antifragility"}]
            >>> results = reranker.rerank(query, docs)
            >>> results[0]["rerank_score"] >= 0.75
            True
        """
        if not documents:
            logger.warning("No documents to re-rank")
            return []

        # Prepare pairs for cross-encoder
        pairs = []
        for doc in documents:
            if "document" not in doc:
                logger.warning("Document missing 'document' key, skipping")
                continue
            pairs.append([query, doc["document"]])

        if not pairs:
            logger.warning("No valid document pairs to score")
            return []

        logger.debug(f"Scoring {len(pairs)} document pairs")

        # Get similarity scores from cross-encoder
        try:
            scores = self.model.predict(pairs, show_progress_bar=False)
        except Exception as e:
            logger.error(f"Cross-encoder prediction failed: {e}")
            raise

        # Attach scores to documents
        valid_docs = []
        score_idx = 0
        for doc in documents:
            if "document" not in doc:
                continue

            doc_copy = doc.copy()
            doc_copy["rerank_score"] = float(scores[score_idx])
            score_idx += 1
            valid_docs.append(doc_copy)

        logger.debug(f"Scored {len(valid_docs)} documents")

        # Filter by threshold
        filtered = [d for d in valid_docs if d["rerank_score"] >= self.threshold]
        logger.info(
            f"Filtered {len(valid_docs) - len(filtered)} documents "
            f"below threshold {self.threshold}"
        )

        if not filtered:
            logger.warning("All documents filtered out by threshold")
            return []

        # Sort by score descending (highest first)
        ranked = sorted(filtered, key=lambda x: x["rerank_score"], reverse=True)

        # Take top_k
        final_results = ranked[:top_k]
        logger.info(f"Returning top {len(final_results)} results")

        return final_results

    def score_single(self, query: str, document: str) -> float:
        """Score a single query-document pair.

        Args:
            query: Search query text.
            document: Document text.

        Returns:
            Similarity score (0.0-1.0).

        Example:
            >>> reranker = ReRanker()
            >>> score = reranker.score_single("antifragility", "Nassim Taleb book")
            >>> 0.0 <= score <= 1.0
            True
        """
        try:
            score = self.model.predict([[query, document]], show_progress_bar=False)
            return float(score[0])
        except Exception as e:
            logger.error(f"Single scoring failed: {e}")
            return 0.0

    def batch_rerank(
        self,
        queries: List[str],
        documents_list: List[List[Dict[str, any]]],
        top_k: int = 5,
    ) -> List[List[Dict[str, any]]]:
        """Re-rank multiple queries in batch.

        Args:
            queries: List of query strings.
            documents_list: List of document lists (one per query).
            top_k: Number of results per query.

        Returns:
            List of re-ranked result lists (one per query).

        Example:
            >>> reranker = ReRanker()
            >>> queries = ["q1", "q2"]
            >>> docs = [[{"document": "d1"}], [{"document": "d2"}]]
            >>> results = reranker.batch_rerank(queries, docs)
            >>> len(results) == 2
            True
        """
        if len(queries) != len(documents_list):
            raise ValueError(
                f"Mismatched lengths: {len(queries)} queries vs "
                f"{len(documents_list)} document lists"
            )

        results = []
        for query, docs in zip(queries, documents_list):
            ranked = self.rerank(query, docs, top_k=top_k)
            results.append(ranked)

        return results


class HybridReRanker(ReRanker):
    """Hybrid re-ranking with additional heuristics.

    Extends base ReRanker with additional filtering:
    - Keyword overlap bonus
    - Metadata matching
    - Length-based penalties
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        threshold: Optional[float] = None,
        config: Optional[Settings] = None,
        keyword_weight: float = 0.1,
        length_penalty: float = 0.0,
    ):
        """Initialize hybrid re-ranker.

        Args:
            model_name: Cross-encoder model name.
            threshold: Minimum score to retain.
            config: Application settings.
            keyword_weight: Weight for keyword overlap bonus (0.0-0.5).
            length_penalty: Penalty for very long/short documents.
        """
        super().__init__(model_name, threshold, config)
        self.keyword_weight = keyword_weight
        self.length_penalty = length_penalty

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, any]],
        top_k: int = 5,
    ) -> List[Dict[str, any]]:
        """Re-rank with hybrid scoring.

        Combines cross-encoder score with:
        - Keyword overlap bonus
        - Length-based adjustments
        """
        # Get base scores from parent class
        results = super().rerank(query, documents, top_k=len(documents))

        if not results:
            return []

        # Apply hybrid scoring
        query_words = set(query.lower().split())

        for doc in results:
            doc_text = doc.get("document", "").lower()
            doc_words = set(doc_text.split())

            # Keyword overlap bonus
            overlap = len(query_words & doc_words)
            keyword_bonus = (overlap / max(len(query_words), 1)) * self.keyword_weight

            # Length penalty (optional)
            word_count = len(doc_text.split())
            length_factor = 1.0
            if self.length_penalty > 0:
                if word_count < 50:
                    length_factor -= self.length_penalty  # Too short
                elif word_count > 1000:
                    length_factor -= self.length_penalty  # Too long

            # Combine scores
            base_score = doc["rerank_score"]
            doc["hybrid_score"] = (base_score + keyword_bonus) * length_factor
            doc["keyword_bonus"] = keyword_bonus

        # Re-sort by hybrid score
        results.sort(
            key=lambda x: x.get("hybrid_score", x["rerank_score"]), reverse=True
        )

        # Filter by original threshold
        filtered = [d for d in results if d["rerank_score"] >= self.threshold]

        return filtered[:top_k]
