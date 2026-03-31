"""Unit tests for OpenAIReranker."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dacke.infrastructure.pipeline.reranker import OpenAIReranker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reranker() -> OpenAIReranker:
    return OpenAIReranker()


def _rerank_response(score: float) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"results": [{"relevance_score": score}]}
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOpenAIReranker:
    @pytest.mark.asyncio
    async def test_rerank_returns_ranked_results(self) -> None:
        reranker = _make_reranker()
        documents = ["doc A", "doc B", "doc C"]
        scores = [0.9, 0.5, 0.7]
        mock_post = AsyncMock(side_effect=[_rerank_response(s) for s in scores])
        with patch("httpx.AsyncClient.post", mock_post):
            results = await reranker.rerank(
                query="test query",
                documents=documents,
                top_n=3,
                model="jina-reranker-v2",
                base_url="http://mock-reranker/v1",
            )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rerank_results_sorted_by_score_descending(self) -> None:
        reranker = _make_reranker()
        documents = ["low", "high", "mid"]
        scores = [0.3, 0.9, 0.6]
        mock_post = AsyncMock(side_effect=[_rerank_response(s) for s in scores])
        with patch("httpx.AsyncClient.post", mock_post):
            results = await reranker.rerank(
                query="q",
                documents=documents,
                top_n=3,
                model="m",
                base_url="http://mock/v1",
            )
        assert results[0].score >= results[1].score >= results[2].score

    @pytest.mark.asyncio
    async def test_rerank_top_n_limits_results(self) -> None:
        reranker = _make_reranker()
        documents = ["a", "b", "c", "d", "e"]
        mock_post = AsyncMock(side_effect=[_rerank_response(float(i) / 10) for i in range(5)])
        with patch("httpx.AsyncClient.post", mock_post):
            results = await reranker.rerank(
                query="q",
                documents=documents,
                top_n=2,
                model="m",
                base_url="http://mock/v1",
            )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_rerank_preserves_original_index(self) -> None:
        reranker = _make_reranker()
        documents = ["first", "second"]
        mock_post = AsyncMock(side_effect=[_rerank_response(0.8), _rerank_response(0.9)])
        with patch("httpx.AsyncClient.post", mock_post):
            results = await reranker.rerank(
                query="q",
                documents=documents,
                top_n=2,
                model="m",
                base_url="http://mock/v1",
            )
        indices = {r.index for r in results}
        assert indices == {0, 1}

    @pytest.mark.asyncio
    async def test_rerank_empty_documents_returns_empty(self) -> None:
        reranker = _make_reranker()
        results = await reranker.rerank(
            query="q",
            documents=[],
            top_n=5,
            model="m",
            base_url="http://mock/v1",
        )
        assert results == []
