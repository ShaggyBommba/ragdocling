from dataclasses import dataclass
from uuid import UUID, uuid4, uuid5

from typing_extensions import TypedDict

from dacke.domain.values.pipeline import PipelineID


@dataclass(frozen=True, slots=True)
class DocumentID:
    """Value object representing a unique document identifier."""

    value: UUID

    @classmethod
    def generate(cls) -> "DocumentID":
        """Generate a new random DocumentID."""
        return cls(value=uuid4())

    @classmethod
    def from_ref(cls, ref: str, pipeline_id: PipelineID) -> "DocumentID":
        """Generate a deterministic DocumentID from a reference string and a pipeline namespace."""
        return cls(value=uuid5(pipeline_id.value, ref.lower().strip()))

    @classmethod
    def from_hex(cls, value: str) -> "DocumentID":
        """Create a DocumentID from a UUID hex string."""
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
class DocumentMetadata(TypedDict):
    """TypedDict for document metadata."""

    title: str
    source_url: str
