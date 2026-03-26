from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """
    Base class for all domain events in a DDD system.
    """

    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: UUID = field(default_factory=uuid4)

    # Event metadata
    EVENT_TOPIC: ClassVar[str] = "domain_event"
    EVENT_NAME: ClassVar[str] = "domain_event"
    EVENT_VERSION: ClassVar[int] = 1

    # Tracing
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None

    @property
    def payload(self) -> dict[str, Any]:
        return {}
