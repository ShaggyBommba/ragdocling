"""Infrastructure dependency providers."""

from __future__ import annotations

import logging
import threading

from dotenv import load_dotenv

from dacke.application.services.handlers import (
    CleanupArtifactDataHandler,
    ConvertArtifactToDocumentHandler,
)
from dacke.application.services.usecases import (
    CreateCollectionUseCase,
    CreateWorkspaceUseCase,
    DeleteFileUseCase,
    DemotePipelineUseCase,
    UploadFileUseCase,
)
from dacke.application.services.usecases.collection import (
    ListArtifactsInCollectionUseCase,
)
from dacke.domain.events.artifact import ArtifactDeletedEvent, ArtifactUploadedEvent
from dacke.infrastructure.bus import DomainEventBus
from dacke.infrastructure.celery.app import celery_app
from dacke.infrastructure.config import AppSettings
from dacke.infrastructure.pipeline.extractor import DoclingExtractor
from dacke.infrastructure.pipeline.registry import TransformerRegistry
from dacke.infrastructure.repositories.providers.minio.repo_artifact import (
    ArtifactBlobRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_artifact import (
    ArtifactMetadataRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_collection import (
    CollectionRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_workspace import (
    WorkspaceRepository,
)

load_dotenv()

logger = logging.getLogger(__name__)


class App:
    def __init__(self) -> None:
        logger.info("App __init__ starting")
        self.settings: AppSettings = AppSettings()
        self._celery_worker_thread: threading.Thread | None = None

        logger.info("Initializing ArtifactBlobRepository")
        self.artifact_blob_repository: ArtifactBlobRepository = ArtifactBlobRepository(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
        )

        logger.info("Initializing ArtifactMetadataRepository")
        self.artifact_metadata_repository = ArtifactMetadataRepository(
            connection_string=self.settings.database_url,
        )

        logger.info("Initializing WorkspaceRepository")
        self.workspace_repository = WorkspaceRepository(
            connection_string=self.settings.database_url,
        )

        logger.info("Initializing CollectionRepository")
        self.collection_repository = CollectionRepository(
            connection_string=self.settings.database_url,
        )

        logger.info("Initializing PipelineRepository")
        self.pipeline_repository = PipelineRepository(
            connection_string=self.settings.database_url,
        )

        logger.info("Initializing DomainEventBus and registering events")
        self.bus = DomainEventBus()
        for event in [ArtifactUploadedEvent, ArtifactDeletedEvent]:
            logger.info(f"Registering event {event}")
            self.bus.register(
                event,
                lambda e: celery_app.send_task(
                    f"{e.EVENT_TOPIC}.{e.EVENT_NAME}.{e.EVENT_VERSION}",
                    kwargs=e.payload,
                ),
            )

        logger.info("Initializing ListArtifactsInCollectionUseCase")
        self.list_artifacts_in_collection_use_case = ListArtifactsInCollectionUseCase(
            collection_repository=self.collection_repository,
        )

        logger.info("Initializing UploadFileUseCase")
        self.upload_file_use_case = UploadFileUseCase(
            artifact_repository=self.artifact_metadata_repository,
            blob_repository=self.artifact_blob_repository,
            event_bus=self.bus,
        )

        logger.info("Initializing DeleteFileUseCase")
        self.delete_file_use_case = DeleteFileUseCase(
            artifact_repository=self.artifact_metadata_repository,
            blob_repository=self.artifact_blob_repository,
            event_bus=self.bus,
        )

        logger.info("Initializing CreateWorkspaceUseCase")
        self.create_workspace_use_case = CreateWorkspaceUseCase(
            workspace_repository=self.workspace_repository,
            collection_repository=self.collection_repository,
            pipeline_repository=self.pipeline_repository,
        )

        logger.info("Initializing CreateCollectionUseCase")
        self.create_collection_use_case = CreateCollectionUseCase(
            collection_repository=self.collection_repository,
            pipeline_repository=self.pipeline_repository,
        )

        logger.info("Initializing DemotePipelineUseCase")
        self.demote_pipeline_use_case = DemotePipelineUseCase(
            pipeline_repository=self.pipeline_repository,
        )

        logger.info("Initializing DoclingExtractor and TransformerRegistry")
        pipeline_extractor = DoclingExtractor()
        transformation_registry = TransformerRegistry()
        self.convert_artifact_handler: ConvertArtifactToDocumentHandler = (
            ConvertArtifactToDocumentHandler(
                pipeline_extractor=pipeline_extractor,
                transformer_registry=transformation_registry,
                pipeline_repo=self.pipeline_repository,
                artifact_repo=self.artifact_metadata_repository,
                blob_repo=self.artifact_blob_repository,
            )
        )

        logger.info("Initializing CleanupArtifactDataHandler")
        self.cleanup_artifact_handler: CleanupArtifactDataHandler = (
            CleanupArtifactDataHandler(
                pipeline_repo=self.pipeline_repository,
                artifact_repo=self.artifact_metadata_repository,
                blob_repo=self.artifact_blob_repository,
            )
        )
        logger.info("App __init__ complete")

    async def startup(self) -> None:
        logger.info("App.startup: artifact_blob_repository.startup")
        await self.artifact_blob_repository.startup()
        logger.info("App.startup: artifact_metadata_repository.startup")
        await self.artifact_metadata_repository.startup()
        logger.info("App.startup: workspace_repository.startup")
        await self.workspace_repository.startup()
        logger.info("App.startup: collection_repository.startup")
        await self.collection_repository.startup()
        logger.info("App.startup: pipeline_repository.startup")
        await self.pipeline_repository.startup()

        # Start Celery worker in background thread
        logger.info("App.startup: Starting Celery worker thread")
        self._celery_worker_thread = threading.Thread(
            target=self._run_celery_worker, daemon=True
        )
        self._celery_worker_thread.start()
        logger.info("App.startup: Celery worker thread started")

    def _run_celery_worker(self) -> None:
        """Run Celery worker in a background thread."""
        # Import tasks to register them with Celery (do this here to avoid circular imports)
        import dacke.infrastructure.celery.tasks.document  # noqa: F401

        logger.info("Celery worker thread started")
        worker = celery_app.Worker(
            queues=["artifacts_1"],
            loglevel="info",
            concurrency=2,
        )
        worker.start()

    async def shutdown(self) -> None:
        await self.artifact_blob_repository.shutdown()
        await self.artifact_metadata_repository.shutdown()
        await self.workspace_repository.shutdown()
        await self.collection_repository.shutdown()
        await self.pipeline_repository.shutdown()

        # Stop Celery worker
        if self._celery_worker_thread and self._celery_worker_thread.is_alive():
            logger.info("Stopping Celery worker")
            celery_app.control.shutdown()
            self._celery_worker_thread.join(timeout=5)

    async def health(self) -> bool:
        checks = [
            await self.artifact_blob_repository.health(),
            await self.artifact_metadata_repository.health(),
            await self.workspace_repository.health(),
            await self.collection_repository.health(),
            await self.pipeline_repository.health(),
        ]
        return all(checks)


def get_app() -> App:
    app = App()
    return app
