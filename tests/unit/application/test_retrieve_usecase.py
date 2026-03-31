"""Unit tests for RetrieveUseCase."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from qdrant_client.http.models import ScoredPoint

from dacke.application.services.usecases.retrieve import RetrieveUseCase
from dacke.domain.values.pipeline import PipelineID, PipelineLifecycle
from dacke.domain.values.retrieval import RerankerSettings
from dacke.dto.retrieve import RetrieveDTO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_point(
    id: str | None = None,
    text: str = "some text",
    origin: str = "https://example.com/doc.pdf",
    references: list[str] | None = None,
    score: float = 0.9,
) -> ScoredPoint:
    point = MagicMock(spec=ScoredPoint)
    point.id = id or str(uuid4())
    point.score = score
    point.payload = {
        "text": text,
        "origin": origin,
        "title": "Test Doc",
        "pages": 1,
        "tags": [],
        "attachments": [],
        "references": references or [],
    }
    return point


def _make_use_case(
    pipeline: MagicMock | None = None,
    points: list[ScoredPoint] | None = None,
    embedding_vector: list[float] | None = None,
) -> tuple[RetrieveUseCase, MagicMock, MagicMock, MagicMock, MagicMock]:
    embedder = MagicMock()
    embedding = MagicMock()
    embedding.vector = embedding_vector or [0.1, 0.2, 0.3]
    embedder.embed = AsyncMock(return_value=embedding)

    embedding_repo = MagicMock()
    embedding_repo.search = AsyncMock(return_value=points or [])
    embedding_repo.fetch_by_origin = AsyncMock(return_value=[])

    pipeline_repo = MagicMock()
    pipeline_repo.get_pipeline_by_id = AsyncMock(return_value=pipeline)

    reranker = MagicMock()
    reranker.rerank = AsyncMock(return_value=[])

    uc = RetrieveUseCase(
        embedder=embedder,
        embedding_repo=embedding_repo,
        pipeline_repo=pipeline_repo,
        reranker=reranker,
    )
    return uc, embedder, embedding_repo, pipeline_repo, reranker


def _make_pipeline(collection_id: str | None = None) -> MagicMock:
    pipeline = MagicMock()
    pipeline.identity = PipelineID.generate()
    pipeline.lifecycle = PipelineLifecycle.PRODUCTION
    pipeline.extraction_settings = MagicMock()
    pipeline.extraction_settings.embedding = MagicMock()
    return pipeline


def _make_dto(
    pipeline_id: PipelineID | None = None,
    query: str = "test query",
    top_k: int = 3,
    reranker: RerankerSettings | None = None,
    expand_links: bool = False,
    tags: list[str] | None = None,
    origins: list[str] | None = None,
) -> RetrieveDTO:
    return RetrieveDTO(
        pipeline_id=pipeline_id or PipelineID.generate(),
        query=query,
        top_k=top_k,
        reranker=reranker,
        expand_links=expand_links,
        tags=tags,
        origins=origins,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRetrieveUseCase:
    @pytest.mark.asyncio
    async def test_returns_empty_when_pipeline_not_found(self) -> None:
        uc, *_ = _make_use_case(pipeline=None)
        result = await uc.execute(_make_dto())
        assert result == []

    @pytest.mark.asyncio
    async def test_embeds_query_and_calls_search(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point()
        uc, embedder, embedding_repo, pipeline_repo, _ = _make_use_case(
            pipeline=pipeline, points=[point]
        )
        dto = _make_dto(pipeline_id=pipeline.identity)

        result = await uc.execute(dto)

        embedder.embed.assert_called_once()
        embedding_repo.search.assert_called_once()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_search_results(self) -> None:
        pipeline = _make_pipeline()
        uc, *_ = _make_use_case(pipeline=pipeline, points=[])
        result = await uc.execute(_make_dto(pipeline_id=pipeline.identity))
        assert result == []

    @pytest.mark.asyncio
    async def test_search_called_with_correct_top_k(self) -> None:
        pipeline = _make_pipeline()
        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[])
        dto = _make_dto(pipeline_id=pipeline.identity, top_k=7)

        await uc.execute(dto)

        call_kwargs = embedding_repo.search.call_args.kwargs
        assert call_kwargs["top_k"] == 7

    @pytest.mark.asyncio
    async def test_search_called_with_oversample_when_reranker_enabled(self) -> None:
        pipeline = _make_pipeline()
        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[])
        reranker_settings = RerankerSettings(enabled=True, oversample=15)
        dto = _make_dto(pipeline_id=pipeline.identity, top_k=3, reranker=reranker_settings)

        await uc.execute(dto)

        call_kwargs = embedding_repo.search.call_args.kwargs
        assert call_kwargs["top_k"] == 15

    @pytest.mark.asyncio
    async def test_reranker_called_when_enabled_and_results_exist(self) -> None:
        pipeline = _make_pipeline()
        points = [_make_point(text="doc A"), _make_point(text="doc B")]
        uc, _, _, _, reranker = _make_use_case(pipeline=pipeline, points=points)
        ranked = [MagicMock(index=0, score=0.95), MagicMock(index=1, score=0.80)]
        reranker.rerank = AsyncMock(return_value=ranked)

        reranker_settings = RerankerSettings(enabled=True, oversample=10)
        dto = _make_dto(pipeline_id=pipeline.identity, reranker=reranker_settings)

        result = await uc.execute(dto)

        reranker.rerank.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_reranker_not_called_when_disabled(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point()
        uc, _, _, _, reranker = _make_use_case(pipeline=pipeline, points=[point])
        reranker_settings = RerankerSettings(enabled=False)
        dto = _make_dto(pipeline_id=pipeline.identity, reranker=reranker_settings)

        await uc.execute(dto)

        reranker.rerank.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_passes_tags_filter(self) -> None:
        pipeline = _make_pipeline()
        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[])
        dto = _make_dto(pipeline_id=pipeline.identity, tags=["ai", "rag"])

        await uc.execute(dto)

        call_kwargs = embedding_repo.search.call_args.kwargs
        assert call_kwargs["tags"] == ["ai", "rag"]

    @pytest.mark.asyncio
    async def test_search_passes_origins_filter(self) -> None:
        pipeline = _make_pipeline()
        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[])
        dto = _make_dto(pipeline_id=pipeline.identity, origins=["https://example.com/doc.pdf"])

        await uc.execute(dto)

        call_kwargs = embedding_repo.search.call_args.kwargs
        assert call_kwargs["origins"] == ["https://example.com/doc.pdf"]

    @pytest.mark.asyncio
    async def test_result_dto_fields_populated(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point(text="hello world", origin="https://source.com/file.pdf")
        uc, *_ = _make_use_case(pipeline=pipeline, points=[point])

        result = await uc.execute(_make_dto(pipeline_id=pipeline.identity))

        assert len(result) == 1
        assert result[0].origin == "https://source.com/file.pdf"
        assert result[0].score == point.score


class TestRetrieveUseCaseLinkExpansion:
    @pytest.mark.asyncio
    async def test_expand_links_fetches_referenced_origins(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point(references=["https://linked.com/ref.pdf"])
        linked_point = _make_point(origin="https://linked.com/ref.pdf", score=0.0)

        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[point])
        embedding_repo.fetch_by_origin = AsyncMock(return_value=[linked_point])

        dto = _make_dto(pipeline_id=pipeline.identity, expand_links=True)
        result = await uc.execute(dto)

        embedding_repo.fetch_by_origin.assert_called_once_with(
            origins=["https://linked.com/ref.pdf"],
            pipeline_id=pipeline.identity,
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_expand_links_deduplicates_already_present_points(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point(id="same-id", references=["https://linked.com/ref.pdf"])
        duplicate = _make_point(id="same-id", origin="https://linked.com/ref.pdf")

        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[point])
        embedding_repo.fetch_by_origin = AsyncMock(return_value=[duplicate])

        dto = _make_dto(pipeline_id=pipeline.identity, expand_links=True)
        result = await uc.execute(dto)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_expand_links_skipped_when_no_references(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point(references=[])
        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[point])

        dto = _make_dto(pipeline_id=pipeline.identity, expand_links=True)
        await uc.execute(dto)

        embedding_repo.fetch_by_origin.assert_not_called()

    @pytest.mark.asyncio
    async def test_expand_links_disabled_does_not_call_fetch(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point(references=["https://linked.com/ref.pdf"])
        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[point])

        dto = _make_dto(pipeline_id=pipeline.identity, expand_links=False)
        await uc.execute(dto)

        embedding_repo.fetch_by_origin.assert_not_called()

    @pytest.mark.asyncio
    async def test_expand_links_appends_with_score_zero(self) -> None:
        pipeline = _make_pipeline()
        point = _make_point(references=["https://linked.com/ref.pdf"])
        linked_point = _make_point(origin="https://linked.com/ref.pdf", score=0.99)

        uc, _, embedding_repo, *_ = _make_use_case(pipeline=pipeline, points=[point])
        embedding_repo.fetch_by_origin = AsyncMock(return_value=[linked_point])

        dto = _make_dto(pipeline_id=pipeline.identity, expand_links=True)
        result = await uc.execute(dto)

        expanded = next(r for r in result if r.origin == "https://linked.com/ref.pdf")
        assert expanded.score == 0.0
