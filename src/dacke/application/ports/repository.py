import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)


DomainT = TypeVar("DomainT", bound=object)
OrmT = TypeVar("OrmT", bound=object)


class AclLayer(ABC, Generic[DomainT, OrmT]):
    @staticmethod
    def to_domain(orm: OrmT, *args: Any, **kwargs: Any) -> DomainT:
        raise NotImplementedError

    @staticmethod
    def from_domain(domain: DomainT, *args: Any, **kwargs: Any) -> OrmT:
        raise NotImplementedError


class Repository(ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._client: Any | None = None

    # Lifecycle methods
    async def startup(self) -> None:
        await self._connect()
        await self._on_startup()

    async def health(self) -> bool:
        return await self._on_health()

    async def shutdown(self) -> None:
        await self._disconnect()
        await self._on_shutdown()

    # To be implemented by subclasses
    @abstractmethod
    async def _disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _connect(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    # callback methods
    async def _on_startup(self) -> None:
        """Override in subclasses for custom startup behavior."""
        logger.info("Repository started")

    async def _on_health(self) -> bool:
        """Override in subclasses for custom health check."""
        logger.info("Repository health check")
        return True

    async def _on_shutdown(self) -> None:
        """Override in subclasses for custom shutdown behavior."""
        logger.info("Repository shutdown")
