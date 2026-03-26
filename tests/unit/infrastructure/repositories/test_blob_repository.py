"""Tests for ArtifactRepository (MinIO)."""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from dacke.domain.aggregates.artifact import Artifact
from dacke.domain.values.artifact import (
    ArtifactMetadata,
    Blob,
    CollectionID,
    ObjectAddress,
    StoragePath,
)
from dacke.infrastructure.repositories.providers.minio.repo_artifact import (
    ArtifactBlobAcl,
    ArtifactBlobRepository,
)


class TestBlobArtifactAcl:
    """Test ArtifactAcl translation layer."""

    @pytest.fixture
    def artifact_metadata(self) -> ArtifactMetadata:
        return ArtifactMetadata(
            filename="test.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
            author="test_user",
        )

    @pytest.fixture
    def object_address(self, artifact_metadata: ArtifactMetadata) -> ObjectAddress:
        return ObjectAddress.create(
            bucket="test-bucket",
            prefix="documents/",
            filename=artifact_metadata.filename,
        )

    @pytest.fixture
    def blob(self, object_address: ObjectAddress) -> Blob:
        return Blob(
            address=object_address,
            content=b"test content",
            media_type="application/pdf",
        )

    def test_from_domain(self, blob: Blob) -> None:
        """Test converting Blob to dict ORM."""
        orm = ArtifactBlobAcl.from_domain(blob)
        assert orm.address == blob.address
        assert orm.content == blob.content
        assert orm.media_type == blob.media_type

    def test_to_domain(self, blob: Blob) -> None:
        """Test converting dict ORM to Blob."""
        orm = ArtifactBlobAcl.from_domain(blob)
        reconstructed = ArtifactBlobAcl.to_domain(orm)
        assert reconstructed.address == blob.address
        assert reconstructed.content == blob.content
        assert reconstructed.media_type == blob.media_type

    def test_roundtrip_conversion(self, blob: Blob) -> None:
        """Test roundtrip conversion Blob -> dict -> Blob."""
        orm = ArtifactBlobAcl.from_domain(blob)
        reconstructed = ArtifactBlobAcl.to_domain(orm)

        assert reconstructed.address == blob.address
        assert reconstructed.content == blob.content
        assert reconstructed.media_type == blob.media_type


class TestBlobArtifactRepository:
    """Test ArtifactRepository persistence operations."""

    @pytest_asyncio.fixture
    async def repository(self) -> AsyncIterator[ArtifactBlobRepository]:
        """Create repository instance with MinIO mock."""
        # TODO: Implement with actual MinIO client or mock
        repo = ArtifactBlobRepository(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        )
        yield repo
        await repo._disconnect()

    @pytest.fixture
    def artifact(self) -> Artifact:
        """Create a test artifact."""
        return Artifact.create(
            collection_id=CollectionID.generate(),
            metadata=ArtifactMetadata(
                filename="test.pdf",
                source="upload",
                size_bytes=1024,
                mime_type="application/pdf",
                checksum="abc123",
                author="test_user",
            ),
            address=ObjectAddress.create(
                bucket="test-bucket",
                prefix="documents/",
                filename="test.pdf",
            ),
        )

    @pytest.fixture
    def content(self) -> bytes:
        """Create test content."""
        return b"test content"

    @pytest.mark.asyncio
    async def test_save_blob(
        self, repository: ArtifactBlobRepository, artifact: Artifact, content: bytes
    ) -> None:
        """Test saving an artifact to MinIO."""
        artifact.set_content(content)
        blob = artifact.as_blob
        await repository.save_blob(blob)
        item = await repository.get_blob(artifact.address)
        assert item is not None
        assert item.content == content

    @pytest.mark.asyncio
    async def test_get_artifact_by_address(self, repository: ArtifactBlobRepository) -> None:
        """Test retrieving an artifact by address."""
        content = b"artifact-by-address"
        address = ObjectAddress.create(
            bucket="test-bucket",
            prefix="documents/",
            filename="by-address.pdf",
        )
        await repository.save_blob(
            Blob(address=address, content=content, media_type="application/pdf")
        )

        item = await repository.get_blob(address)

        assert item is not None
        assert item.address == address
        assert item.content == content

    @pytest.mark.asyncio
    async def test_delete_artifact(self, repository: ArtifactBlobRepository) -> None:
        """Test deleting an artifact from MinIO."""
        address = ObjectAddress.create(
            bucket="test-bucket",
            prefix="documents/",
            filename="to-delete.pdf",
        )
        await repository.save_blob(
            Blob(address=address, content=b"to delete", media_type="application/pdf")
        )

        await repository.delete_blob(address)

        item = await repository.get_blob(address)
        assert item is None

    @pytest.mark.asyncio
    async def test_list_artifacts_in_bucket(self, repository: ArtifactBlobRepository) -> None:
        """Test listing artifacts in a bucket."""
        prefix = "documents/listing"
        address_1 = ObjectAddress.create(
            bucket="test-bucket",
            prefix=prefix,
            filename="list-1.pdf",
        )
        address_2 = ObjectAddress.create(
            bucket="test-bucket",
            prefix=prefix,
            filename="list-2.pdf",
        )

        await repository.save_blob(
            Blob(address=address_1, content=b"content 1", media_type="application/pdf")
        )
        await repository.save_blob(
            Blob(address=address_2, content=b"content 2", media_type="application/pdf")
        )

        items = await repository.list_blobs_by_prefix(
            StoragePath(bucket="test-bucket", prefix=prefix)
        )
        keys = {item.address.key for item in items}

        assert address_1.key in keys
        assert address_2.key in keys

    @pytest.mark.asyncio
    async def test_artifact_not_found(self, repository: ArtifactBlobRepository) -> None:
        """Test retrieving non-existent artifact returns None."""
        missing_address = ObjectAddress.create(
            bucket="test-bucket",
            prefix="documents/",
            filename="missing-artifact.pdf",
        )

        item = await repository.get_blob(missing_address)

        assert item is None
