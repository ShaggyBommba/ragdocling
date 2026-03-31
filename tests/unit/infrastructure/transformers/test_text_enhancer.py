"""Unit tests for TextEnhancerTransformer."""

from unittest.mock import AsyncMock, patch

import pytest

from dacke.infrastructure.pipeline.transformers.text_enhancer import (
    TextEnhancerTransformer,
)

from .common import llm_response, make_doc


class TestTextEnhancerTransformer:
    def _make_transformer(self) -> TextEnhancerTransformer:
        return TextEnhancerTransformer(url="http://mock-llm/v1/chat/completions")

    @pytest.mark.asyncio
    async def test_replaces_content_with_enhanced_text(self) -> None:
        doc = make_doc("Bro-\nken hy-\nphenation here.")
        enhanced = "Broken hyphenation here."
        mock_post = AsyncMock(return_value=llm_response(enhanced))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == enhanced

    @pytest.mark.asyncio
    async def test_llm_failure_preserves_original(self) -> None:
        original = "Original content."
        doc = make_doc(original)
        mock_post = AsyncMock(side_effect=Exception("timeout"))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == original

    @pytest.mark.asyncio
    async def test_empty_llm_response_preserves_original(self) -> None:
        original = "Original content."
        doc = make_doc(original)
        mock_post = AsyncMock(return_value=llm_response("   "))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == original

    @pytest.mark.asyncio
    async def test_multiple_chunks_each_enhanced(self) -> None:
        doc = make_doc("Raw A.", "Raw B.")
        mock_post = AsyncMock(
            side_effect=[
                llm_response("Enhanced A."),
                llm_response("Enhanced B."),
            ]
        )
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].content == "Enhanced A."
        assert doc.chunks[1].content == "Enhanced B."

    @pytest.mark.asyncio
    async def test_returns_same_document(self) -> None:
        doc = make_doc("text")
        mock_post = AsyncMock(return_value=llm_response("better text"))
        with patch("httpx.AsyncClient.post", mock_post):
            result = await self._make_transformer().transform(doc)
        assert result is doc
