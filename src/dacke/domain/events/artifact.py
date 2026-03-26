"""Domain events for artifact operations."""

from dataclasses import dataclass
from typing import Any, ClassVar

from dacke.domain.events.domain import DomainEvent
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID


@dataclass(frozen=True, kw_only=True)
class ArtifactUploadedEvent(DomainEvent):
    """Raised when an artifact is successfully uploaded."""

    EVENT_TOPIC: ClassVar[str] = "artifacts"
    EVENT_NAME: ClassVar[str] = "upload"

    artifact_id: ArtifactID
    collection_id: CollectionID

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "artifact_id": str(self.artifact_id),
            "collection_id": str(self.collection_id),
        }


@dataclass(frozen=True, kw_only=True)
class ArtifactDeletedEvent(DomainEvent):
    """Raised when an artifact is deleted."""

    EVENT_TOPIC: ClassVar[str] = "artifacts"
    EVENT_NAME: ClassVar[str] = "delete"

    artifact_id: ArtifactID
    collection_id: CollectionID

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "artifact_id": str(self.artifact_id),
            "collection_id": str(self.collection_id),
        }
