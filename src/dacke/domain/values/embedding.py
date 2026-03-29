from dataclasses import dataclass
from uuid import UUID, uuid5

from typing_extensions import TypedDict

from dacke.domain.values.chunk import ChunkID


class EmbeddingMetadata(TypedDict):
    """Metadata captured at embedding time."""

    model: str
    dimensions: int
    prompt_tokens: int | None


@dataclass(frozen=True, slots=True)
class EmbeddingID:
    """Value object representing a unique embedding identifier.

    Deterministic: derived from the chunk it was produced from,
    so re-embedding the same chunk yields the same ID.
    """

    value: UUID

    @classmethod
    def from_chunk(cls, chunk_id: ChunkID) -> "EmbeddingID":
        """Generate a deterministic EmbeddingID scoped to a chunk."""
        namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace
        return cls(value=uuid5(namespace, str(chunk_id)))

    @classmethod
    def from_hex(cls, value: str) -> "EmbeddingID":
        try:
            return cls(value=UUID(hex=value))
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid UUID hex string") from e

    def __str__(self) -> str:
        return self.value.hex

    def __repr__(self) -> str:
        return str(self.value)
