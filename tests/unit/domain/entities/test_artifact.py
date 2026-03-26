import io

import pytest

from dacke.domain.aggregates.artifact import Artifact
from dacke.domain.exceptions import DomainError
from dacke.domain.values.artifact import (
    ArtifactID,
    ArtifactMetadata,
    ObjectAddress,
    StoragePath,
)
from dacke.domain.values.collection import CollectionID


class TestArtifactCreation:
    @pytest.fixture
    def artifact_metadata(self) -> ArtifactMetadata:
        return ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=0,
            mime_type="application/pdf",
            checksum="abc123",
        )

    @pytest.fixture
    def artifact_address(self) -> ObjectAddress:
        path = StoragePath(bucket="test-bucket", prefix="documents")
        return ObjectAddress(path=path, filename="document.pdf")

    def test_create_artifact(
        self, artifact_metadata: ArtifactMetadata, artifact_address: ObjectAddress
    ) -> None:
        artifact = Artifact.create(
            collection_id=CollectionID.generate(),
            metadata=artifact_metadata,
            address=artifact_address,
        )
        assert artifact.metadata == artifact_metadata
        assert artifact.address == artifact_address
        assert artifact.has_content is False

    def test_create_artifact_with_content(
        self, artifact_metadata: ArtifactMetadata, artifact_address: ObjectAddress
    ) -> None:
        content = b"PDF content"
        artifact = Artifact.create(
            collection_id=CollectionID.generate(),
            metadata=artifact_metadata,
            address=artifact_address,
            content=content,
        )
        assert artifact.has_content is True
        assert artifact.content == content
        assert artifact.metadata.size_bytes == len(content)

    def test_artifact_identity_from_address(
        self, artifact_metadata: ArtifactMetadata, artifact_address: ObjectAddress
    ) -> None:
        collection_id = CollectionID.generate()

        artifact = Artifact.create(
            collection_id=collection_id,
            metadata=artifact_metadata,
            address=artifact_address,
        )
        expected_identity = ArtifactID.from_checksum(
            checksum=artifact_metadata.checksum, namespace=collection_id
        )
        assert artifact.identity == expected_identity


class TestArtifactContent:
    @pytest.fixture
    def artifact(self) -> Artifact:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=0,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        return Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )

    def test_set_content_from_bytes(self, artifact: Artifact) -> None:
        content = b"New content"
        artifact.set_content(content)
        assert artifact.content == content
        assert artifact.metadata.size_bytes == len(content)

    def test_set_content_from_bytesio(self, artifact: Artifact) -> None:
        content = b"BytesIO content"
        bytes_io = io.BytesIO(content)
        artifact.set_content(bytes_io)
        assert artifact.content == content
        assert artifact.metadata.size_bytes == len(content)

    def test_set_content_from_bytesio_with_position(self, artifact: Artifact) -> None:
        content = b"BytesIO content"
        bytes_io = io.BytesIO(content)
        bytes_io.seek(5)  # Move position
        artifact.set_content(bytes_io)
        assert artifact.content == content  # Should read from beginning

    def test_set_content_updates_timestamp(self, artifact: Artifact) -> None:
        original_updated_at = artifact.updated_at
        artifact.set_content(b"content")
        assert artifact.updated_at > original_updated_at

    def test_set_content_updates_metadata_size(self, artifact: Artifact) -> None:
        original_size = artifact.metadata.size_bytes
        new_content = b"x" * 2048
        artifact.set_content(new_content)
        assert artifact.metadata.size_bytes == 2048
        assert artifact.metadata.size_bytes != original_size

    def test_content_property_raises_when_not_loaded(self, artifact: Artifact) -> None:
        with pytest.raises(DomainError):
            _ = artifact.content

    def test_has_content_property(self, artifact: Artifact) -> None:
        assert artifact.has_content is False
        artifact.set_content(b"content")
        assert artifact.has_content is True


class TestArtifactBlob:
    @pytest.fixture
    def artifact_with_content(self) -> Artifact:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=0,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        content = b"PDF content"
        return Artifact.create(
            collection_id=CollectionID.generate(),
            metadata=metadata,
            address=address,
            content=content,
        )

    @pytest.fixture
    def artifact_without_content(self) -> Artifact:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=0,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        return Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )

    def test_as_blob_converts_to_blob(self, artifact_with_content: Artifact) -> None:
        blob = artifact_with_content.as_blob
        assert blob.address == artifact_with_content.address
        assert blob.content == artifact_with_content.content
        assert blob.media_type == artifact_with_content.metadata.mime_type

    def test_as_blob_raises_when_content_not_loaded(
        self, artifact_without_content: Artifact
    ) -> None:
        with pytest.raises(DomainError):
            _ = artifact_without_content.as_blob


class TestArtifactSizes:
    @pytest.fixture
    def artifact_1kb(self) -> Artifact:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        return Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )

    @pytest.fixture
    def artifact_1mb(self) -> Artifact:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024 * 1024,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        return Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )

    def test_size_kb_property(self, artifact_1kb: Artifact) -> None:
        assert artifact_1kb.size_kb == 1.0

    def test_size_mb_property(self, artifact_1mb: Artifact) -> None:
        assert artifact_1mb.size_mb == 1.0

    def test_size_kb_fractional(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=512,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        artifact = Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )
        assert artifact.size_kb == 0.5


class TestArtifactInvariants:
    def test_artifact_created_at_before_updated_at(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        artifact = Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )
        assert artifact.created_at <= artifact.updated_at

    def test_artifact_address_matches_metadata_filename(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
        )
        path = StoragePath(bucket="test-bucket", prefix="documents")
        address = ObjectAddress(path=path, filename="document.pdf")
        artifact = Artifact.create(
            collection_id=CollectionID.generate(), metadata=metadata, address=address
        )
        assert artifact.address.filename == artifact.metadata.filename
