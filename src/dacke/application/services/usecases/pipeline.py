from dacke.application.exceptions import UseCaseError
from dacke.application.ports.usecase import UseCase
from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.values.pipeline import PipelineID, PipelineLifecycle
from dacke.dto.pipeline import UpdatePipelineDTO
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineRepository,
)


class DemotePipelineUseCase(UseCase[UpdatePipelineDTO, bool]):
    def __init__(
        self,
        pipeline_repository: PipelineRepository,
    ):
        self.pipeline_repository = pipeline_repository

    async def execute(self, dto: UpdatePipelineDTO) -> bool:
        try:
            identity = PipelineID.from_hex(dto.id)
            await self.pipeline_repository.change_lifecycle(
                pipeline_id=identity, stage=PipelineLifecycle(dto.lifecycle)
            )
            return True
        except Exception as e:
            raise UseCaseError("Failed to demote pipeline") from e


class PromotePipelineUseCase(UseCase[UpdatePipelineDTO, bool]):
    def __init__(
        self,
        pipeline_repository: PipelineRepository,
    ):
        self.pipeline_repository = pipeline_repository

    async def execute(self, dto: UpdatePipelineDTO) -> bool:
        try:
            identity = PipelineID.from_hex(dto.id)
            await self.pipeline_repository.change_lifecycle(
                pipeline_id=identity, stage=PipelineLifecycle(dto.lifecycle)
            )
            return True
        except Exception as e:
            raise UseCaseError("Failed to promote pipeline") from e


class GetPipelineInLifecycleUseCase(UseCase[UpdatePipelineDTO, Pipeline]):
    def __init__(
        self,
        pipeline_repository: PipelineRepository,
    ):
        self.pipeline_repository = pipeline_repository

    async def execute(self, dto: UpdatePipelineDTO) -> Pipeline:
        try:
            identity = PipelineID.from_hex(dto.id)
            pipeline = await self.pipeline_repository.get_pipeline_by_id(identity)
            if pipeline is None:
                raise UseCaseError("Pipeline not found")
            return pipeline

        except Exception as e:
            raise UseCaseError("Failed to get pipeline") from e
