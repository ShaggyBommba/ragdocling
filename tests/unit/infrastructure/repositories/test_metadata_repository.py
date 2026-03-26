"""Tests for ArtifactMetadataRepository."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dacke.domain.aggregates.artifact import Artifact
from dacke.domain.values.artifact import ArtifactID, ArtifactMetadata, ObjectAddress
from dacke.domain.values.collection import CollectionID
from dacke.infrastructure.repositories.providers.postgres.models import ArtifactsTable
from dacke.infrastructure.repositories.providers.postgres.repo_artifact import (
    ArtifactMetadataAcl,
    ArtifactMetadataRepository,
)

pytest_plugins = ("pytest_asyncio",)


class TestArtifactMetadataAcl:
    """Test ArtifactMetadataAcl translation layer."""

    @pytest.fixture
    def acl(self) -> ArtifactMetadataAcl:
        return ArtifactMetadataAcl()

    @pytest.fixture
    def collection_id(self) -> CollectionID:
        return CollectionID.generate()

    @pytest.fixture
    def artifact(self) -> Artifact:
        collection_id = CollectionID.generate()
        metadata = ArtifactMetadata.create(
            filename="sample.pdf",
            source="test",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
            author="tester",
        )
        address = ObjectAddress.create(
            bucket="test-bucket",
            prefix="collections/test/files",
            filename="sample.pdf",
        )
        return Artifact.create(collection_id=collection_id, metadata=metadata, address=address)

    def test_roundtrip_conversion(
        self,
        acl: ArtifactMetadataAcl,
        artifact: Artifact,
        collection_id: CollectionID,
    ) -> None:
        """Test roundtrip conversion domain -> ORM -> domain."""
        orm = acl.from_domain(artifact, collection_id)
        domain = acl.to_domain(orm)

        assert domain.identity.value == artifact.identity.value
        assert domain.metadata.filename == artifact.metadata.filename
        assert domain.address.s3_uri == artifact.address.s3_uri


class TestArtifactMetadataRepository:
    """Test ArtifactMetadataRepository persistence operations."""

    @pytest_asyncio.fixture
    async def repository(self) -> AsyncIterator[ArtifactMetadataRepository]:
        """Create repository instance with in-memory database."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        async with engine.begin() as conn:
            await conn.run_sync(ArtifactsTable.metadata.create_all)

        repo = ArtifactMetadataRepository("sqlite+aiosqlite:///:memory:")
        repo._engine = engine
        repo._client = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        yield repo
        await engine.dispose()

    def _artifact(self, filename: str) -> Artifact:
        metadata = ArtifactMetadata.create(
            filename=filename,
            source="test",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum=f"checksum-{filename}",
            author="tester",
        )
        address = ObjectAddress.create(
            bucket="test-bucket",
            prefix="collections/test/files",
            filename=filename,
        )
        collection_id = CollectionID.generate()
        return Artifact.create(collection_id=collection_id, metadata=metadata, address=address)

    @pytest.mark.asyncio
    async def test_save_artifact(self, repository: ArtifactMetadataRepository) -> None:
        """Test saving an artifact entity."""
        collection_id = CollectionID.generate()
        artifact = self._artifact("save.pdf")

        await repository.save_artifact(artifact, collection_id)

        assert artifact.identity.value is not None

    @pytest.mark.asyncio
    async def test_get_artifact_by_id(self, repository: ArtifactMetadataRepository) -> None:
        """Test retrieving an artifact by identity."""
        collection_id = CollectionID.generate()
        artifact = self._artifact("get-by-id.pdf")

        await repository.save_artifact(artifact, collection_id)
        retrieved = await repository.get_artifact_by_id(artifact.identity)

        assert retrieved is not None
        assert retrieved.identity.value == artifact.identity.value

    @pytest.mark.asyncio
    async def test_get_artifacts_by_collection_id(
        self,
        repository: ArtifactMetadataRepository,
    ) -> None:
        """Test retrieving all artifacts in a collection."""
        collection_id = CollectionID.generate()
        artifact = self._artifact("in-collection.pdf")

        await repository.save_artifact(artifact, collection_id)
        artifacts = await repository.get_artifacts_by_collection_id(collection_id)

        assert len(artifacts) >= 1

    @pytest.mark.asyncio
    async def test_delete_artifact(self, repository: ArtifactMetadataRepository) -> None:
        """Test deleting an artifact by ID."""
        collection_id = CollectionID.generate()
        artifact = self._artifact("to-delete.pdf")

        await repository.save_artifact(artifact, collection_id)
        await repository.delete_artifact(artifact.identity)
        retrieved = await repository.get_artifact_by_id(artifact.identity)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_artifact_not_found(self, repository: ArtifactMetadataRepository) -> None:
        """Test retrieving non-existent artifact returns None."""
        fake_id = ArtifactID.generate()
        retrieved = await repository.get_artifact_by_id(fake_id)

        assert retrieved is None
