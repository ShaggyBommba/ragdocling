from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# Define Type Variables for Document and Response
ResponseType = TypeVar("ResponseType")


class Handler(ABC, Generic[ResponseType]):
    """
    Standard interface for all Document Extractors.

    Enforces a strict input/output contract using Generics.
    """

    @abstractmethod
    async def handle(self, *args, **kwargs) -> ResponseType:
        """Execute the handler logic for this specific handler."""
        pass
