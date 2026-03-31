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
    def _default_transformations(cls) -> list[TransformerSettings]:
        return [
            TransformerSettings(
                name="PatternMatchTransformer",
                parameters={
                    "patterns": {
                        "doi": r"10\.\d{4,}/\S+",
                        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
                        "arxiv": r"arXiv:\d{4}\.\d{4,5}",
                    }
                },
            ),
            TransformerSettings(name="UrlExtractTransformer"),
            TransformerSettings(
                name="QueryGenerationTransformer",
                parameters={
                    "url": "http://localhost:1234/v1/chat/completions",
                    "params": {
                        "model": "qwen3.5-9b-mlx",
                        "max_completion_tokens": 300,
                        "enable_thinking": False,
                    },
                    "timeout": 120.0,
                    "concurrency": 2,
                },
            ),
        ]

    @classmethod
    def create(
        cls,
        name: str,
        collection_id: CollectionID,
        extraction_settings: ExtractionSettings = ExtractionSettings(),
        transformations_settings: list[TransformerSettings] | None = None,  # None = use defaults
        lifecycle: PipelineLifecycle = PipelineLifecycle.STAGING,
    ) -> "Pipeline":
        resolved = transformations_settings if transformations_settings is not None else cls._default_transformations()

        fingerprint = {
            "extraction": extraction_settings.model_dump_json(),
            "transformations": [t.model_dump_json() for t in resolved],
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
            transformations_settings=resolved,
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
