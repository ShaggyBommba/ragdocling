"""Unit tests for CleanupArtifactDataHandler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dacke.application.services.handlers.artifact import CleanupArtifactDataHandler
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.pipeline import PipelineLifecycle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifact(source: str = "https://example.com/test.pdf") -> MagicMock:
    a = MagicMock()
    a.metadata = MagicMock()
    a.metadata.source = source
    a.address = MagicMock()
    return a


def _make_handler(
    artifact: MagicMock | None = None,
    pipelines: list[MagicMock] | None = None,
) -> tuple[CleanupArtifactDataHandler, MagicMock, MagicMock, MagicMock, MagicMock]:
    resolved = artifact if artifact is not None else _make_artifact()

    _pipelines = pipelines
    if _pipelines is None:
        pipeline = MagicMock()
        pipeline.identity = MagicMock()
        pipeline.lifecycle = PipelineLifecycle.PRODUCTION
        _pipelines = [pipeline]

    pipeline_repo = MagicMock()
    pipeline_repo.get_pipelines_by_collection = AsyncMock(return_value=_pipelines)

    artifact_repo = MagicMock()
    artifact_repo.get_artifact_by_id = AsyncMock(return_value=resolved)
    artifact_repo.delete_artifact = AsyncMock()

    blob_repo = MagicMock()
    blob_repo.delete_blob = AsyncMock()

    embedding_repo = MagicMock()
    embedding_repo.delete_by_origin = AsyncMock()

    handler = CleanupArtifactDataHandler(
        pipeline_repo=pipeline_repo,
        artifact_repo=artifact_repo,
        blob_repo=blob_repo,
        embedding_repo=embedding_repo,
    )
    return handler, pipeline_repo, artifact_repo, blob_repo, embedding_repo


def _make_handler_artifact_missing() -> tuple[CleanupArtifactDataHandler, MagicMock, MagicMock, MagicMock, MagicMock]:
    pipeline = MagicMock()
    pipeline.identity = MagicMock()

    pipeline_repo = MagicMock()
    pipeline_repo.get_pipelines_by_collection = AsyncMock(return_value=[pipeline])

    artifact_repo = MagicMock()
    artifact_repo.get_artifact_by_id = AsyncMock(return_value=None)
    artifact_repo.delete_artifact = AsyncMock()

    blob_repo = MagicMock()
    blob_repo.delete_blob = AsyncMock()

    embedding_repo = MagicMock()
    embedding_repo.delete_by_origin = AsyncMock()

    handler = CleanupArtifactDataHandler(
        pipeline_repo=pipeline_repo,
        artifact_repo=artifact_repo,
        blob_repo=blob_repo,
        embedding_repo=embedding_repo,
    )
    return handler, pipeline_repo, artifact_repo, blob_repo, embedding_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCleanupArtifactDataHandler:
    @pytest.mark.asyncio
    async def test_returns_empty_when_artifact_not_found(self) -> None:
        handler, *_ = _make_handler_artifact_missing()
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_deletes_embeddings_for_each_pipeline(self) -> None:
        pipeline_a = MagicMock()
        pipeline_a.identity = MagicMock()
        pipeline_b = MagicMock()
        pipeline_b.identity = MagicMock()

        handler, _, _, _, embedding_repo = _make_handler(pipelines=[pipeline_a, pipeline_b])
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )

        assert embedding_repo.delete_by_origin.call_count == 2

    @pytest.mark.asyncio
    async def test_deletes_blob_from_storage(self) -> None:
        handler, _, _, blob_repo, _ = _make_handler()
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        blob_repo.delete_blob.assert_called_once()

    @pytest.mark.asyncio
    async def test_deletes_artifact_metadata(self) -> None:
        handler, _, artifact_repo, *_ = _make_handler()
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        artifact_repo.delete_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_embedding_deletion_when_no_pipelines(self) -> None:
        handler, _, _, _, embedding_repo = _make_handler(pipelines=[])
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        embedding_repo.delete_by_origin.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_status_dict_on_success(self) -> None:
        handler, *_ = _make_handler()
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert isinstance(result, dict)
        assert result["status"] == "cleaned"

    @pytest.mark.asyncio
    async def test_delete_by_origin_called_with_artifact_source(self) -> None:
        artifact = _make_artifact(source="https://example.com/specific.pdf")
        handler, _, _, _, embedding_repo = _make_handler(artifact=artifact)
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )

        call_origins = embedding_repo.delete_by_origin.call_args.args[0]
        assert "https://example.com/specific.pdf" in call_origins
