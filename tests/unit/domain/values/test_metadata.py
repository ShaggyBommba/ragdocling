from dacke.domain.values.artifact import ArtifactMetadata


class TestArtifactMetadata:
    def test_create_artifact_metadata(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
            author="john",
        )
        assert metadata.filename == "document.pdf"
        assert metadata.source == "upload"
        assert metadata.size_bytes == 1024
        assert metadata.mime_type == "application/pdf"
        assert metadata.checksum == "abc123"
        assert metadata.author == "john"

    def test_create_with_default_author(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
        )
        assert metadata.author == "unknown"

    def test_size_kb_property(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=2048,
            mime_type="application/pdf",
            checksum="abc",
        )
        assert metadata.size_kb == 2.0

    def test_size_mb_property(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=1024 * 1024,
            mime_type="application/pdf",
            checksum="abc",
        )
        assert metadata.size_mb == 1.0

    def test_size_kb_fractional(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=512,
            mime_type="application/pdf",
            checksum="abc",
        )
        assert metadata.size_kb == 0.5

    def test_size_mb_fractional(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=512 * 1024,
            mime_type="application/pdf",
            checksum="abc",
        )
        assert metadata.size_mb == 0.5

    def test_str_representation(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=1024 * 1024,
            mime_type="application/pdf",
            checksum="abc",
        )
        assert "doc.pdf" in str(metadata)
        assert "1.00 MB" in str(metadata)
        assert "application/pdf" in str(metadata)

    def test_repr_representation(self) -> None:
        metadata = ArtifactMetadata.create(
            filename="document.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc123",
        )
        repr_str = repr(metadata)
        assert "document.pdf" in repr_str
        assert "upload" in repr_str
        assert "application/pdf" in repr_str

    def test_metadata_is_hashable(self) -> None:
        metadata1 = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc",
        )
        metadata2 = ArtifactMetadata.create(
            filename="doc.pdf",
            source="upload",
            size_bytes=1024,
            mime_type="application/pdf",
            checksum="abc",
        )
        # Should be able to use in sets/dicts
        metadata_set = {metadata1, metadata2}
        assert len(metadata_set) == 1
