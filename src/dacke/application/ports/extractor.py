from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import HttpUrl

# Define Type Variables for Document and Response
ConfigType = TypeVar("ConfigType")
ResponseType = TypeVar("ResponseType")


class Extractor(ABC, Generic[ConfigType, ResponseType]):
    """
    Standard interface for all Document Extractors.

    Enforces a strict input/output contract using Generics.
    """

    @abstractmethod
    async def extract(self, config: ConfigType, url: HttpUrl) -> ResponseType:
        """Execute the extraction logic for this specific extractor."""
        pass
