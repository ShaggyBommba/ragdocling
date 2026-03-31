"""Unit tests for ContextualSummaryTransformer."""

from unittest.mock import AsyncMock, patch

import pytest

from dacke.infrastructure.pipeline.transformers.contextual_summary import (
    ContextualSummaryTransformer,
)

from .common import llm_response, make_doc


class TestContextualSummaryTransformer:
    def _make_transformer(self) -> ContextualSummaryTransformer:
        return ContextualSummaryTransformer(url="http://mock-llm/v1/chat/completions")

    @pytest.mark.asyncio
    async def test_prepends_summary_to_content(self) -> None:
        original = "Python supports dynamic typing and garbage collection."
        doc = make_doc(original)
        summary = "Python is a dynamically typed programming language."
        mock_post = AsyncMock(return_value=llm_response(summary))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == f"{summary}\n\n{original}"

    @pytest.mark.asyncio
    async def test_llm_failure_preserves_original(self) -> None:
        original = "Original content."
        doc = make_doc(original)
        mock_post = AsyncMock(side_effect=Exception("timeout"))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == original

    @pytest.mark.asyncio
    async def test_empty_summary_preserves_original(self) -> None:
        original = "Original content."
        doc = make_doc(original)
        mock_post = AsyncMock(return_value=llm_response(""))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == original

    @pytest.mark.asyncio
    async def test_multiple_chunks_each_get_summary(self) -> None:
        doc = make_doc("Content A.", "Content B.")
        mock_post = AsyncMock(
            side_effect=[
                llm_response("Summary A."),
                llm_response("Summary B."),
            ]
        )
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == "Summary A.\n\nContent A."
        assert doc.chunks[1].content == "Summary B.\n\nContent B."

    @pytest.mark.asyncio
    async def test_summary_is_stripped(self) -> None:
        original = "Content."
        doc = make_doc(original)
        mock_post = AsyncMock(return_value=llm_response("  Summary with whitespace.  "))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == "Summary with whitespace.\n\nContent."
