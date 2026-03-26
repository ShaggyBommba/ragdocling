"""Pipeline value objects — PipelineID."""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4, uuid5


@dataclass(frozen=True)
class PipelineID:
    """
    Pipeline identity — UUID4 (random) if not generated from a name.
    """

    value: UUID

    @classmethod
    def generate(cls) -> "PipelineID":
        """Generate a new random PipelineID."""
        return cls(value=uuid4())

    @classmethod
    def from_hash(cls, hash_value: str, collection_id: UUID) -> "PipelineID":
        """Generate a deterministic PipelineID from a hash and collection ID."""
        return cls(value=uuid5(collection_id, hash_value))

    @classmethod
    def from_hex(cls, value: str) -> "PipelineID":
        """Create a PipelineID from a UUID hex string."""
        try:
            return cls(value=UUID(hex=value))
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid UUID hex string") from e

    def __str__(self) -> str:
        """Returns the 32-character hexadecimal string without hyphens."""
        return self.value.hex

    def __repr__(self) -> str:
        return str(self.value)


class PipelineLifecycle(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    ARCHIVED = "archived"
