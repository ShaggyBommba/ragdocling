"""Collection repository implementation."""

from typing import Any, Optional

from dacke.application.ports.repository import AclLayer, Repository
from dacke.domain.aggregates.collection import Collection
from dacke.domain.values.artifact import ArtifactID
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.workspace import WorkspaceID
from dacke.infrastructure.exceptions import (
    DatabaseOperationError,
)
from dacke.infrastructure.repositories.providers.postgres.models import CollectionsTable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool


class CollectionAcl(AclLayer[Collection, CollectionsTable]):
    """Translation layer between Collection domain and ORM."""

    @staticmethod
    def to_domain(orm: CollectionsTable, *args: Any, **kwargs: Any) -> Collection:
        """Convert ORM model to domain aggregate."""

        return Collection(
            identity=CollectionID.from_hex(orm.id),
            workspace_id=WorkspaceID.from_hex(orm.workspace_id),
            name=orm.name,
            artifact_ids=[
                ArtifactID.from_hex(artifact.id) for artifact in orm.artifacts
            ]
            if orm.artifacts
            else [],
            max_count_files=orm.max_count_files,
            max_file_size_kb=orm.max_file_size_kb,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def from_domain(domain: Collection, *args: Any, **kwargs: Any) -> CollectionsTable:
        """Convert domain aggregate to ORM model."""
        return CollectionsTable(
            id=str(domain.identity),
            workspace_id=str(domain.workspace_id),
            name=domain.name,
            max_count_files=domain.max_count_files,
            max_file_size_kb=domain.max_file_size_kb,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )


class CollectionRepository(Repository):
    """Repository for persisting and retrieving Collection aggregates."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._client: Optional[async_sessionmaker[AsyncSession]] = None
        self._engine: Optional[AsyncEngine] = None

    async def _connect(self) -> None:
        """Connect to database."""
        # Create the asynchronous engine
        self._engine = create_async_engine(
            self.connection_string, echo=True, pool_pre_ping=True, poolclass=NullPool
        )

        # Create a session factory and assign it to self._client
        self._client = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _disconnect(self) -> None:
        """Disconnect from database."""
        try:
            if self._engine:
                await self._engine.dispose()
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to disconnect from database: {e}"
            ) from e
        finally:
            self._engine = None
            self._client = None

    async def save_collection(self, collection: Collection) -> None:
        """Save a collection to the database."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                orm = CollectionAcl.from_domain(collection)
                session.add(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save collection: {e}") from e

    async def get_collection_by_id(
        self, collection_id: CollectionID
    ) -> Optional[Collection]:
        """Retrieve a collection by ID."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "_client should be initialized after _connect"
            async with self._client() as session:
                result = await session.execute(
                    select(CollectionsTable)
                    .options(
                        selectinload(CollectionsTable.artifacts),
                    )
                    .where(CollectionsTable.id == str(collection_id))
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return None
                return CollectionAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve collection: {e}") from e

    async def get_collection_by_name(
        self, collection_name: str
    ) -> Optional[Collection]:
        """Retrieve a collection by name."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "_client should be initialized after _connect"
            async with self._client() as session:
                result = await session.execute(
                    select(CollectionsTable)
                    .options(
                        selectinload(CollectionsTable.artifacts),
                    )
                    .where(CollectionsTable.name == collection_name)
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return None
                return CollectionAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve collection: {e}") from e

    async def delete_collection(self, collection_id: CollectionID) -> None:
        """Delete a collection by ID."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "_client should be initialized after _connect"
            async with self._client() as session:
                result = await session.execute(
                    select(CollectionsTable).where(
                        CollectionsTable.id == str(collection_id)
                    )
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return

                await session.delete(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to delete collection: {e}") from e

    async def list_collections(self) -> list[Collection]:
        """List all collections."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "_client should be initialized after _connect"
            async with self._client() as session:
                result = await session.execute(
                    select(CollectionsTable).options(
                        selectinload(CollectionsTable.artifacts),
                    )
                )
                orm_list = result.unique().scalars().all()
                return [CollectionAcl.to_domain(orm) for orm in orm_list]
        except Exception as e:
            raise DatabaseOperationError(f"Failed to list collections: {e}") from e

    async def update_collection(self, collection: Collection) -> None:
        """Update a collection in the database."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "_client should be initialized after _connect"
            async with self._client() as session:
                # Fetch the existing object and update it
                result = await session.execute(
                    select(CollectionsTable).where(
                        CollectionsTable.id == str(collection.identity)
                    )
                )
                orm = result.scalar_one_or_none()
                if orm is None:
                    raise DatabaseOperationError(
                        f"Collection {collection.identity} not found"
                    )

                # Update the fields
                orm.name = collection.name
                orm.max_count_files = collection.max_count_files
                orm.max_file_size_kb = collection.max_file_size_kb

                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to update collection: {e}") from e
