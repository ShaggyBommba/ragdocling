from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from dacke.domain.exceptions import DomainError
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID


class Collection(BaseModel):
    """
    Aggregate Root representing a collection of artifacts.

    A collection is an independent aggregate that manages artifacts.
    It enforces constraints on file count, size, and uniqueness.

    Attributes:
        identity: The unique identifier for the collection.
        workspace_id: The workspace this collection belongs to.
        name: The name of the collection.
        artifact_ids: List of artifact identities in this collection.
        created_at: The creation timestamp of the collection.
        updated_at: The last update timestamp of the collection.
        max_count_files: Maximum number of artifacts allowed in the collection.
        max_file_size_kb: Maximum size (in KB) for individual artifacts.

    Invariants:
        - Identity must be unique globally.
        - Artifact IDs list cannot contain duplicates.
        - Artifact count must not exceed max_count_files.
        - updated_at must be >= created_at.
        - Timestamps must reflect actual state changes.
    """

    identity: CollectionID
    workspace_id: WorkspaceID
    name: str
    artifact_ids: list[ArtifactID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    max_count_files: int = Field(default=100)
    max_file_size_kb: float = Field(default=10240.0)

    @classmethod
    def create(
        cls,
        name: str,
        workspace_id: WorkspaceID,
    ) -> "Collection":
        return cls(
            identity=CollectionID.from_name(name, workspace_id),
            workspace_id=workspace_id,
            name=name,
        )

    def update_name(self, name: str) -> None:
        self.name = name
        self.updated_at = datetime.now()

    def add_artifact(self, artifact_id: ArtifactID, size_kb: float) -> None:
        if self.find_artifact_by_identity(artifact_id):
            raise DomainError("Artifact already exists")

        if self.artifact_count() >= self.max_count_files:
            raise DomainError("Collection is full")

        if size_kb > self.max_file_size_kb:
            raise DomainError("Artifact is too large")

        self.artifact_ids.append(artifact_id)
        self.updated_at = datetime.now()

    def remove_artifact(self, artifact_id: ArtifactID) -> None:
        if not self.find_artifact_by_identity(artifact_id):
            raise DomainError("Artifact does not exist")

        self.artifact_ids.remove(artifact_id)
        self.updated_at = datetime.now()

    def find_artifact_by_identity(
        self, artifact_id: ArtifactID
    ) -> Optional[ArtifactID]:
        for aid in self.artifact_ids:
            if aid == artifact_id:
                return aid
        return None

    def artifact_count(self) -> int:
        return len(self.artifact_ids)
