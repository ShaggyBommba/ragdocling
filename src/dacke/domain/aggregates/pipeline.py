import hashlib
import json
from datetime import datetime
from logging import getLogger

from pydantic import BaseModel, Field

from dacke.domain.values.collection import CollectionID
from dacke.domain.values.extraction import ExtractionSettings
from dacke.domain.values.pipeline import PipelineID, PipelineLifecycle
from dacke.domain.values.transformer import TransformerSettings

logger = getLogger(__name__)


class Pipeline(BaseModel):
    """
    Pipeline aggregate root.

    Attributes:
        identity: Unique pipeline identifier
        collection_id: Collection this pipeline belongs to
        extraction_settings: Extraction configuration
        transformations_settings: List of transformation configurations
        lifecycle: Current pipeline lifecycle state
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Invariants:
        - Pipeline must have at least one transformation
        - Pipeline must belong to a valid collection
    """

    identity: PipelineID
    name: str = "default"
    collection_id: CollectionID
    lifecycle: PipelineLifecycle = PipelineLifecycle.STAGING
    extraction_settings: ExtractionSettings
    transformations_settings: list[TransformerSettings]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        name: str,
        collection_id: CollectionID,
        extraction_settings: ExtractionSettings = ExtractionSettings(),
        transformations_settings: list[TransformerSettings] = [],
        lifecycle: PipelineLifecycle = PipelineLifecycle.STAGING,
    ) -> "Pipeline":
        fingerprint = {
            "extraction": extraction_settings.model_dump_json(),
            "transformations": [
                transformer.model_dump_json() for transformer in transformations_settings
            ],
            "collection_id": str(collection_id.value),
        }
        serialized = json.dumps(fingerprint, sort_keys=True).encode("utf-8")
        hash_value = hashlib.sha256(serialized).hexdigest()

        return cls(
            identity=PipelineID.from_hash(hash_value, collection_id.value),
            name=name,
            collection_id=collection_id,
            lifecycle=lifecycle,
            extraction_settings=extraction_settings,
            transformations_settings=transformations_settings,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def deploy(self) -> None:
        if self.lifecycle == PipelineLifecycle.ARCHIVED:
            logger.warning("Cannot activate an archived pipeline")
            return
        self.lifecycle = PipelineLifecycle.PRODUCTION
        self.updated_at = datetime.now()

    def stage(self) -> None:
        if self.lifecycle == PipelineLifecycle.ARCHIVED:
            logger.warning("Cannot deactivate an archived pipeline")
            return
        self.lifecycle = PipelineLifecycle.STAGING
        self.updated_at = datetime.now()

    def archive(self) -> None:
        if self.lifecycle == PipelineLifecycle.ARCHIVED:
            logger.warning("Cannot archive an archived pipeline")
            return
        self.lifecycle = PipelineLifecycle.ARCHIVED
        self.updated_at = datetime.now()
