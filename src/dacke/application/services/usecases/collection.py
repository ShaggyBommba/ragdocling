from dacke.application.exceptions import UseCaseError
from dacke.application.ports.usecase import UseCase
from dacke.domain.aggregates.collection import Collection
from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.extraction import ExtractionSettings
from dacke.domain.values.pipeline import PipelineLifecycle
from dacke.domain.values.transformer import TransformerSettings
from dacke.dto.collection import CreateCollectionDTO
from dacke.infrastructure.repositories.providers.postgres.repo_collection import (
    CollectionRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineRepository,
)


class CreateCollectionUseCase(UseCase[CreateCollectionDTO, Collection]):
    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        collection_repository: CollectionRepository,
    ):
        self.pipeline_repository = pipeline_repository
        self.collection_repository = collection_repository

    async def execute(self, dto: CreateCollectionDTO) -> Collection:
        collection = dto.to_domain()
        pipeline = Pipeline.create(
            name=collection.name,
            extraction_settings=ExtractionSettings(),
            transformations_settings=[TransformerSettings(name="default")],
            collection_id=collection.identity,
            lifecycle=PipelineLifecycle.PRODUCTION,
        )
        try:
            await self.collection_repository.save_collection(collection)
            await self.pipeline_repository.save_pipeline(pipeline)
            return collection
        except Exception as e:
            await self.collection_repository.delete_collection(collection.identity)
            await self.pipeline_repository.delete_pipeline(pipeline.identity)
            raise UseCaseError("Failed to create collection") from e


class ListArtifactsInCollectionUseCase(UseCase[CollectionID, list[ArtifactID]]):
    """
    Synchronous use case: lists all artifacts in a collection.
    """

    def __init__(
        self,
        collection_repository: CollectionRepository,
    ):
        self.collection_repository = collection_repository

    async def execute(self, dto: CollectionID) -> list[ArtifactID]:
        try:
            collection = await self.collection_repository.get_collection_by_id(dto)
            if not collection:
                raise UseCaseError("Collection not found")

            return collection.artifact_ids

        except UseCaseError:
            raise
        except Exception as e:
            raise UseCaseError(f"Failed to list artifacts: {str(e)}") from e
