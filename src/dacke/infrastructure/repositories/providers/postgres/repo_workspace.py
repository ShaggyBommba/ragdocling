"""Workspace repository implementation."""

from typing import Any, List, Optional

from dacke.application.ports.repository import AclLayer, Repository
from dacke.domain.aggregates.workspace import Workspace
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID
from dacke.infrastructure.exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
)
from dacke.infrastructure.repositories.providers.postgres.models import WorkspacesTable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool


class WorkspaceAcl(AclLayer[Workspace, WorkspacesTable]):
    """Translation layer between Workspace domain and ORM."""

    @staticmethod
    def to_domain(orm: WorkspacesTable, *args: Any, **kwargs: Any) -> Workspace:
        """Convert ORM model to domain aggregate."""
        return Workspace(
            name=orm.name,
            identity=WorkspaceID.from_hex(orm.id),
            collection_ids=[CollectionID.from_hex(cid.id) for cid in orm.collections],
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def from_domain(domain: Workspace, *args: Any, **kwargs: Any) -> WorkspacesTable:
        """Convert domain aggregate to ORM model."""
        return WorkspacesTable(
            id=str(domain.identity),
            name=domain.name,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )


class WorkspaceRepository(Repository):
    """Repository for persisting and retrieving Workspace aggregates."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._client: Optional[async_sessionmaker[AsyncSession]] = None
        self._engine: Optional[AsyncEngine] = None

    async def create(self, workspace: Workspace) -> None:
        if self._client is None:
            await self._connect()

        assert self._client is not None, "Client should be initialized after connect"
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                orm = WorkspaceAcl.from_domain(workspace)
                session.add(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to create workspace: {e}")

    async def update(self, workspace: Workspace) -> None:
        if self._client is None:
            await self._connect()

        assert self._client is not None, "Client should be initialized after connect"
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                orm = WorkspaceAcl.from_domain(workspace)
                await session.merge(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to update workspace: {e}")

    async def delete(self, workspace: Workspace) -> None:
        if self._client is None:
            await self._connect()

        assert self._client is not None, "Client should be initialized after connect"
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(WorkspacesTable).where(
                        WorkspacesTable.id == str(workspace.identity)
                    )
                )
                orm = result.unique().scalar_one_or_none()
                if orm is not None:
                    await session.delete(orm)
                    await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to delete workspace: {e}")

    async def get_by_id(self, workspace_id: WorkspaceID) -> Optional[Workspace]:
        if self._client is None:
            await self._connect()

        assert self._client is not None, "Client should be initialized after connect"
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(WorkspacesTable)
                    .options(selectinload(WorkspacesTable.collections))
                    .where(WorkspacesTable.id == str(workspace_id))
                )

                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return None

                return WorkspaceAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to get workspace: {e}")

    async def get_by_name(self, workspace_name: str) -> Optional[Workspace]:
        if self._client is None:
            await self._connect()

        assert self._client is not None, "Client should be initialized after connect"
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(WorkspacesTable)
                    .options(selectinload(WorkspacesTable.collections))
                    .where(WorkspacesTable.name == workspace_name)
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return None
                return WorkspaceAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to get workspace: {e}")

    async def get_all(self) -> List[Workspace]:
        if self._client is None:
            await self._connect()

        assert self._client is not None, "Client should be initialized after connect"
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(WorkspacesTable).options(
                        selectinload(WorkspacesTable.collections)
                    )
                )
                orms = result.unique().scalars().all()
                return [WorkspaceAcl.to_domain(orm) for orm in orms]
        except Exception as e:
            raise DatabaseOperationError(f"Failed to get workspaces: {e}")

    async def _connect(self) -> None:
        """Connect to database."""
        # Create the asynchronous engine
        try:
            self._engine = create_async_engine(
                self.connection_string,
                echo=True,
                pool_pre_ping=True,
                poolclass=NullPool,
            )

            # Create a session factory and assign it to self._client
            self._client = async_sessionmaker(
                bind=self._engine, class_=AsyncSession, expire_on_commit=False
            )
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to database: {e}")

    async def _disconnect(self) -> None:
        """Disconnect from database."""
        try:
            if self._engine:
                await self._engine.dispose()
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to disconnect from database: {e}")
        finally:
            self._engine = None
            self._client = None
