from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from dacke.domain.exceptions import DomainError
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID


class Workspace(BaseModel):
    """
    Aggregate Root representing a workspace.

    A workspace is a top-level container that manages collection references.
    Collections are separate aggregates managed independently.

    Attributes:
        identity: Unique identifier (WorkspaceID) for the workspace.
        collection_ids: List of collection identities in this workspace.
        created_at: Timestamp when the workspace was created.
        updated_at: Timestamp when the workspace was last modified.

    Invariants:
        - Identity must be unique globally.
        - Collection IDs list cannot contain duplicates.
        - created_at must be <= updated_at.
        - updated_at must reflect the last time collections changed.
    """

    name: str
    identity: WorkspaceID
    collection_ids: list[CollectionID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def create(cls, name: str) -> "Workspace":
        """Factory method to create a workspace from a name."""
        return cls(name=name, identity=WorkspaceID.from_name(name))

    def add_collection(self, collection_id: CollectionID) -> None:
        if self.find_collection_by_identity(collection_id):
            raise DomainError(
                f"Collection with identity {collection_id} already exists"
            )

        self.collection_ids.append(collection_id)
        self.updated_at = datetime.now()

    def remove_collection(self, collection_id: CollectionID) -> None:
        if not self.find_collection_by_identity(collection_id):
            raise DomainError(f"Collection with identity {collection_id} not found")

        self.collection_ids.remove(collection_id)
        self.updated_at = datetime.now()

    def find_collection_by_identity(
        self, collection_id: CollectionID
    ) -> Optional[CollectionID]:
        """Find a collection identity by its ID."""
        for cid in self.collection_ids:
            if cid == collection_id:
                return cid
        return None

    def collection_count(self) -> int:
        """Get the total number of collections in the workspace."""
        return len(self.collection_ids)
