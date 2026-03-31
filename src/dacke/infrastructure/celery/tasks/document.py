"""Celery tasks for document processing pipeline."""

import asyncio
import logging

from celery import Task

from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.infrastructure.celery.app import celery_app
from dacke.infrastructure.dependencies import get_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="artifacts.upload.1")
def convert_artifact_to_document(
    self: Task,
    artifact_id: str,
    collection_id: str,
) -> None:
    try:
        application = get_app()
        embeddings = asyncio.run(
            application.convert_artifact_handler.handle(
                artifact_id=ArtifactID.from_hex(artifact_id),
                collection_id=CollectionID.from_hex(collection_id),
            )
        )

        logger.info(
            f"Document conversion completed for artifact {artifact_id}: "
            f"{len(embeddings) if embeddings else 0} embedding(s) produced"
        )

    except Exception as exc:
        logger.error(f"Document conversion failed for artifact {artifact_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries)) from exc


@celery_app.task(bind=True, max_retries=3, name="artifacts.delete.1")
def cleanup_artifact_data(
    self: Task,
    artifact_id: str,
    collection_id: str,
) -> None:
    try:
        application = get_app()
        asyncio.run(
            application.cleanup_artifact_handler.handle(
                artifact_id=ArtifactID.from_hex(artifact_id),
                collection_id=CollectionID.from_hex(collection_id),
            )
        )
        logger.info(f"Cleanup completed for artifact {artifact_id}")
    except Exception as exc:
        logger.error(f"Cleanup failed for artifact {artifact_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries)) from exc
