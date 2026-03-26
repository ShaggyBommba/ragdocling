from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# Define Type Variables for Request and Response
RequestType = TypeVar("RequestType")
ResponseType = TypeVar("ResponseType")


class UseCase(ABC, Generic[RequestType, ResponseType]):
    """
    Standard interface for all Application Use Cases.

    Enforces a strict input/output contract using Generics.
    """

    @abstractmethod
    async def execute(self, dto: RequestType) -> ResponseType:
        """Execute the business logic for this specific use case."""
        pass
