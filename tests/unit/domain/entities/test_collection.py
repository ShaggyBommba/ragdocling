import pytest

from dacke.domain.aggregates.collection import Collection
from dacke.domain.exceptions import DomainError
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.workspace import WorkspaceID


class TestCollectionCreation:
    @pytest.fixture
    def workspace_id(self) -> WorkspaceID:
        return WorkspaceID.generate()

    def test_create_collection(self, workspace_id: WorkspaceID) -> None:
        collection = Collection.create("Documents", workspace_id)
        assert collection.name == "Documents"
        assert collection.artifact_count() == 0

    def test_create_collection_with_deterministic_id(self, workspace_id: WorkspaceID) -> None:
        collection1 = Collection.create("Docs", workspace_id)
        collection2 = Collection.create("Docs", workspace_id)
        assert collection1.identity == collection2.identity

    def test_create_collection_different_names_different_ids(
        self, workspace_id: WorkspaceID
    ) -> None:
        collection1 = Collection.create("Docs1", workspace_id)
        collection2 = Collection.create("Docs2", workspace_id)
        assert collection1.identity != collection2.identity

    def test_create_collection_different_workspaces_different_ids(self) -> None:
        ws1 = WorkspaceID.generate()
        ws2 = WorkspaceID.generate()
        collection1 = Collection.create("Docs", ws1)
        collection2 = Collection.create("Docs", ws2)
        assert collection1.identity != collection2.identity


class TestCollectionArtifactOperations:
    @pytest.fixture
    def workspace_id(self) -> WorkspaceID:
        return WorkspaceID.generate()

    @pytest.fixture
    def collection(self, workspace_id: WorkspaceID) -> Collection:
        return Collection.create("My Collection", workspace_id)

    @pytest.fixture
    def artifact_id(self) -> ArtifactID:
        return ArtifactID.generate()

    def test_add_artifact_to_collection(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        collection.add_artifact(artifact_id, 1.0)
        assert collection.artifact_count() == 1
        assert collection.find_artifact_by_identity(artifact_id) == artifact_id

    def test_add_multiple_artifacts(self, collection: Collection) -> None:
        for _ in range(3):
            artifact_id = ArtifactID.generate()
            collection.add_artifact(artifact_id, 1.0)

        assert collection.artifact_count() == 3

    def test_add_duplicate_artifact_raises_error(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        collection.add_artifact(artifact_id, 1.0)
        with pytest.raises(DomainError, match="Artifact already exists"):
            collection.add_artifact(artifact_id, 1.0)

    def test_remove_artifact_from_collection(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        collection.add_artifact(artifact_id, 1.0)
        collection.remove_artifact(artifact_id)
        assert collection.artifact_count() == 0

    def test_remove_nonexistent_artifact_raises_error(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        with pytest.raises(DomainError, match="Artifact does not exist"):
            collection.remove_artifact(artifact_id)

    def test_find_artifact_by_identity(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        collection.add_artifact(artifact_id, 1.0)
        found = collection.find_artifact_by_identity(artifact_id)
        assert found == artifact_id

    def test_find_artifact_by_identity_returns_none(self, collection: Collection) -> None:
        artifact_id = ArtifactID.generate()
        found = collection.find_artifact_by_identity(artifact_id)
        assert found is None


class TestCollectionConstraints:
    @pytest.fixture
    def workspace_id(self) -> WorkspaceID:
        return WorkspaceID.generate()

    @pytest.fixture
    def collection(self, workspace_id: WorkspaceID) -> Collection:
        return Collection.create("My Collection", workspace_id)

    def test_add_artifact_exceeding_count_limit_raises_error(self, collection: Collection) -> None:
        collection.max_count_files = 1

        artifact_id1 = ArtifactID.generate()
        collection.add_artifact(artifact_id1, 1.0)

        artifact_id2 = ArtifactID.generate()
        with pytest.raises(DomainError, match="Collection is full"):
            collection.add_artifact(artifact_id2, 1.0)

    def test_add_artifact_exceeding_size_limit_raises_error(self, collection: Collection) -> None:
        collection.max_file_size_kb = 0.5

        artifact_id = ArtifactID.generate()
        with pytest.raises(DomainError, match="Artifact is too large"):
            collection.add_artifact(artifact_id, 1.0)

    def test_default_max_count_files(self, collection: Collection) -> None:
        assert collection.max_count_files == 100

    def test_default_max_file_size_kb(self, collection: Collection) -> None:
        assert collection.max_file_size_kb == 10240.0


class TestCollectionNameManagement:
    @pytest.fixture
    def workspace_id(self) -> WorkspaceID:
        return WorkspaceID.generate()

    @pytest.fixture
    def collection(self, workspace_id: WorkspaceID) -> Collection:
        return Collection.create("Original Name", workspace_id)

    def test_update_collection_name(self, collection: Collection) -> None:
        collection.update_name("New Name")
        assert collection.name == "New Name"

    def test_update_collection_name_updates_timestamp(self, collection: Collection) -> None:
        original_updated_at = collection.updated_at
        collection.update_name("New Name")
        assert collection.updated_at > original_updated_at


class TestCollectionTimestamps:
    @pytest.fixture
    def workspace_id(self) -> WorkspaceID:
        return WorkspaceID.generate()

    @pytest.fixture
    def collection(self, workspace_id: WorkspaceID) -> Collection:
        return Collection.create("My Collection", workspace_id)

    @pytest.fixture
    def artifact_id(self) -> ArtifactID:
        return ArtifactID.generate()

    def test_add_artifact_updates_timestamp(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        original_updated_at = collection.updated_at
        collection.add_artifact(artifact_id, 1.0)
        assert collection.updated_at > original_updated_at

    def test_remove_artifact_updates_timestamp(
        self, collection: Collection, artifact_id: ArtifactID
    ) -> None:
        collection.add_artifact(artifact_id, 1.0)
        original_updated_at = collection.updated_at
        collection.remove_artifact(artifact_id)
        assert collection.updated_at > original_updated_at

    def test_created_at_before_updated_at(self, collection: Collection) -> None:
        assert collection.created_at <= collection.updated_at
