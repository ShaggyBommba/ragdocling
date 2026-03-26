from pydantic import BaseModel

from dacke.domain.aggregates.workspace import Workspace


class CreateWorkspaceDTO(BaseModel):
    name: str

    def to_domain(self) -> Workspace:
        return Workspace.create(name=self.name)


class UpdateWorkspaceDTO(BaseModel):
    name: str


class WorkspaceDTO(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, workspace: Workspace) -> "WorkspaceDTO":
        return cls(
            id=str(workspace.identity),
            name=workspace.name,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat(),
        )
