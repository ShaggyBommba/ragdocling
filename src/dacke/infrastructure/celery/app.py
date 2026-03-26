"""Celery application configuration."""

from celery import Celery
from dacke.domain.events.artifact import ArtifactDeletedEvent, ArtifactUploadedEvent
from dacke.infrastructure.config import AppSettings

settings = AppSettings()

celery_app = Celery(
    "dacke",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

celery_app.conf.task_routes = {
    f"{ArtifactUploadedEvent.EVENT_TOPIC}.{ArtifactUploadedEvent.EVENT_NAME}.{ArtifactUploadedEvent.EVENT_VERSION}": {
        "queue": f"{ArtifactUploadedEvent.EVENT_TOPIC}_{ArtifactUploadedEvent.EVENT_VERSION}"
    },
    f"{ArtifactDeletedEvent.EVENT_TOPIC}.{ArtifactDeletedEvent.EVENT_NAME}.{ArtifactDeletedEvent.EVENT_VERSION}": {
        "queue": f"{ArtifactDeletedEvent.EVENT_TOPIC}_{ArtifactDeletedEvent.EVENT_VERSION}"
    },
    f"{ArtifactUploadedEvent.EVENT_TOPIC}.{ArtifactUploadedEvent.EVENT_NAME}.{ArtifactUploadedEvent.EVENT_VERSION}": {
        "queue": f"{ArtifactUploadedEvent.EVENT_TOPIC}_{ArtifactUploadedEvent.EVENT_VERSION}"
    },
}

# Autodiscover tasks from the tasks module to avoid circular imports
celery_app.autodiscover_tasks(["dacke.infrastructure.celery.tasks"])
