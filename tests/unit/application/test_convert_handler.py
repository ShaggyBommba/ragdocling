"""Unit tests for ConvertArtifactToDocumentHandler."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from dacke.application.services.handlers.artifact import ConvertArtifactToDocumentHandler
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.pipeline import PipelineLifecycle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(
    artifact: MagicMock | None = MagicMock(),
    presigned_url: str | None = "http://minio/bucket/file.pdf",
    pipelines: list[MagicMock] | None = None,
    document: MagicMock | None = None,
    embeddings: list[MagicMock] | None = None,
) -> tuple[ConvertArtifactToDocumentHandler, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    if artifact is not None:
        artifact.metadata = MagicMock()
        artifact.metadata.filename = "test.pdf"
        artifact.metadata.source = "https://example.com/test.pdf"
        artifact.address = MagicMock()

    _pipelines = pipelines
    if _pipelines is None:
        prod_pipeline = MagicMock()
        prod_pipeline.identity = MagicMock()
        prod_pipeline.lifecycle = PipelineLifecycle.PRODUCTION
        prod_pipeline.extraction_settings = MagicMock()
        prod_pipeline.extraction_settings.embedding = MagicMock()
        prod_pipeline.transformations_settings = []
        _pipelines = [prod_pipeline]

    if document is not None:
        doc = document
    else:
        doc = MagicMock()
        doc.get_chunks.return_value = [MagicMock(), MagicMock()]

    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value=doc)

    transformer_registry = MagicMock()
    transformer_registry.get = MagicMock(return_value=None)

    pipeline_repo = MagicMock()
    pipeline_repo.get_pipelines_by_collection = AsyncMock(return_value=_pipelines)

    artifact_repo = MagicMock()
    artifact_repo.get_artifact_by_id = AsyncMock(return_value=artifact)

    blob_repo = MagicMock()
    blob_repo.get_presigned_url = AsyncMock(return_value=presigned_url)

    embedder = MagicMock()
    embedder.embed_many = AsyncMock(return_value=embeddings or [MagicMock(), MagicMock()])

    embedding_repo = MagicMock()
    embedding_repo.delete_by_origin = AsyncMock()
    embedding_repo.save_many = AsyncMock()

    handler = ConvertArtifactToDocumentHandler(
        pipeline_extractor=extractor,
        transformer_registry=transformer_registry,
        pipeline_repo=pipeline_repo,
        artifact_repo=artifact_repo,
        blob_repo=blob_repo,
        embedder=embedder,
        embedding_repo=embedding_repo,
    )
    return handler, extractor, transformer_registry, artifact_repo, blob_repo, embedder, embedding_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConvertArtifactToDocumentHandler:
    @pytest.mark.asyncio
    async def test_returns_embeddings_on_success(self) -> None:
        handler, *_ = _make_handler()
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_artifact_not_found(self) -> None:
        handler, *_ = _make_handler(artifact=None)
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_presigned_url_not_found(self) -> None:
        handler, *_ = _make_handler(presigned_url=None)
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pipelines(self) -> None:
        handler, *_ = _make_handler(pipelines=[])
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_production_pipeline(self) -> None:
        staging = MagicMock()
        staging.lifecycle = PipelineLifecycle.STAGING
        handler, *_ = _make_handler(pipelines=[staging])
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_extractor_called_with_presigned_url(self) -> None:
        handler, extractor, *_ = _make_handler(presigned_url="http://minio/bucket/file.pdf")
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        extractor.extract.assert_called_once()
        call_kwargs = extractor.extract.call_args.kwargs
        assert str(call_kwargs["url"]) == "http://minio/bucket/file.pdf"

    @pytest.mark.asyncio
    async def test_delete_by_origin_called_before_save(self) -> None:
        handler, _, _, _, _, _, embedding_repo = _make_handler()
        call_order: list[str] = []
        embedding_repo.delete_by_origin = AsyncMock(side_effect=lambda *a, **kw: call_order.append("delete"))
        embedding_repo.save_many = AsyncMock(side_effect=lambda *a, **kw: call_order.append("save"))

        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )

        assert call_order == ["delete", "save"]

    @pytest.mark.asyncio
    async def test_embeddings_saved_to_repo(self) -> None:
        handler, _, _, _, _, _, embedding_repo = _make_handler()
        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        embedding_repo.save_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_chunks_extracted(self) -> None:
        doc = MagicMock()
        doc.get_chunks.return_value = []
        handler, *_ = _make_handler(document=doc)
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_transformer_applied_when_registered(self) -> None:
        transformer_cls = MagicMock()
        transformer_instance = MagicMock()
        transformer_instance.transform = AsyncMock()
        transformer_cls.return_value = transformer_instance

        prod_pipeline = MagicMock()
        prod_pipeline.lifecycle = PipelineLifecycle.PRODUCTION
        prod_pipeline.identity = MagicMock()
        prod_pipeline.extraction_settings = MagicMock()
        prod_pipeline.extraction_settings.embedding = MagicMock()
        prod_pipeline.transformations_settings = [
            MagicMock(name="SomeTransformer", parameters={})
        ]

        handler, _, transformer_registry, *_ = _make_handler(pipelines=[prod_pipeline])
        transformer_registry.get = MagicMock(return_value=transformer_cls)

        await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )

        transformer_instance.transform.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_transformer_skipped_gracefully(self) -> None:
        prod_pipeline = MagicMock()
        prod_pipeline.lifecycle = PipelineLifecycle.PRODUCTION
        prod_pipeline.identity = MagicMock()
        prod_pipeline.extraction_settings = MagicMock()
        prod_pipeline.extraction_settings.embedding = MagicMock()
        prod_pipeline.transformations_settings = [
            MagicMock(name="UnknownTransformer", parameters={})
        ]

        handler, _, transformer_registry, *_ = _make_handler(pipelines=[prod_pipeline])
        transformer_registry.get = MagicMock(return_value=None)

        # Should not raise
        result = await handler.handle(
            artifact_id=ArtifactID.generate(),
            collection_id=CollectionID.generate(),
        )
        assert isinstance(result, list)
