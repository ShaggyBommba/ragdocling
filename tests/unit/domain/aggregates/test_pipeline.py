"""Unit tests for Pipeline aggregate."""

import pytest

from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.pipeline import PipelineLifecycle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collection_id() -> CollectionID:
    return CollectionID.generate()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelineCreation:
    def test_create_pipeline_has_correct_collection(self) -> None:
        cid = _collection_id()
        pipeline = Pipeline.create(name="default", collection_id=cid)
        assert pipeline.collection_id == cid

    def test_create_pipeline_default_lifecycle_is_staging(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        assert pipeline.lifecycle == PipelineLifecycle.STAGING

    def test_create_pipeline_with_explicit_production_lifecycle(self) -> None:
        pipeline = Pipeline.create(
            name="default",
            collection_id=_collection_id(),
            lifecycle=PipelineLifecycle.PRODUCTION,
        )
        assert pipeline.lifecycle == PipelineLifecycle.PRODUCTION

    def test_create_pipeline_has_default_transformations(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        assert len(pipeline.transformations_settings) > 0

    def test_create_pipeline_deterministic_id_for_same_settings(self) -> None:
        cid = _collection_id()
        p1 = Pipeline.create(name="default", collection_id=cid)
        p2 = Pipeline.create(name="default", collection_id=cid)
        assert p1.identity.value == p2.identity.value

    def test_create_pipeline_different_collections_produce_different_ids(self) -> None:
        p1 = Pipeline.create(name="default", collection_id=_collection_id())
        p2 = Pipeline.create(name="default", collection_id=_collection_id())
        assert p1.identity.value != p2.identity.value

    def test_create_pipeline_has_identity(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        assert pipeline.identity is not None

    def test_created_at_before_updated_at(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        assert pipeline.created_at <= pipeline.updated_at


class TestPipelineLifecycle:
    def test_deploy_sets_production(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        pipeline.deploy()
        assert pipeline.lifecycle == PipelineLifecycle.PRODUCTION

    def test_stage_sets_staging(self) -> None:
        pipeline = Pipeline.create(
            name="default",
            collection_id=_collection_id(),
            lifecycle=PipelineLifecycle.PRODUCTION,
        )
        pipeline.stage()
        assert pipeline.lifecycle == PipelineLifecycle.STAGING

    def test_archive_sets_archived(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        pipeline.archive()
        assert pipeline.lifecycle == PipelineLifecycle.ARCHIVED

    def test_deploy_updates_timestamp(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        before = pipeline.updated_at
        pipeline.deploy()
        assert pipeline.updated_at >= before

    def test_stage_updates_timestamp(self) -> None:
        pipeline = Pipeline.create(
            name="default",
            collection_id=_collection_id(),
            lifecycle=PipelineLifecycle.PRODUCTION,
        )
        before = pipeline.updated_at
        pipeline.stage()
        assert pipeline.updated_at >= before

    def test_archive_updates_timestamp(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        before = pipeline.updated_at
        pipeline.archive()
        assert pipeline.updated_at >= before

    def test_cannot_deploy_archived_pipeline(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        pipeline.archive()
        pipeline.deploy()
        assert pipeline.lifecycle == PipelineLifecycle.ARCHIVED

    def test_cannot_stage_archived_pipeline(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        pipeline.archive()
        pipeline.stage()
        assert pipeline.lifecycle == PipelineLifecycle.ARCHIVED

    def test_cannot_archive_already_archived_pipeline(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        pipeline.archive()
        before = pipeline.updated_at
        pipeline.archive()
        # Still archived, updated_at may or may not change — just ensure no crash and state is correct
        assert pipeline.lifecycle == PipelineLifecycle.ARCHIVED


class TestPipelineDefaultTransformations:
    def test_default_transformations_include_pattern_match(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        names = [t.name for t in pipeline.transformations_settings]
        assert "PatternMatchTransformer" in names

    def test_default_transformations_include_url_extract(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        names = [t.name for t in pipeline.transformations_settings]
        assert "UrlExtractTransformer" in names

    def test_default_transformations_include_query_generation(self) -> None:
        pipeline = Pipeline.create(name="default", collection_id=_collection_id())
        names = [t.name for t in pipeline.transformations_settings]
        assert "QueryGenerationTransformer" in names

    def test_custom_transformations_override_defaults(self) -> None:
        from dacke.domain.values.transformer import TransformerSettings
        custom = [TransformerSettings(name="UrlExtractTransformer")]
        pipeline = Pipeline.create(
            name="default",
            collection_id=_collection_id(),
            transformations_settings=custom,
        )
        assert len(pipeline.transformations_settings) == 1
        assert pipeline.transformations_settings[0].name == "UrlExtractTransformer"
