"""Artifact endpoints."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile

from dacke.application.exceptions import UseCaseError
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID
from dacke.dto.artifact import ArtifactDeleteDTO, ArtifactDTO, ArtifactUploadDTO
from dacke.infrastructure.dependencies import App, get_app

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/collections/{collection_id}/artifacts",
    tags=["Artifacts"],
)


async def _validate_workspace_and_collection(
    app: App, workspace_id: str, collection_id: str
) -> None:
    """Validate workspace and collection exist."""
    ws_identity = WorkspaceID.from_hex(workspace_id)
    workspace = await app.workspace_repository.get_by_id(ws_identity)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    coll_identity = CollectionID.from_hex(collection_id)
    collection = await app.collection_repository.get_collection_by_id(coll_identity)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")


@router.post("", response_model=ArtifactDTO)
async def upload_artifact(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    file: UploadFile = File(...),
    app: App = Depends(get_app),
) -> ArtifactDTO:
    """Upload a file to a collection."""
    try:
        assert file is not None, "File content is empty"
        assert file.filename, "Filename is required"

        await _validate_workspace_and_collection(app, workspace_id, collection_id)

        content = await file.read()
        dto = ArtifactUploadDTO(
            collection_id=collection_id,
            file=content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )

        result = await app.upload_file_use_case.execute(dto)

        logger.info(f"File {file.filename} uploaded successfully to collection {collection_id}")
        return result

    except UseCaseError as e:
        logger.error(f"Use case error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{artifact_id}")
async def delete_artifact(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    artifact_id: str = Path(...),
    app: App = Depends(get_app),
) -> None:
    """Delete an artifact."""
    try:
        await _validate_workspace_and_collection(app, workspace_id, collection_id)

        identity = ArtifactID.from_hex(artifact_id)
        file = await app.artifact_metadata_repository.get_artifact_by_id(identity)
        if file is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        dto = ArtifactDeleteDTO(artifact_id=str(identity), collection_id=str(file.collection_id))
        await app.delete_file_use_case.execute(dto)

        logger.info(f"Artifact {artifact_id} deleted successfully")

    except UseCaseError as e:
        logger.error(f"Use case error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting artifact: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
