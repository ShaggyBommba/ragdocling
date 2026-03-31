"""Unit tests for EntityExtractorTransformer."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from dacke.infrastructure.pipeline.transformers.entity_extractor import (
    EntityExtractorTransformer,
)

from .common import llm_response, make_doc


class TestEntityExtractorTransformer:
    def _make_transformer(self) -> EntityExtractorTransformer:
        return EntityExtractorTransformer(url="http://mock-llm/v1/chat/completions")

    @pytest.mark.asyncio
    async def test_adds_entities_to_tags(self) -> None:
        doc = make_doc("Anthropic released Claude in San Francisco in 2023.")
        entities = ["Anthropic", "Claude", "San Francisco", "2023"]
        mock_post = AsyncMock(return_value=llm_response(json.dumps(entities)))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["tags"] == entities

    @pytest.mark.asyncio
    async def test_merges_with_existing_tags(self) -> None:
        doc = make_doc("Anthropic is an AI company.")
        doc.chunks[0].metadata["tags"] = ["ai", "existing-tag"]
        entities = ["Anthropic"]
        mock_post = AsyncMock(return_value=llm_response(json.dumps(entities)))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        tags = doc.chunks[0].metadata["tags"] or []
        assert "ai" in tags
        assert "existing-tag" in tags
        assert "Anthropic" in tags

    @pytest.mark.asyncio
    async def test_deduplicates_with_existing_tags(self) -> None:
        doc = make_doc("Anthropic is great.")
        doc.chunks[0].metadata["tags"] = ["Anthropic"]
        entities = ["Anthropic", "New Entity"]
        mock_post = AsyncMock(return_value=llm_response(json.dumps(entities)))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        tags = doc.chunks[0].metadata["tags"] or []
        assert tags.count("Anthropic") == 1
        assert "New Entity" in tags

    @pytest.mark.asyncio
    async def test_llm_failure_leaves_tags_unchanged(self) -> None:
        doc = make_doc("Content.")
        doc.chunks[0].metadata["tags"] = ["existing"]
        mock_post = AsyncMock(side_effect=Exception("timeout"))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["tags"] == ["existing"]

    @pytest.mark.asyncio
    async def test_invalid_json_leaves_tags_unchanged(self) -> None:
        doc = make_doc("Content.")
        doc.chunks[0].metadata["tags"] = None
        mock_post = AsyncMock(return_value=llm_response("not json"))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["tags"] is None

    @pytest.mark.asyncio
    async def test_empty_entities_skips_chunk(self) -> None:
        doc = make_doc("No named entities here.")
        mock_post = AsyncMock(return_value=llm_response(json.dumps([])))
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["tags"] is None

    @pytest.mark.asyncio
    async def test_multiple_chunks_processed(self) -> None:
        doc = make_doc("Chunk A content.", "Chunk B content.")
        mock_post = AsyncMock(
            side_effect=[
                llm_response(json.dumps(["Entity A"])),
                llm_response(json.dumps(["Entity B"])),
            ]
        )
        with patch("httpx.AsyncClient.post", mock_post):
            await self._make_transformer().transform(doc)
        assert doc.chunks[0].metadata["tags"] == ["Entity A"]
        assert doc.chunks[1].metadata["tags"] == ["Entity B"]

    @pytest.mark.asyncio
    async def test_returns_same_document(self) -> None:
        doc = make_doc("content")
        mock_post = AsyncMock(return_value=llm_response(json.dumps(["Entity"])))
        with patch("httpx.AsyncClient.post", mock_post):
            result = await self._make_transformer().transform(doc)
        assert result is doc
