"""Event handlers for artifact events."""

import logging
from typing import Any

from pydantic import HttpUrl

from dacke.application.ports.extractor import Extractor
from dacke.application.ports.handler import Handler
from dacke.domain.aggregates.document import Document
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.infrastructure.pipeline.registry import TransformerRegistry
from dacke.infrastructure.repositories.providers.minio.repo_artifact import (
    ArtifactBlobRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_artifact import (
    ArtifactMetadataRepository,
)
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineRepository,
)

logger = logging.getLogger(__name__)


class ConvertArtifactToDocumentHandler(Handler[Any]):
    """
    Convert an artifact to a document.
    """

    def __init__(
        self,
        pipeline_extractor: Extractor[Any, Document],
        transformer_registry: TransformerRegistry,
        pipeline_repo: PipelineRepository,
        artifact_repo: ArtifactMetadataRepository,
        blob_repo: ArtifactBlobRepository,
    ):
        self.pipeline_extractor = pipeline_extractor
        self.transformer_registry = transformer_registry
        self.pipeline_repo = pipeline_repo
        self.artifact_repo = artifact_repo
        self.blob_repo = blob_repo

    async def handle(
        self,
        artifact_id: ArtifactID,
        collection_id: CollectionID,
    ) -> Any:
        """
        Handle artifact uploaded event by triggering document conversion.

        Args:
            artifact_id: ID of the artifact to convert
            collection_id: ID of the collection the artifact belongs to
        """
        logger.info(
            f"Converting artifact {artifact_id} from collection {collection_id} to document"
        )

        artifact = await self.artifact_repo.get_artifact_by_id(artifact_id)
        if artifact is None:
            logger.warning(f"Artifact {artifact_id} not found for conversion")
            return None

        uri = await self.blob_repo.get_presigned_url(artifact.address)
        if uri is None:
            logger.warning(f"Presigned URL for artifact {artifact_id} not found for conversion")
            return None

        pipelines = await self.pipeline_repo.get_pipelines_by_collection(collection_id)
        logger.info(
            f"Artifact {artifact_id} ready for conversion with {len(pipelines)} configured pipelines"
        )

        document = await self.pipeline_extractor.extract(pipelines, HttpUrl(uri))

        for name, cls in self.transformer_registry.all().items():
            logger.info(f"Applying transformer '{name}' to document from artifact {artifact_id}")
            transformer_instance = cls()
            document = await transformer_instance.transform(document)

        logger.info(f"Document conversion completed for artifact {artifact_id}")
        return document


class CleanupArtifactDataHandler(Handler[Any]):
    """
    Clean up artifact data.
    """

    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        artifact_repo: ArtifactMetadataRepository,
        blob_repo: ArtifactBlobRepository,
    ):
        self.pipeline_repo = pipeline_repo
        self.artifact_repo = artifact_repo
        self.blob_repo = blob_repo

    async def handle(
        self,
        artifact_id: ArtifactID,
        collection_id: CollectionID,
    ) -> Any:
        """
        Handle artifact deleted event by triggering cleanup.

        Args:
            artifact_id: ID of the artifact to cleanup
            collection_id: ID of the collection the artifact belongs to
        """
        logger.info(
            f"Cleanup task queued for artifact {artifact_id} from collection {collection_id}"
        )

        artifact = await self.artifact_repo.get_artifact_by_id(artifact_id)
        if artifact is None:
            logger.info(f"Artifact {artifact_id} already removed before cleanup")
            return None

        await self.blob_repo.delete_blob(artifact.address)
        await self.artifact_repo.delete_artifact(artifact_id)
        logger.info(f"Artifact {artifact_id} cleanup completed")
        return {
            "artifact_id": str(artifact_id),
            "collection_id": str(collection_id),
            "status": "cleaned",
        }
