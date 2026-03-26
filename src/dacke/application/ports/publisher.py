"""Port for publishing domain events."""

from abc import ABC, abstractmethod
from typing import Any


class EventPublisher(ABC):
    """Port for publishing domain events to async processors."""

    @abstractmethod
    async def publish(self, event: Any) -> None:
        """Publish a domain event."""
        pass
