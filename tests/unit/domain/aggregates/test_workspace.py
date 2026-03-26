import pytest
from dacke.domain.aggregates.collection import Collection
from dacke.domain.aggregates.workspace import Workspace
from dacke.domain.exceptions import DomainError
from dacke.domain.values.collection import CollectionID


class TestWorkspaceCreation:
    def test_create_workspace_from_name(self) -> None:
        workspace = Workspace.create("Test Workspace")
        assert workspace.identity is not None
        assert workspace.collection_count() == 0

    def test_deterministic_workspace_id_from_name(self) -> None:
        ws1 = Workspace.create("MyWorkspace")
        ws2 = Workspace.create("MyWorkspace")
        assert ws1.identity.value == ws2.identity.value

    def test_different_workspace_names_produce_different_ids(self) -> None:
        ws1 = Workspace.create("Workspace1")
        ws2 = Workspace.create("Workspace2")
        assert ws1.identity.value != ws2.identity.value

    def test_workspace_created_at_before_updated_at(self) -> None:
        workspace = Workspace.create("Test Workspace")
        assert workspace.created_at <= workspace.updated_at


class TestWorkspaceCollectionManagement:
    @pytest.fixture
    def workspace(self) -> Workspace:
        return Workspace.create("My Workspace")

    def test_add_collection_to_workspace(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        new_collection = Collection.create("New Collection", workspace_id)
        workspace.add_collection(new_collection.identity)
        assert workspace.collection_count() == 1
        assert (
            workspace.find_collection_by_identity(new_collection.identity) is not None
        )

    def test_add_multiple_collections(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        for i in range(3):
            collection = Collection.create(f"Collection{i}", workspace_id)
            workspace.add_collection(collection.identity)

        assert workspace.collection_count() == 3

    def test_add_duplicate_collection_identity_raises_error(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        collection1 = Collection.create("Docs1", workspace_id)
        collection2 = Collection.create("Docs1", workspace_id)

        workspace.add_collection(collection1.identity)
        with pytest.raises(
            DomainError, match="Collection with identity .* already exists"
        ):
            workspace.add_collection(collection2.identity)

    def test_remove_collection_from_workspace(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        collection = Collection.create("ToRemove", workspace_id)
        workspace.add_collection(collection.identity)

        workspace.remove_collection(collection.identity)
        assert workspace.find_collection_by_identity(collection.identity) is None

    def test_remove_nonexistent_collection_raises_error(self, workspace: Workspace) -> None:
        fake_id = CollectionID.generate()
        with pytest.raises(DomainError, match="Collection with identity .* not found"):
            workspace.remove_collection(fake_id)

    def test_workspace_empty_after_removing_all_collections(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        collection = Collection.create("ToRemove", workspace_id)
        workspace.add_collection(collection.identity)
        workspace.remove_collection(collection.identity)
        assert workspace.collection_count() == 0


class TestWorkspaceTimestamps:
    @pytest.fixture
    def workspace(self) -> Workspace:
        return Workspace.create("My Workspace")

    def test_add_collection_updates_workspace_timestamp(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        collection = Collection.create("New", workspace_id)

        original_updated_at = workspace.updated_at
        workspace.add_collection(collection.identity)

        assert workspace.updated_at > original_updated_at

    def test_remove_collection_updates_workspace_timestamp(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        collection = Collection.create("ToRemove", workspace_id)
        workspace.add_collection(collection.identity)

        original_updated_at = workspace.updated_at
        workspace.remove_collection(collection.identity)

        assert workspace.updated_at > original_updated_at


class TestWorkspaceCollectionLookup:
    @pytest.fixture
    def workspace(self) -> Workspace:
        return Workspace.create("My Workspace")

    def test_find_collection_by_identity(self, workspace: Workspace) -> None:
        workspace_id = workspace.identity
        collection = Collection.create("Search", workspace_id)
        workspace.add_collection(collection.identity)

        found = workspace.find_collection_by_identity(collection.identity)
        assert found == collection.identity

    def test_find_collection_by_identity_returns_none(self, workspace: Workspace) -> None:
        fake_id = CollectionID.generate()
        found = workspace.find_collection_by_identity(fake_id)
        assert found is None


class TestWorkspaceComplexScenarios:
    def test_workspace_with_multiple_collections(self) -> None:
        workspace = Workspace.create("Complex Workspace")
        workspace_id = workspace.identity

        for i in range(3):
            collection = Collection.create(f"Collection{i}", workspace_id)
            workspace.add_collection(collection.identity)

        assert workspace.collection_count() == 3

    def test_workspace_invariants_collection_uniqueness(self) -> None:
        workspace = Workspace.create("Test Workspace")
        workspace_id = workspace.identity

        collection1 = Collection.create("SameName", workspace_id)
        collection2 = Collection.create("SameName", workspace_id)

        workspace.add_collection(collection1.identity)

        with pytest.raises(DomainError):
            workspace.add_collection(collection2.identity)
