"""Event handlers for artifact events."""

import logging
from typing import Any

from pydantic import AnyUrl

from dacke.application.ports.embedder import Embedder
from dacke.application.ports.extractor import Extractor
from dacke.application.ports.handler import Handler
from dacke.domain.aggregates.document import Document
from dacke.domain.entities.embedding import Embedding
from dacke.domain.values.artifact import ArtifactID, StoragePath
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.document import DocumentMetadata
from dacke.domain.values.pipeline import PipelineLifecycle
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
from dacke.infrastructure.repositories.providers.qdrant.repo_embedding import (
    QdrantEmbeddingRepository,
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
        embedder: Embedder,
        embedding_repo: QdrantEmbeddingRepository,
    ):
        self.pipeline_extractor = pipeline_extractor
        self.transformer_registry = transformer_registry
        self.pipeline_repo = pipeline_repo
        self.artifact_repo = artifact_repo
        self.blob_repo = blob_repo
        self.embedder = embedder
        self.embedding_repo = embedding_repo

    async def handle(
        self,
        artifact_id: ArtifactID,
        collection_id: CollectionID,
    ) -> list[Embedding]:
        """
        Handle artifact uploaded event by triggering document conversion.

        Args:
            artifact_id: ID of the artifact to convert
            collection_id: ID of the collection the artifact belongs to
        """
        logger.info(
            f"[DEBUG] handle: Start for artifact {artifact_id}, collection {collection_id}"
        )

        logger.info("[DEBUG] handle: Fetching artifact from artifact_repo")
        artifact = await self.artifact_repo.get_artifact_by_id(artifact_id)
        logger.info(f"[DEBUG] handle: artifact fetched: {artifact}")
        if artifact is None:
            logger.warning(f"Artifact {artifact_id} not found for conversion")
            return []

        logger.info("[DEBUG] handle: Fetching presigned URL from blob_repo")
        uri = await self.blob_repo.get_presigned_url(artifact.address)
        logger.info(f"[DEBUG] handle: presigned URL: {uri}")
        if uri is None:
            logger.warning(
                f"Presigned URL for artifact {artifact_id} not found for conversion"
            )
            return []

        logger.info("[DEBUG] handle: Fetching pipelines from pipeline_repo")
        pipelines = await self.pipeline_repo.get_pipelines_by_collection(collection_id)
        logger.info(f"[DEBUG] handle: pipelines fetched: {pipelines}")
        if not pipelines:
            logger.warning(
                f"No pipelines configured for collection {collection_id}, cannot convert artifact {artifact_id}"
            )
            return []

        logger.info("[DEBUG] handle: Selecting production pipeline")
        pipeline = next(
            (p for p in pipelines if p.lifecycle == PipelineLifecycle.PRODUCTION), None
        )
        logger.info(f"[DEBUG] handle: selected pipeline: {pipeline}")
        if pipeline is None:
            logger.warning(
                f"No production pipeline found for collection {collection_id}, pipelines available: {[p.model_dump_json(indent=2) for p in pipelines]}. Cannot convert artifact {artifact_id}"
            )
            return []

        logger.info("[DEBUG] handle: Calling pipeline_extractor.extract")
        document = await self.pipeline_extractor.extract(
            folder=StoragePath(f"collections/{collection_id}/artifacts/{artifact_id}"),
            pipeline_id=pipeline.identity,
            extraction_settings=pipeline.extraction_settings,
            url=AnyUrl(uri),
            metadata=DocumentMetadata(
                title=artifact.metadata.filename,
                origin=artifact.metadata.source,
                source_url=AnyUrl(uri),
            ),
        )
        logger.info("[DEBUG] handle: document extracted successfully")

        for settings in pipeline.transformations_settings:
            cls = self.transformer_registry.get(settings.name)
            if cls is None:
                logger.warning(f"Transformer '{settings.name}' not found in registry, skipping")
                continue
            logger.info(f"[DEBUG] handle: Applying transformer '{settings.name}'")
            transformer_instance = cls(**settings.parameters)
            await transformer_instance.transform(document)

        chunks = document.get_chunks()
        if not chunks:
            logger.warning(
                f"[DEBUG] handle: No chunks found for artifact {artifact_id}, skipping embedding"
            )
            return []

        embeddings = await self.embedder.embed_many(
            chunks, pipeline.extraction_settings.embedding
        )
        logger.info(
            f"[DEBUG] handle: Embedded {len(embeddings)} chunk(s) for artifact {artifact_id}"
        )

        origin = str(artifact.metadata.source)
        await self.embedding_repo.delete_by_origin([origin], pipeline.identity)
        logger.info(
            f"[DEBUG] handle: Removed existing embeddings for artifact {artifact_id} from pipeline {pipeline.identity}"
        )

        await self.embedding_repo.save_many(embeddings, pipeline.identity)
        logger.info(
            f"[DEBUG] handle: Persisted {len(embeddings)} embedding(s) for pipeline {pipeline.identity}"
        )

        return embeddings


class CleanupArtifactDataHandler(Handler[Any]):
    """
    Clean up artifact data.
    """

    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        artifact_repo: ArtifactMetadataRepository,
        blob_repo: ArtifactBlobRepository,
        embedding_repo: QdrantEmbeddingRepository,
    ):
        self.pipeline_repo = pipeline_repo
        self.artifact_repo = artifact_repo
        self.blob_repo = blob_repo
        self.embedding_repo = embedding_repo

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
            return []

        pipelines = await self.pipeline_repo.get_pipelines_by_collection(collection_id)
        origin = str(artifact.metadata.source)
        for pipeline in pipelines:
            await self.embedding_repo.delete_by_origin([origin], pipeline.identity)
            logger.info(
                f"Deleted embeddings for artifact {artifact_id} from pipeline {pipeline.identity}"
            )

        await self.blob_repo.delete_blob(artifact.address)
        await self.artifact_repo.delete_artifact(artifact_id)
        logger.info(f"Artifact {artifact_id} cleanup completed")
        return {
            "artifact_id": str(artifact_id),
            "collection_id": str(collection_id),
            "status": "cleaned",
        }
