import asyncio
import logging
from collections.abc import Callable
from typing import Any

from dacke.application.ports.publisher import EventPublisher
from dacke.domain.events.domain import DomainEvent

logger = logging.getLogger(__name__)


class DomainEventBus(EventPublisher):
    """
    Domain event bus for handling local event handlers.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Callable[[DomainEvent], Any]]] = {}

    def register(
        self, event_type: type[DomainEvent], handler: Callable[[DomainEvent], Any]
    ) -> None:
        """Register a local handler for an event."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Registered local handler for {event_type.__name__}")

    async def publish(self, event: DomainEvent) -> Any:
        """
        The main entry point. Orchestrates local execution.
        """
        event_name = type(event).__name__
        logger.info(f"Processing event: {event_name}")

        try:
            handlers = self._handlers.get(type(event), [])
            if handlers:
                for handler in handlers:
                    # Handle both async and sync handlers
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                logger.debug(f"Executed {len(handlers)} local handlers for {event_name}")
            else:
                logger.debug(f"No local handlers registered for {event_name}")
        except Exception as e:
            logger.error(f"Failed to publish event {event_name}: {e}", exc_info=True)
            raise
