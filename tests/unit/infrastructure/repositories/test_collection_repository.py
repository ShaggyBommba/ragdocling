"""Tests for CollectionRepository."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dacke.domain.aggregates.collection import Collection
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID
from dacke.infrastructure.repositories.providers.postgres.models import (
    CollectionsTable,
)
from dacke.infrastructure.repositories.providers.postgres.repo_collection import (
    CollectionAcl,
    CollectionRepository,
)

pytest_plugins = ("pytest_asyncio",)


class TestCollectionAcl:
    """Test CollectionAcl translation layer."""

    @pytest.fixture
    def acl(self) -> CollectionAcl:
        return CollectionAcl()

    @pytest.fixture
    def workspace_id(self) -> WorkspaceID:
        return WorkspaceID.generate()

    @pytest.fixture
    def collection(self, workspace_id: WorkspaceID) -> Collection:
        return Collection.create("Test Collection", workspace_id)

    def test_roundtrip_conversion(self, acl: CollectionAcl, collection: Collection) -> None:
        """Test roundtrip conversion domain -> ORM -> domain."""
        orm = acl.from_domain(collection)
        domain = acl.to_domain(orm)

        assert domain.identity.value == collection.identity.value
        assert domain.name == collection.name
        assert domain.workspace_id == collection.workspace_id
        assert domain.max_count_files == collection.max_count_files
        assert domain.max_file_size_kb == collection.max_file_size_kb
        assert domain.artifact_ids == collection.artifact_ids


class TestCollectionRepository:
    """Test CollectionRepository persistence operations."""

    @pytest_asyncio.fixture
    async def repository(self) -> AsyncIterator[CollectionRepository]:
        """Create repository instance with in-memory database."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        async with engine.begin() as conn:
            await conn.run_sync(CollectionsTable.metadata.create_all)

        repo = CollectionRepository("sqlite+aiosqlite:///:memory:")
        repo._engine = engine
        repo._client = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        yield repo
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_save_collection(self, repository: CollectionRepository) -> None:
        """Test saving a collection aggregate."""
        workspace_id = WorkspaceID.generate()
        collection = Collection.create("Test Collection", workspace_id)
        await repository.save_collection(collection)
        assert collection.identity.value is not None

    @pytest.mark.asyncio
    async def test_get_collection_by_id(self, repository: CollectionRepository) -> None:
        """Test retrieving a collection by identity."""
        workspace_id = WorkspaceID.generate()
        collection = Collection.create("Test Collection", workspace_id)
        await repository.save_collection(collection)
        retrieved = await repository.get_collection_by_id(collection.identity)
        assert retrieved is not None
        assert retrieved.name == "Test Collection"

    @pytest.mark.asyncio
    async def test_get_collections_by_workspace(self, repository: CollectionRepository) -> None:
        """Test retrieving all collections in a workspace."""
        workspace_id = WorkspaceID.generate()
        collection = Collection.create("Test Collection", workspace_id)
        await repository.save_collection(collection)
        collections = await repository.list_collections()
        assert len(collections) >= 1

    @pytest.mark.asyncio
    async def test_delete_collection(self, repository: CollectionRepository) -> None:
        """Test deleting a collection."""
        workspace_id = WorkspaceID.generate()
        collection = Collection.create("To Delete", workspace_id)
        await repository.save_collection(collection)
        await repository.delete_collection(collection.identity)
        retrieved = await repository.get_collection_by_id(collection.identity)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_collection_not_found(self, repository: CollectionRepository) -> None:
        """Test retrieving non-existent collection returns None."""
        fake_id = CollectionID.generate()
        retrieved = await repository.get_collection_by_id(fake_id)
        assert retrieved is None
