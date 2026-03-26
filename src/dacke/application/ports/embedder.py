from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Optional
import logging


logger = logging.getLogger(__name__)


DomainT = TypeVar("DomainT", bound=object)
OrmT = TypeVar("OrmT", bound=object)


class AclLayer(ABC, Generic[DomainT, OrmT]):
    @abstractmethod
    def to_domain(self, orm: OrmT, *args, **kwargs) -> DomainT:
        pass

    @abstractmethod
    def from_domain(self, domain: DomainT, *args, **kwargs) -> OrmT:
        pass


ClientT = TypeVar("ClientT", bound=Any)
DomainAclT = TypeVar("DomainAclT", bound=AclLayer)


class Repository(ABC, Generic[ClientT, DomainAclT]):
    def __init__(self, translation: DomainAclT, *args, **kwargs):
        self._translator = translation
        self._client: Optional[ClientT] = None

        self.startup()
        if not self.health():
            raise Exception("Repository failed to start")

    @property
    def translator(self) -> DomainAclT:
        return self._translator

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
    async def _connect(self) -> None:
        raise NotImplementedError

    # callback methods
    async def _on_startup(self) -> None:
        """Override in subclasses for custom startup behavior."""
        logger.info("Repository started")

    async def _on_health(self) -> bool:
        """Override in subclasses for custom health check."""
        logger.info("Repository health check")

    async def _on_shutdown(self) -> None:
        """Override in subclasses for custom shutdown behavior."""
        logger.info("Repository shutdown")
