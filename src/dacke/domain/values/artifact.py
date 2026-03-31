from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from pydantic import AnyUrl

from dacke.domain.values.collection import CollectionID
from dacke.domain.values.pipeline import PipelineID


@dataclass(frozen=True, slots=True)
class ArtifactID:
    """Value object representing a unique artifact identifier."""

    value: UUID

    @classmethod
    def generate(cls) -> "ArtifactID":
        """Generate a new random ArtifactID."""
        return cls(value=uuid4())

    @classmethod
    def from_checksum(
        cls, checksum: str, namespace: CollectionID | PipelineID
    ) -> "ArtifactID":
        """Generate a deterministic ArtifactID from a checksum and namespace."""
        return cls(value=uuid5(namespace.value, checksum.lower().strip()))

    @classmethod
    def from_hex(cls, value: str) -> "ArtifactID":
        """Create an ArtifactID from a UUID hex string."""
        try:
            return cls(value=UUID(hex=value))
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid UUID hex string") from e

    def __str__(self) -> str:
        """Returns the 32-character hexadecimal string without hyphens."""
        return self.value.hex

    def __repr__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Value object containing artifact metadata information."""

    filename: str
    source: AnyUrl
    size_bytes: int
    mime_type: str
    checksum: str
    author: str = "unknown"

    @classmethod
    def create(
        cls,
        filename: str,
        source: AnyUrl,
        size_bytes: int,
        mime_type: str,
        checksum: str,
        author: str = "unknown",
    ) -> "ArtifactMetadata":
        """Create ArtifactMetadata."""
        return cls(
            filename=filename,
            source=source,
            size_bytes=size_bytes,
            mime_type=mime_type,
            checksum=checksum,
            author=author,
        )

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024

    def __str__(self) -> str:
        return f"{self.filename} ({self.size_mb:.2f} MB, {self.mime_type})"

    def __repr__(self) -> str:
        return f"ArtifactMetadata(filename={self.filename!r}, source={self.source!r}, size_bytes={self.size_bytes}, mime_type={self.mime_type!r}, checksum={self.checksum!r})"


@dataclass(frozen=True, slots=True)
class StoragePath:  # Renamed from Prefix
    """Represents a location path within a specific cloud bucket."""

    bucket: str
    prefix: str = ""

    def at(self, *parts: str) -> "StoragePath":
        """Returns a new path deeper within the current prefix."""
        new_prefix = (
            str(Path(self.prefix) / Path(*parts)) if self.prefix else "/".join(parts)
        )
        return StoragePath(bucket=self.bucket, prefix=new_prefix)

    def parent(self) -> "StoragePath":
        """Returns the path one level up."""
        if not self.prefix:
            return self
        parent_path = str(Path(self.prefix).parent)
        return StoragePath(
            bucket=self.bucket, prefix="" if parent_path == "." else parent_path
        )

    def resolve(self, filename: str) -> "ObjectAddress":
        """Combines the current path with a filename to create a specific address."""
        return ObjectAddress(path=self, filename=filename)


@dataclass(frozen=True, slots=True)
class ObjectAddress:  # Renamed from ObjectLocation
    """The full 'coordinates' of an object in S3/MinIO."""

    path: StoragePath
    filename: str
    version_id: str | None = None

    @property
    def key(self) -> str:
        """The complete S3 object key (prefix + filename)."""
        if self.path.prefix:
            prefix = self.path.prefix.rstrip("/")
            return f"{prefix}/{self.filename}"
        return self.filename

    @classmethod
    def create(cls, bucket: str, prefix: str, filename: str) -> "ObjectAddress":
        """Creates an ObjectAddress from individual components."""
        return cls(path=StoragePath(bucket, prefix), filename=filename)

    @classmethod
    def from_uri(cls, uri: str) -> "ObjectAddress":
        """Parses s3://bucket/prefix/file format."""
        if not uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI")

        parts = uri.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        full_path = parts[1] if len(parts) > 1 else ""

        path_parts = full_path.rsplit("/", 1)
        prefix = path_parts[0] if len(path_parts) > 1 else ""
        filename = path_parts[-1]

        return cls(path=StoragePath(bucket, prefix), filename=filename)

    @property
    def bucket(self) -> str:
        return self.path.bucket

    @property
    def prefix(self) -> str:
        return self.path.prefix

    @property
    def s3_uri(self) -> str:
        uri = f"s3://{self.path.bucket}/{self.key}"
        if self.version_id:
            uri += f"?versionId={self.version_id}"
        return uri

    def __str__(self) -> str:
        return self.s3_uri


@dataclass(frozen=True, slots=True)
class Blob:
    """A physical representation of the content and its storage address."""

    address: ObjectAddress
    content: bytes
    media_type: str = "application/octet-stream"

    @property
    def size_bytes(self) -> int:
        return len(self.content)
