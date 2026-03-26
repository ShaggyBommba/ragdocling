from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# Define Type Variables for Document and Response
DocumentType = TypeVar("DocumentType")
ResponseType = TypeVar("ResponseType")


class Transformer(ABC, Generic[DocumentType, ResponseType]):
    """
    Standard interface for all Document Transformers.

    Enforces a strict input/output contract using Generics.
    """

    @abstractmethod
    async def transform(self, document: DocumentType) -> ResponseType:
        """Execute the transformation logic for this specific transformer."""
        pass
