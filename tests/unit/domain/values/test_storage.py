import pytest

from dacke.domain.values.artifact import Blob, ObjectAddress, StoragePath


class TestStoragePath:
    def test_create_storage_path(self) -> None:
        path = StoragePath(bucket="my-bucket", prefix="documents/2024")
        assert path.bucket == "my-bucket"
        assert path.prefix == "documents/2024"

    def test_create_storage_path_empty_prefix(self) -> None:
        path = StoragePath(bucket="my-bucket", prefix="")
        assert path.bucket == "my-bucket"
        assert path.prefix == ""

    def test_at_appends_to_prefix(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        new_path = path.at("2024", "january")
        assert new_path.bucket == "bucket"
        assert "2024" in new_path.prefix
        assert "january" in new_path.prefix

    def test_at_with_empty_prefix(self) -> None:
        path = StoragePath(bucket="bucket", prefix="")
        new_path = path.at("docs", "file.pdf")
        assert "docs" in new_path.prefix
        assert "file.pdf" in new_path.prefix

    def test_at_single_part(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        new_path = path.at("subfolder")
        assert "docs" in new_path.prefix
        assert "subfolder" in new_path.prefix

    def test_parent_goes_up_one_level(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs/2024/january")
        parent = path.parent()
        assert parent.bucket == "bucket"
        assert "january" not in parent.prefix
        assert "2024" in parent.prefix

    def test_parent_at_root_returns_self(self) -> None:
        path = StoragePath(bucket="bucket", prefix="")
        parent = path.parent()
        assert parent.prefix == ""

    def test_parent_single_level(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        parent = path.parent()
        assert parent.prefix == ""

    def test_resolve_creates_object_address(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = path.resolve("file.pdf")
        assert address.path == path
        assert address.filename == "file.pdf"


class TestObjectAddress:
    def test_create_object_address(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        assert address.path == path
        assert address.filename == "file.pdf"
        assert address.version_id is None

    def test_create_object_address_with_version(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf", version_id="v123")
        assert address.version_id == "v123"

    def test_key_combines_prefix_and_filename(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs/2024")
        address = ObjectAddress(path=path, filename="file.pdf")
        assert "docs/2024" in address.key
        assert "file.pdf" in address.key

    def test_key_without_prefix(self) -> None:
        path = StoragePath(bucket="bucket", prefix="")
        address = ObjectAddress(path=path, filename="file.pdf")
        assert address.key == "file.pdf"

    def test_from_uri_parses_s3_uri(self) -> None:
        uri = "s3://my-bucket/documents/2024/file.pdf"
        address = ObjectAddress.from_uri(uri)
        assert address.path.bucket == "my-bucket"
        assert "documents/2024" in address.path.prefix
        assert address.filename == "file.pdf"

    def test_from_uri_without_prefix(self) -> None:
        uri = "s3://bucket/file.pdf"
        address = ObjectAddress.from_uri(uri)
        assert address.path.bucket == "bucket"
        assert address.path.prefix == ""
        assert address.filename == "file.pdf"

    def test_from_uri_deep_nesting(self) -> None:
        uri = "s3://bucket/a/b/c/d/e/file.pdf"
        address = ObjectAddress.from_uri(uri)
        assert address.path.bucket == "bucket"
        assert "a/b/c/d/e" in address.path.prefix
        assert address.filename == "file.pdf"

    def test_from_uri_raises_on_invalid_uri(self) -> None:
        with pytest.raises(ValueError):
            ObjectAddress.from_uri("http://invalid.com/file.pdf")

    def test_from_uri_raises_on_non_s3_scheme(self) -> None:
        with pytest.raises(ValueError):
            ObjectAddress.from_uri("gs://bucket/file.pdf")

    def test_s3_uri_property(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        assert address.s3_uri.startswith("s3://")
        assert "bucket" in address.s3_uri
        assert "file.pdf" in address.s3_uri

    def test_s3_uri_without_prefix(self) -> None:
        path = StoragePath(bucket="bucket", prefix="")
        address = ObjectAddress(path=path, filename="file.pdf")
        uri = address.s3_uri
        assert uri == "s3://bucket/file.pdf"

    def test_s3_uri_with_version_id(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf", version_id="v123")
        assert "versionId=v123" in address.s3_uri

    def test_str_returns_s3_uri(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        assert str(address) == address.s3_uri


class TestBlob:
    def test_create_blob(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        content = b"PDF content here"
        blob = Blob(address=address, content=content, media_type="application/pdf")
        assert blob.address == address
        assert blob.content == content
        assert blob.media_type == "application/pdf"

    def test_create_blob_default_media_type(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.bin")
        blob = Blob(address=address, content=b"binary")
        assert blob.media_type == "application/octet-stream"

    def test_size_bytes_property(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        content = b"test content"
        blob = Blob(address=address, content=content)
        assert blob.size_bytes == len(content)

    def test_size_bytes_empty_content(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        blob = Blob(address=address, content=b"")
        assert blob.size_bytes == 0

    def test_size_bytes_large_content(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        content = b"x" * (1024 * 1024)
        blob = Blob(address=address, content=content)
        assert blob.size_bytes == 1024 * 1024

    def test_blob_is_hashable(self) -> None:
        path = StoragePath(bucket="bucket", prefix="docs")
        address = ObjectAddress(path=path, filename="file.pdf")
        blob1 = Blob(address=address, content=b"content")
        blob2 = Blob(address=address, content=b"content")
        # Should be able to use in sets/dicts
        blob_set = {blob1, blob2}
        assert len(blob_set) == 1
