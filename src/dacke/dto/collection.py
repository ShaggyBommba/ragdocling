from pydantic import BaseModel

from dacke.domain.aggregates.collection import Collection
from dacke.domain.values.workspace import WorkspaceID


class CreateCollectionDTO(BaseModel):
    workspace_id: str
    name: str

    def to_domain(self) -> Collection:
        return Collection.create(
            name=self.name,
            workspace_id=WorkspaceID.from_hex(self.workspace_id),
        )


class UpdateCollectionDTO(BaseModel):
    name: str


class CollectionDTO(BaseModel):
    id: str
    workspace_id: str
    name: str
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, collection: Collection) -> "CollectionDTO":
        return cls(
            id=str(collection.identity),
            workspace_id=collection.workspace_id.value.hex,
            name=collection.name,
            created_at=collection.created_at.isoformat(),
            updated_at=collection.updated_at.isoformat(),
        )
