import pytest

from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID


class TestWorkspaceID:
    def test_generate_creates_random_id(self) -> None:
        id1 = WorkspaceID.generate()
        id2 = WorkspaceID.generate()
        assert id1.value != id2.value

    def test_from_name_creates_deterministic_id(self) -> None:
        id1 = WorkspaceID.from_name("my-workspace")
        id2 = WorkspaceID.from_name("my-workspace")
        assert id1.value == id2.value

    def test_from_name_case_insensitive(self) -> None:
        id1 = WorkspaceID.from_name("MyWorkspace")
        id2 = WorkspaceID.from_name("myworkspace")
        assert id1.value == id2.value

    def test_from_hex_parses_valid_uuid(self) -> None:
        hex_str = "550e8400e29b41d4a716446655440000"
        workspace_id = WorkspaceID.from_hex(hex_str)
        assert workspace_id.value.hex == hex_str

    def test_from_hex_raises_on_invalid_uuid(self) -> None:
        with pytest.raises(ValueError):
            WorkspaceID.from_hex("invalid-uuid")

    def test_str_returns_hex_without_hyphens(self) -> None:
        workspace_id = WorkspaceID.generate()
        assert str(workspace_id) == workspace_id.value.hex

    def test_repr_returns_uuid(self) -> None:
        workspace_id = WorkspaceID.generate()
        assert repr(workspace_id) == str(workspace_id.value)


class TestCollectionID:
    def test_generate_creates_random_id(self) -> None:
        id1 = CollectionID.generate()
        id2 = CollectionID.generate()
        assert id1.value != id2.value

    def test_from_name_requires_workspace_id(self) -> None:
        workspace_id = WorkspaceID.generate()
        id1 = CollectionID.from_name("docs", workspace_id)
        id2 = CollectionID.from_name("docs", workspace_id)
        assert id1.value == id2.value

    def test_from_name_different_workspace_ids_produce_different_ids(self) -> None:
        ws1 = WorkspaceID.generate()
        ws2 = WorkspaceID.generate()
        id1 = CollectionID.from_name("docs", ws1)
        id2 = CollectionID.from_name("docs", ws2)
        assert id1.value != id2.value

    def test_from_hex_parses_valid_uuid(self) -> None:
        hex_str = "550e8400e29b41d4a716446655440000"
        collection_id = CollectionID.from_hex(hex_str)
        assert collection_id.value.hex == hex_str

    def test_str_returns_hex_without_hyphens(self) -> None:
        collection_id = CollectionID.generate()
        assert str(collection_id) == collection_id.value.hex


class TestArtifactID:
    def test_generate_creates_random_id(self) -> None:
        id1 = ArtifactID.generate()
        id2 = ArtifactID.generate()
        assert id1.value != id2.value

    def test_from_address_creates_deterministic_id(self) -> None:
        address = "s3://bucket/prefix/file.pdf"
        namespace = CollectionID.generate()
        id1 = ArtifactID.from_checksum(address, namespace=namespace)
        id2 = ArtifactID.from_checksum(address, namespace=namespace)
        assert id1.value == id2.value

    def test_from_address_case_insensitive(self) -> None:
        namespace = CollectionID.generate()
        id1 = ArtifactID.from_checksum("S3://BUCKET/FILE.PDF", namespace=namespace)
        id2 = ArtifactID.from_checksum("s3://bucket/file.pdf", namespace=namespace)
        assert id1.value == id2.value

    def test_from_hex_parses_valid_uuid(self) -> None:
        hex_str = "550e8400e29b41d4a716446655440000"
        artifact_id = ArtifactID.from_hex(hex_str)
        assert artifact_id.value.hex == hex_str

    def test_str_returns_hex_without_hyphens(self) -> None:
        artifact_id = ArtifactID.generate()
        assert str(artifact_id) == artifact_id.value.hex
