import logging

from fastapi import APIRouter, Depends, HTTPException, Path

from dacke.domain.aggregates.collection import Collection
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.pipeline import PipelineID, PipelineLifecycle
from dacke.domain.values.workspace import WorkspaceID
from dacke.dto.pipeline import PipelineDTO
from dacke.infrastructure.dependencies import App, get_app

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/collections/{collection_id}/pipelines",
    tags=["Pipelines"],
)


def application() -> App:
    app: App = get_app()
    return app


async def _get_collection_or_404(app: App, workspace_id: str, collection_id: str) -> Collection:
    ws_identity = WorkspaceID.from_hex(workspace_id)
    workspace = await app.workspace_repository.get_by_id(ws_identity)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    identity = CollectionID.from_hex(collection_id)
    collection = await app.collection_repository.get_collection_by_id(identity)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


async def _get_pipeline_by_lifecycle(
    app: App,
    workspace_id: str,
    collection_id: str,
    lifecycle: PipelineLifecycle,
) -> PipelineDTO:
    await _get_collection_or_404(app, workspace_id, collection_id)
    identity = CollectionID.from_hex(collection_id)
    pipelines = await app.pipeline_repository.get_pipelines_by_collection(identity)
    for pipeline in pipelines:
        if pipeline.lifecycle == lifecycle:
            return PipelineDTO.from_domain(pipeline)
    raise HTTPException(status_code=404, detail="Pipeline not found")


@router.get("", response_model=list[PipelineDTO])
async def list_collection_pipelines(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> list[PipelineDTO]:
    try:
        identity = CollectionID.from_hex(collection_id)
        await _get_collection_or_404(app, workspace_id, collection_id)
        pipelines = await app.pipeline_repository.get_pipelines_by_collection(identity)
        return [PipelineDTO.from_domain(pipeline) for pipeline in pipelines]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/production", response_model=PipelineDTO)
async def get_production_pipeline(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> PipelineDTO:
    try:
        return await _get_pipeline_by_lifecycle(
            app, workspace_id, collection_id, PipelineLifecycle.PRODUCTION
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/staging", response_model=PipelineDTO)
async def get_staging_pipeline(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> PipelineDTO:
    try:
        return await _get_pipeline_by_lifecycle(
            app, workspace_id, collection_id, PipelineLifecycle.STAGING
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/archived", response_model=PipelineDTO)
async def get_archived_pipeline(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    app: App = Depends(application),
) -> PipelineDTO:
    try:
        return await _get_pipeline_by_lifecycle(
            app, workspace_id, collection_id, PipelineLifecycle.ARCHIVED
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{pipeline_id}", response_model=PipelineDTO)
async def get_collection_pipeline(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    pipeline_id: str = Path(...),
    app: App = Depends(application),
) -> PipelineDTO:
    try:
        await _get_collection_or_404(app, workspace_id, collection_id)
        identity = PipelineID.from_hex(pipeline_id)
        pipeline = await app.pipeline_repository.get_pipeline_by_id(identity)
        if pipeline is None or str(pipeline.collection_id) != collection_id:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return PipelineDTO.from_domain(pipeline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{pipeline_id}/promote", response_model=PipelineDTO)
async def promote_pipeline(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    pipeline_id: str = Path(...),
    app: App = Depends(application),
) -> PipelineDTO:
    try:
        await _get_collection_or_404(app, workspace_id, collection_id)
        identity = PipelineID.from_hex(pipeline_id)
        pipeline = await app.pipeline_repository.get_pipeline_by_id(identity)
        if pipeline is None or str(pipeline.collection_id) != collection_id:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        await app.pipeline_repository.change_lifecycle(identity, PipelineLifecycle.PRODUCTION)
        updated = await app.pipeline_repository.get_pipeline_by_id(identity)
        if updated is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return PipelineDTO.from_domain(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{pipeline_id}/demote", response_model=PipelineDTO)
async def demote_pipeline(
    workspace_id: str = Path(...),
    collection_id: str = Path(...),
    pipeline_id: str = Path(...),
    app: App = Depends(application),
) -> PipelineDTO:
    try:
        await _get_collection_or_404(app, workspace_id, collection_id)
        identity = PipelineID.from_hex(pipeline_id)
        pipeline = await app.pipeline_repository.get_pipeline_by_id(identity)
        if pipeline is None or str(pipeline.collection_id) != collection_id:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        await app.pipeline_repository.change_lifecycle(identity, PipelineLifecycle.STAGING)
        updated = await app.pipeline_repository.get_pipeline_by_id(identity)
        if updated is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return PipelineDTO.from_domain(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
