import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from dacke.application.exceptions import ApplicationError
from dacke.domain.exceptions import DomainError
from dacke.domain.values.workspace import WorkspaceID
from dacke.dto.workspace import CreateWorkspaceDTO, UpdateWorkspaceDTO, WorkspaceDTO
from dacke.infrastructure.dependencies import App, get_app
from dacke.infrastructure.exceptions import InfrastructureError

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["Workspaces"],
)


def application() -> App:
    app = get_app()
    return app


@router.post("", response_model=WorkspaceDTO)
async def create_workspace(
    request: CreateWorkspaceDTO = Body(...),
    app: App = Depends(application),
) -> WorkspaceDTO:
    try:
        workspace = await app.create_workspace_use_case.execute(request)
        return WorkspaceDTO.from_domain(workspace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ApplicationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except InfrastructureError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=list[WorkspaceDTO])
async def list_workspaces(
    app: App = Depends(application),
) -> list[WorkspaceDTO]:
    try:
        workspaces = await app.workspace_repository.get_all()
        return [WorkspaceDTO.from_domain(workspace) for workspace in workspaces]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{workspace_id}", response_model=WorkspaceDTO)
async def get_workspace(
    workspace_id: str = Path(...),
    app: App = Depends(application),
) -> WorkspaceDTO:
    try:
        identity = WorkspaceID.from_hex(workspace_id)
        workspace = await app.workspace_repository.get_by_id(identity)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return WorkspaceDTO.from_domain(workspace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ApplicationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except InfrastructureError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{workspace_id}", response_model=WorkspaceDTO)
async def update_workspace(
    workspace_id: str = Path(...),
    request: UpdateWorkspaceDTO = Body(...),
    app: App = Depends(application),
) -> WorkspaceDTO:
    try:
        identity = WorkspaceID.from_hex(workspace_id)
        workspace = await app.workspace_repository.get_by_id(identity)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace = workspace.model_copy(update=request.model_dump())
        await app.workspace_repository.update(workspace)
        return WorkspaceDTO.from_domain(workspace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ApplicationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except InfrastructureError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str = Path(...),
    app: App = Depends(application),
) -> None:
    try:
        identity = WorkspaceID.from_hex(workspace_id)
        workspace = await app.workspace_repository.get_by_id(identity)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        await app.workspace_repository.delete(workspace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
