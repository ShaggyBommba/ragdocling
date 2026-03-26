"""Tests for PipelineRepository."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.pipeline import PipelineID
from dacke.infrastructure.repositories.providers.postgres.models import PipelinesTable
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineAcl,
    PipelineRepository,
)

pytest_plugins = ("pytest_asyncio",)


class TestPipelineAcl:
    """Test PipelineAcl translation layer."""

    @pytest.fixture
    def acl(self) -> PipelineAcl:
        return PipelineAcl()

    @pytest.fixture
    def collection_id(self) -> CollectionID:
        return CollectionID.generate()

    @pytest.fixture
    def pipeline(self, collection_id: CollectionID) -> Pipeline:
        return Pipeline.create("Test Pipeline", collection_id)

    def test_roundtrip_conversion(self, acl: PipelineAcl, pipeline: Pipeline) -> None:
        """Test roundtrip conversion domain -> ORM -> domain."""
        orm = acl.from_domain(pipeline)
        domain = acl.to_domain(orm)

        assert domain.identity.value == pipeline.identity.value
        assert domain.collection_id == pipeline.collection_id


class TestPipelineRepository:
    """Test PipelineRepository persistence operations."""

    @pytest_asyncio.fixture
    async def repository(self) -> AsyncIterator[PipelineRepository]:
        """Create repository instance with in-memory database."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        async with engine.begin() as conn:
            await conn.run_sync(PipelinesTable.metadata.create_all)

        repo = PipelineRepository("sqlite+aiosqlite:///:memory:")
        repo._engine = engine
        repo._client = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        yield repo
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_save_pipeline(self, repository: PipelineRepository) -> None:
        """Test saving a pipeline aggregate."""
        collection_id = CollectionID.generate()
        pipeline = Pipeline.create("Test Pipeline", collection_id)
        await repository.save_pipeline(pipeline)
        assert pipeline.identity.value is not None

    @pytest.mark.asyncio
    async def test_get_pipeline_by_id(self, repository: PipelineRepository) -> None:
        """Test retrieving a pipeline by identity."""
        collection_id = CollectionID.generate()
        pipeline = Pipeline.create("Test Pipeline", collection_id)
        await repository.save_pipeline(pipeline)
        retrieved = await repository.get_pipeline_by_id(pipeline.identity)
        assert retrieved is not None
        assert retrieved.identity.value == pipeline.identity.value

    @pytest.mark.asyncio
    async def test_get_pipelines_by_collection(self, repository: PipelineRepository) -> None:
        """Test retrieving all pipelines in a collection."""
        collection_id = CollectionID.generate()
        pipeline = Pipeline.create("Test Pipeline", collection_id)
        await repository.save_pipeline(pipeline)
        pipelines = await repository.get_pipelines_by_collection(collection_id)
        assert len(pipelines) >= 1

    @pytest.mark.asyncio
    async def test_delete_pipeline(self, repository: PipelineRepository) -> None:
        """Test deleting a pipeline."""
        collection_id = CollectionID.generate()
        pipeline = Pipeline.create("To Delete", collection_id)
        await repository.save_pipeline(pipeline)
        await repository.delete_pipeline(pipeline.identity)
        retrieved = await repository.get_pipeline_by_id(pipeline.identity)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_pipeline_not_found(self, repository: PipelineRepository) -> None:
        """Test retrieving non-existent pipeline returns None."""
        fake_id = PipelineID.generate()
        retrieved = await repository.get_pipeline_by_id(fake_id)
        assert retrieved is None
