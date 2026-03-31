import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID
from dacke.dto.collection import (
    CollectionDTO,
    CreateCollectionBodyDTO,
    CreateCollectionDTO,
    UpdateCollectionDTO,
)
from dacke.infrastructure.dependencies import App, get_app

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/collections",
    tags=["Collections"],
)


def application() -> App:
    app: App = get_app()
    return app


async def _workspace_exists_or_404(app: App, workspace_id: str) -> None:
    identity = WorkspaceID.from_hex(workspace_id)
    workspace = await app.workspace_repository.get_by_id(identity)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")


@router.post("", response_model=CollectionDTO)
async def create_collection(
    workspace_id: str = Path(...),
    body: CreateCollectionBodyDTO = Body(...),
    app: App = Depends(application),
) -> CollectionDTO:
    request = CreateCollectionDTO(workspace_id=workspace_id, name=body.name)
    logger.info(f"Received request to create collection: {request}")
    try:
        await _workspace_exists_or_404(app, workspace_id)
        collection = await app.create_collection_use_case.execute(request)
        return CollectionDTO.from_domain(collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=list[CollectionDTO])
async def list_collections(
    workspace_id: str = Path(...),
    app: App = Depends(application),
) -> list[CollectionDTO]:
    try:
        await _workspace_exists_or_404(app, workspace_id)
        id = WorkspaceID.from_hex(workspace_id)
        items = await app.collection_repository.list_collections(id)
        return [CollectionDTO.from_domain(item) for item in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{collection_id}/files", response_model=list[str])
async def list_artifacts_in_collection(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> list[str]:
    try:
        await _workspace_exists_or_404(app, workspace_id)
        identity = CollectionID.from_hex(collection_id)
        results = [
            str(artifact_id)
            for artifact_id in await app.list_artifacts_in_collection_use_case.execute(
                identity
            )
            or []
        ]
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{collection_id}", response_model=CollectionDTO)
async def get_collection(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> CollectionDTO:
    try:
        await _workspace_exists_or_404(app, workspace_id)
        identity = CollectionID.from_hex(collection_id)
        collection = await app.collection_repository.get_collection_by_id(identity)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return CollectionDTO.from_domain(collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{collection_id}", response_model=CollectionDTO)
async def update_collection(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    request: UpdateCollectionDTO = Body(...),
    app: App = Depends(application),
) -> CollectionDTO:
    try:
        await _workspace_exists_or_404(app, workspace_id)
        identity = CollectionID.from_hex(collection_id)
        collection = await app.collection_repository.get_collection_by_id(identity)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")

        collection.name = request.name
        await app.collection_repository.update_collection(collection)
        return CollectionDTO.from_domain(collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> None:
    try:
        await _workspace_exists_or_404(app, workspace_id)
        identity = CollectionID.from_hex(collection_id)
        collection = await app.collection_repository.get_collection_by_id(identity)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")

        await app.collection_repository.delete_collection(identity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
