"""Port for dispatching events to use cases."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Type


class EventDispatcher(ABC):
    """Port for dispatching domain events to registered use cases."""

    @abstractmethod
    def register(
        self,
        event_type: Type[Any],
        use_case: Callable[[Any], Any],
    ) -> None:
        """
        Register a use case handler for an event type.

        Args:
            event_type: The domain event class to handle
            use_case: The use case callable that handles the event
        """
        pass

    @abstractmethod
    async def dispatch(self, event: Any) -> Any:
        """
        Dispatch an event to its registered use case handler.

        Args:
            event: The domain event to dispatch

        Returns:
            The result from the use case handler

        Raises:
            ValueError: If no handler is registered for the event type
        """
        pass

    @abstractmethod
    def has_handler(self, event_type: Type[Any]) -> bool:
        """Check if a handler is registered for an event type."""
        pass
