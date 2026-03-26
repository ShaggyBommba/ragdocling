from dacke.application.exceptions import UseCaseError
from dacke.application.ports.usecase import UseCase
from dacke.domain.events.artifact import ArtifactDeletedEvent, ArtifactUploadedEvent
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.dto.artifact import ArtifactDeleteDTO, ArtifactDTO, ArtifactUploadDTO
from dacke.infrastructure.bus import DomainEventBus
from dacke.infrastructure.repositories.providers.minio.repo_artifact import (
    ArtifactBlobRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_artifact import (
    ArtifactMetadataRepository,
)


class UploadFileUseCase(UseCase[ArtifactUploadDTO, ArtifactDTO]):
    """
    Synchronous use case: saves artifact to DB and blob storage.
    Publishes event for async processing (document conversion → chunking).
    """

    def __init__(
        self,
        artifact_repository: ArtifactMetadataRepository,
        blob_repository: ArtifactBlobRepository,
        event_bus: DomainEventBus,
    ):
        self.artifact_repository = artifact_repository
        self.blob_repository = blob_repository
        self.event_bus = event_bus

    async def execute(self, dto: ArtifactUploadDTO) -> ArtifactDTO:
        artifact = dto.to_domain()
        collection_id = CollectionID.from_hex(dto.collection_id)

        try:
            await self.blob_repository.save_blob(artifact.as_blob)
            await self.artifact_repository.save_artifact(artifact, collection_id)
            event = ArtifactUploadedEvent(
                artifact_id=artifact.identity,
                collection_id=collection_id,
            )
            await self.event_bus.publish(event)
            return ArtifactDTO.from_domain(artifact)

        except Exception as e:
            await self.blob_repository.delete_blob(artifact.address)
            await self.artifact_repository.delete_artifact(artifact.identity)
            raise UseCaseError(f"Failed to upload file: {str(e)}") from e


class DeleteFileUseCase(UseCase[ArtifactDeleteDTO, None]):
    """
    Synchronous use case: deletes artifact from DB and blob storage.
    Publishes event for async cleanup (document/chunks deletion).
    """

    def __init__(
        self,
        artifact_repository: ArtifactMetadataRepository,
        blob_repository: ArtifactBlobRepository,
        event_bus: DomainEventBus,
    ):
        self.artifact_repository = artifact_repository
        self.blob_repository = blob_repository
        self.event_bus = event_bus

    async def execute(self, dto: ArtifactDeleteDTO) -> None:
        try:
            artifact_id = ArtifactID.from_hex(dto.artifact_id)

            artifact = await self.artifact_repository.get_artifact_by_id(artifact_id)
            if not artifact:
                raise UseCaseError("Artifact not found")
            await self.blob_repository.delete_blob(artifact.address)
            await self.artifact_repository.delete_artifact(artifact_id)
            event = ArtifactDeletedEvent(
                artifact_id=artifact_id,
                collection_id=CollectionID.from_hex(dto.collection_id),
            )
            await self.event_bus.publish(event)
        except UseCaseError:
            raise
        except Exception as e:
            raise UseCaseError(f"Failed to delete file: {str(e)}") from e
