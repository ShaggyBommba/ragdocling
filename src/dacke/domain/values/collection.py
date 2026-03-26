"""Collection value objects — CollectionID."""

from dataclasses import dataclass
from uuid import UUID, uuid4, uuid5

from dacke.domain.values.workspace import WorkspaceID


@dataclass(frozen=True)
class CollectionID:
    """
    Collection identity — UUID4 (random) if not generated from a name.
    """

    value: UUID

    @classmethod
    def generate(cls) -> "CollectionID":
        """Generate a new random CollectionID."""
        return cls(value=uuid4())

    @classmethod
    def from_name(
        cls,
        name: str,
        workspace_id: WorkspaceID,
    ) -> "CollectionID":
        """Generate a deterministic CollectionID from a name and workspace ID."""
        return cls(value=uuid5(workspace_id.value, name.lower().strip()))

    @classmethod
    def from_hex(cls, value: str) -> "CollectionID":
        """Create a CollectionID from a UUID hex string."""
        try:
            return cls(value=UUID(hex=value))
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid UUID hex string") from e

    def __str__(self) -> str:
        """Returns the 32-character hexadecimal string without hyphens."""
        return self.value.hex

    def __repr__(self) -> str:
        return str(self.value)
