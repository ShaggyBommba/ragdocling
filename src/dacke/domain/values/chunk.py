from dataclasses import dataclass
from uuid import UUID, uuid4, uuid5

from pydantic import AnyUrl
from typing_extensions import TypedDict

from dacke.domain.values.document import DocumentID


@dataclass(frozen=True, slots=True)
class ChunkID:
    """Value object representing a unique chunk identifier."""

    value: UUID

    @classmethod
    def generate(cls) -> "ChunkID":
        """Generate a new random ChunkID."""
        return cls(value=uuid4())

    @classmethod
    def from_ref(cls, ref: str, namespace: DocumentID) -> "ChunkID":
        """Generate a deterministic ChunkID from a reference string and a document namespace."""
        return cls(value=uuid5(namespace.value, ref.lower().strip()))

    @classmethod
    def from_hex(cls, value: str) -> "ChunkID":
        """Create a ChunkID from a UUID hex string."""
        try:
            return cls(value=UUID(hex=value))
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid UUID hex string") from e

    def __str__(self) -> str:
        """Returns the 32-character hexadecimal string without hyphens."""
        return self.value.hex

    def __repr__(self) -> str:
        return str(self.value)


# typed metadata
class ChunkMetadata(TypedDict):
    """TypedDict for chunk metadata."""

    origin: AnyUrl
    order: int | None
    pages: list[int] | None
    title: str | None
    tags: list[str] | None
    urls: list[str] | None
    positive_queries: list[str] | None
    negative_queries: list[str] | None
