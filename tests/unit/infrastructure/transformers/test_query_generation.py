"""Unit tests for QueryGenerationTransformer."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from dacke.infrastructure.pipeline.transformers.query_generation import (
    QueryGenerationTransformer,
)

from .common import llm_response, make_doc


class TestQueryGenerationTransformer:
    def _make_transformer(self) -> QueryGenerationTransformer:
        return QueryGenerationTransformer(url="http://mock-llm/v1/chat/completions")

    @pytest.mark.asyncio
    async def test_sets_positive_and_negative_queries(self) -> None:
        doc = make_doc("Python is a programming language.")
        llm_json = json.dumps(
            {
                "positive": ["What is Python?", "What kind of language is Python?"],
                "negative": ["What is Java?", "How do you bake bread?"],
            }
        )
        mock_post = AsyncMock(return_value=llm_response(llm_json))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["positive_queries"] == [
            "What is Python?",
            "What kind of language is Python?",
        ]
        assert doc.chunks[0].metadata["negative_queries"] == [
            "What is Java?",
            "How do you bake bread?",
        ]

    @pytest.mark.asyncio
    async def test_llm_failure_sets_none(self) -> None:
        doc = make_doc("Some content.")
        mock_post = AsyncMock(side_effect=Exception("connection refused"))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["positive_queries"] is None
        assert doc.chunks[0].metadata["negative_queries"] is None

    @pytest.mark.asyncio
    async def test_invalid_json_sets_none(self) -> None:
        doc = make_doc("Some content.")
        mock_post = AsyncMock(return_value=llm_response("not valid json {{"))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["positive_queries"] is None

    @pytest.mark.asyncio
    async def test_multiple_chunks_called_concurrently(self) -> None:
        doc = make_doc("Chunk A.", "Chunk B.", "Chunk C.")
        llm_json = json.dumps({"positive": ["q1"], "negative": ["q2"]})
        mock_post = AsyncMock(return_value=llm_response(llm_json))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert mock_post.call_count == 3
        for chunk in doc.chunks:
            assert chunk.metadata["positive_queries"] == ["q1"]

    @pytest.mark.asyncio
    async def test_empty_lists_set_none(self) -> None:
        doc = make_doc("Content.")
        llm_json = json.dumps({"positive": [], "negative": []})
        mock_post = AsyncMock(return_value=llm_response(llm_json))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["positive_queries"] is None
        assert doc.chunks[0].metadata["negative_queries"] is None
