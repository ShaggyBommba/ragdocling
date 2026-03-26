from dacke.application.exceptions import UseCaseError
from dacke.application.ports.usecase import UseCase
from dacke.domain.aggregates.collection import Collection
from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.aggregates.workspace import Workspace
from dacke.domain.values.pipeline import PipelineLifecycle
from dacke.dto.workspace import CreateWorkspaceDTO
from dacke.infrastructure.repositories.providers.postgres.repo_collection import (
    CollectionRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_workspace import (
    WorkspaceRepository,
)


class CreateWorkspaceUseCase(UseCase[CreateWorkspaceDTO, Workspace]):
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        collection_repository: CollectionRepository,
        pipeline_repository: PipelineRepository,
    ):
        self.workspace_repository = workspace_repository
        self.collection_repository = collection_repository
        self.pipeline_repository = pipeline_repository

    async def execute(self, dto: CreateWorkspaceDTO) -> Workspace:
        workspace = Workspace.create(dto.name)
        collection = Collection.create("default", workspace.identity)
        pipeline = Pipeline.create(
            "default", collection.identity, lifecycle=PipelineLifecycle.PRODUCTION
        )
        workspace.add_collection(collection.identity)

        try:
            await self.workspace_repository.create(workspace)
            await self.collection_repository.save_collection(collection)
            await self.pipeline_repository.save_pipeline(pipeline)
            return workspace
        except Exception as e:
            await self.workspace_repository.delete(workspace)
            await self.collection_repository.delete_collection(collection.identity)
            await self.pipeline_repository.delete_pipeline(pipeline.identity)
            raise UseCaseError("Failed to create workspace") from e
