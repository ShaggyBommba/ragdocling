"""Workspace value objects — WorkspaceID."""

from dataclasses import dataclass
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5


@dataclass(frozen=True)
class WorkspaceID:
    """
    Workspace identity — UUID4 (random) if not generated from a name.
    """

    value: UUID

    @classmethod
    def generate(cls) -> "WorkspaceID":
        """Generate a new random WorkspaceID."""
        return cls(value=uuid4())

    @classmethod
    def from_name(cls, name: str) -> "WorkspaceID":
        """Generate a deterministic WorkspaceID from a name."""
        return cls(value=uuid5(NAMESPACE_DNS, name.lower().strip()))

    @classmethod
    def from_hex(cls, value: str) -> "WorkspaceID":
        """Create a WorkspaceID from a UUID hex string."""
        try:
            return cls(value=UUID(hex=value))
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid UUID hex string") from e

    def __str__(self) -> str:
        """Returns the 32-character hexadecimal string without hyphens."""
        return self.value.hex

    def __repr__(self) -> str:
        return str(self.value)
