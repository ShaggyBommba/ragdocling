from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import AnyUrl

from dacke.domain.values.artifact import StoragePath
from dacke.domain.values.document import DocumentMetadata
from dacke.domain.values.pipeline import PipelineID

# Define Type Variables for Document and Response
ConfigType = TypeVar("ConfigType")
ResponseType = TypeVar("ResponseType")


class Extractor(ABC, Generic[ConfigType, ResponseType]):
    """
    Standard interface for all Document Extractors.

    Enforces a strict input/output contract using Generics.
    """

    @abstractmethod
    async def extract(
        self,
        folder: StoragePath,
        pipeline_id: PipelineID,
        extraction_settings: ConfigType,
        url: AnyUrl,
        metadata: DocumentMetadata,
    ) -> ResponseType:
        """Execute the extraction logic for this specific extractor."""
        pass
