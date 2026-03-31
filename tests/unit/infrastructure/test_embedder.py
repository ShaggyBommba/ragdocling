"""Unit tests for OpenAIEmbedder."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import AnyUrl

from dacke.domain.entities.chunk import Chunk
from dacke.domain.values.document import DocumentID
from dacke.infrastructure.pipeline.embedder import OpenAIEmbedder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ORIGIN = AnyUrl("https://example.com/doc.pdf")


def _make_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder(base_url="http://mock-llm/v1")


def _embedding_response(vector: list[float], index: int = 0) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"data": [{"embedding": vector, "index": index}]}
    return resp


def _make_chunk(content: str = "test content") -> Chunk:
    return Chunk.create(
        content=content,
        document_id=DocumentID.generate(),
        reference="ref-0",
        origin=_ORIGIN,
    )


def _make_settings(model: str = "text-embedding-3-small", dimensions: int = 3) -> MagicMock:
    settings = MagicMock()
    settings.model = model
    settings.dimensions = dimensions
    return settings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOpenAIEmbedder:
    @pytest.mark.asyncio
    async def test_embed_returns_embedding_with_vector(self) -> None:
        embedder = _make_embedder()
        vector = [0.1, 0.2, 0.3]
        mock_post = AsyncMock(return_value=_embedding_response(vector))
        with patch("httpx.AsyncClient.post", mock_post):
            result = await embedder.embed(_make_chunk(), _make_settings())
        assert result.vector == vector

    @pytest.mark.asyncio
    async def test_embed_many_returns_one_embedding_per_chunk(self) -> None:
        embedder = _make_embedder()
        chunks = [_make_chunk("A"), _make_chunk("B"), _make_chunk("C")]

        def _multi_response(*_args: object, **_kwargs: object) -> MagicMock:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {
                "data": [
                    {"embedding": [0.1], "index": 0},
                    {"embedding": [0.2], "index": 1},
                    {"embedding": [0.3], "index": 2},
                ]
            }
            return resp

        mock_post = AsyncMock(side_effect=_multi_response)
        with patch("httpx.AsyncClient.post", mock_post):
            results = await embedder.embed_many(chunks, _make_settings())
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_embed_calls_correct_url(self) -> None:
        embedder = _make_embedder()
        mock_post = AsyncMock(return_value=_embedding_response([0.0]))
        with patch("httpx.AsyncClient.post", mock_post) as patched:
            await embedder.embed(_make_chunk(), _make_settings())
        called_url = str(patched.call_args.args[0])
        assert "embeddings" in called_url

    @pytest.mark.asyncio
    async def test_embed_passes_model_in_request(self) -> None:
        embedder = _make_embedder()
        mock_post = AsyncMock(return_value=_embedding_response([0.0]))
        with patch("httpx.AsyncClient.post", mock_post) as patched:
            await embedder.embed(_make_chunk(), _make_settings(model="my-model"))
        body = patched.call_args.kwargs.get("json") or patched.call_args.args[1]
        assert body["model"] == "my-model"

    @pytest.mark.asyncio
    async def test_embed_single_chunk_produces_one_result(self) -> None:
        embedder = _make_embedder()
        mock_post = AsyncMock(return_value=_embedding_response([0.5, 0.6, 0.7]))
        with patch("httpx.AsyncClient.post", mock_post):
            results = await embedder.embed_many([_make_chunk("solo")], _make_settings())
        assert len(results) == 1
        assert results[0].vector == [0.5, 0.6, 0.7]
