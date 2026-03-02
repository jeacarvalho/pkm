"""Unit tests for retrieval module."""

import pytest
from unittest.mock import Mock, patch

from src.retrieval.vector_search import VectorSearch


class TestVectorSearch:
    """Test vector search functionality."""

    @pytest.fixture
    def mock_collection(self):
        """Create mock ChromaDB collection."""
        collection = Mock()
        collection.query.return_value = {
            "ids": [["doc1", "doc2", "doc3"]],
            "documents": [["text1", "text2", "text3"]],
            "metadatas": [
                [{"title": "Note 1"}, {"title": "Note 2"}, {"title": "Note 3"}]
            ],
            "distances": [[0.1, 0.3, 0.5]],
        }
        return collection

    @pytest.fixture
    def mock_chroma_client(self, mock_collection):
        """Create mock ChromaDB client."""
        client = Mock()
        client.get_or_create_collection.return_value = mock_collection
        return client

    def test_search_returns_expected_results(self, mock_chroma_client, mock_collection):
        """Test that search returns expected number of results."""
        search = VectorSearch(chroma_client=mock_chroma_client)
        embedding = [0.1] * 1024

        results = search.search(embedding, n_results=3)

        assert len(results) == 3
        assert all("id" in r for r in results)
        assert all("document" in r for r in results)
        assert all("metadata" in r for r in results)

    def test_search_includes_scores(self, mock_chroma_client, mock_collection):
        """Test that search results include scores."""
        search = VectorSearch(chroma_client=mock_chroma_client)
        embedding = [0.1] * 1024

        results = search.search(embedding, n_results=3)

        assert all("score" in r for r in results)
        assert all("distance" in r for r in results)
        # Scores should be between 0 and 1
        assert all(0 <= r["score"] <= 1 for r in results)

    def test_search_respects_n_results(self, mock_chroma_client, mock_collection):
        """Test that search respects n_results parameter."""
        search = VectorSearch(chroma_client=mock_chroma_client)
        embedding = [0.1] * 1024

        results = search.search(embedding, n_results=2)

        assert len(results) <= 2

    def test_search_empty_results(self, mock_chroma_client):
        """Test handling of empty results."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        search = VectorSearch(chroma_client=mock_chroma_client)
        embedding = [0.1] * 1024

        results = search.search(embedding, n_results=10)

        assert results == []


class TestVectorSearchEdgeCases:
    """Test edge cases for vector search."""

    def test_search_with_filter_metadata(self):
        """Test search with metadata filters."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "documents": [["filtered text"]],
            "metadatas": [[{"title": "Filtered", "tags": ["important"]}]],
            "distances": [[0.2]],
        }

        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        search = VectorSearch(chroma_client=mock_client)
        embedding = [0.1] * 1024
        filter_meta = {"tags": {"$contains": "important"}}

        results = search.search(embedding, n_results=10, filter_metadata=filter_meta)

        assert len(results) == 1
        assert results[0]["metadata"]["tags"] == ["important"]


class TestReRankerIntegration:
    """Test re-ranker integration (requires actual model)."""

    @pytest.mark.slow
    def test_reranker_loads_model(self):
        """Test that re-ranker loads the cross-encoder model."""
        from src.retrieval.reranker import ReRanker

        # This test requires the actual model and is slow
        # Mark with pytest.mark.slow to skip in CI
        reranker = ReRanker()
        assert reranker.model is not None

    @pytest.mark.slow
    def test_rerank_filters_by_threshold(self):
        """Test that re-ranker filters by threshold."""
        from src.retrieval.reranker import ReRanker

        reranker = ReRanker(threshold=0.75)
        query = "antifragility concept"
        documents = [
            {"document": "Nassim Taleb's concept of antifragility"},
            {"document": "Completely unrelated text about cats"},
        ]

        results = reranker.rerank(query, documents, top_k=5)

        assert all(r["rerank_score"] >= 0.75 for r in results)


class TestRetrievalPipeline:
    """Test retrieval pipeline orchestration."""

    @pytest.fixture
    def mock_pipeline_components(self):
        """Create mock pipeline components."""
        mock_vector_search = Mock()
        mock_vector_search.search.return_value = [
            {"id": "doc1", "document": "text1", "metadata": {}, "score": 0.9},
            {"id": "doc2", "document": "text2", "metadata": {}, "score": 0.8},
        ]

        mock_reranker = Mock()
        mock_reranker.rerank.return_value = [
            {"id": "doc1", "document": "text1", "metadata": {}, "rerank_score": 0.85},
        ]

        return mock_vector_search, mock_reranker

    def test_pipeline_returns_expected_results(self, mock_pipeline_components):
        """Test that pipeline returns expected results."""
        from src.retrieval.pipeline import RetrievalPipeline

        mock_vector_search, mock_reranker = mock_pipeline_components

        # Create pipeline with mocked components
        pipeline = RetrievalPipeline.__new__(RetrievalPipeline)
        pipeline.vector_search = mock_vector_search
        pipeline.reranker = mock_reranker

        results = pipeline.retrieve(
            query_text="test query",
            query_embedding=[0.1] * 1024,
            n_results_initial=20,
            n_results_final=5,
            generate_embedding=False,
        )

        assert len(results) == 1
        assert results[0]["rerank_score"] == 0.85

    def test_pipeline_empty_vector_results(self):
        """Test pipeline with empty vector search results."""
        from src.retrieval.pipeline import RetrievalPipeline

        mock_vector_search = Mock()
        mock_vector_search.search.return_value = []

        pipeline = RetrievalPipeline.__new__(RetrievalPipeline)
        pipeline.vector_search = mock_vector_search

        results = pipeline.retrieve(
            query_text="test query",
            query_embedding=[0.1] * 1024,
            generate_embedding=False,
        )

        assert results == []


class TestPerformanceMetrics:
    """Test performance logging."""

    def test_results_include_timing(self):
        """Test that results include timing metadata."""
        from src.retrieval.pipeline import RetrievalPipeline
        import time

        mock_vector_search = Mock()
        mock_vector_search.search.return_value = [
            {"id": "doc1", "document": "text1", "metadata": {}},
        ]
        mock_vector_search.get_collection_stats.return_value = {"document_count": 1000}

        mock_reranker = Mock()
        mock_reranker.rerank.return_value = [
            {"id": "doc1", "document": "text1", "metadata": {}, "rerank_score": 0.85},
        ]

        pipeline = RetrievalPipeline.__new__(RetrievalPipeline)
        pipeline.vector_search = mock_vector_search
        pipeline.reranker = mock_reranker

        results = pipeline.retrieve(
            query_text="test",
            query_embedding=[0.1] * 1024,
            generate_embedding=False,
        )

        assert all("retrieval_time" in r for r in results)
        assert all(r["retrieval_time"] > 0 for r in results)
