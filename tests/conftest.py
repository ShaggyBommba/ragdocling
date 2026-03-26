import pytest

from dacke.domain.aggregates.artifact import Artifact
from dacke.domain.aggregates.collection import Collection
from dacke.domain.aggregates.workspace import Workspace
from dacke.domain.values.artifact import (
    ArtifactID,
    ArtifactMetadata,
    ObjectAddress,
    StoragePath,
)
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID


@pytest.fixture
def workspace_id() -> WorkspaceID:
    """Generate a random workspace ID."""
    return WorkspaceID.generate()


@pytest.fixture
def workspace_id_from_name() -> WorkspaceID:
    """Create a deterministic workspace ID from a name."""
    return WorkspaceID.from_name("test-workspace")


@pytest.fixture
def collection_id(workspace_id: WorkspaceID) -> CollectionID:
    """Generate a random collection ID."""
    return CollectionID.from_name("test-collection", workspace_id)


@pytest.fixture
def artifact_id() -> ArtifactID:
    """Generate a random artifact ID."""
    return ArtifactID.generate()


@pytest.fixture
def artifact_metadata() -> ArtifactMetadata:
    """Create sample artifact metadata."""
    return ArtifactMetadata.create(
        filename="sample.pdf",
        source="test",
        size_bytes=1024,
        mime_type="application/pdf",
        checksum="test-checksum",
        author="test-author",
    )


@pytest.fixture
def storage_path() -> StoragePath:
    """Create a sample storage path."""
    return StoragePath(bucket="test-bucket", prefix="test/documents")


@pytest.fixture
def object_address(storage_path: StoragePath) -> ObjectAddress:
    """Create a sample object address."""
    return ObjectAddress(path=storage_path, filename="sample.pdf")


@pytest.fixture
def artifact(
    artifact_metadata: ArtifactMetadata, object_address: ObjectAddress, collection_id: CollectionID
) -> Artifact:
    """Create a sample artifact."""
    return Artifact.create(
        metadata=artifact_metadata, address=object_address, collection_id=collection_id
    )


@pytest.fixture
def artifact_with_content(
    artifact_metadata: ArtifactMetadata, object_address: ObjectAddress, collection_id: CollectionID
) -> Artifact:
    """Create a sample artifact with content."""
    content = b"Sample PDF content for testing"
    return Artifact.create(
        collection_id=collection_id,
        metadata=artifact_metadata,
        address=object_address,
        content=content,
    )


@pytest.fixture
def collection(workspace_id: WorkspaceID) -> Collection:
    """Create a sample collection."""
    return Collection.create("test-collection", workspace_id)


@pytest.fixture
def workspace() -> Workspace:
    """Create a sample workspace."""
    return Workspace.create("test-workspace")
