"""Artifact repository implementation."""

from typing import Any, List, Optional

from dacke.application.ports.repository import AclLayer, Repository
from dacke.domain.aggregates.artifact import Artifact
from dacke.domain.values.artifact import ArtifactID, ArtifactMetadata, ObjectAddress
from dacke.domain.values.collection import CollectionID
from dacke.infrastructure.exceptions import (
    DatabaseOperationError,
)
from dacke.infrastructure.repositories.providers.postgres.models import ArtifactsTable
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


class ArtifactMetadataAcl(AclLayer[Artifact, ArtifactsTable]):
    """Translation layer between Artifact domain and ORM."""

    @staticmethod
    def to_domain(orm: ArtifactsTable, *args: Any, **kwargs: Any) -> Artifact:
        """Convert ORM model to domain entity."""
        metadata = ArtifactMetadata.create(
            filename=orm.filename,
            source=orm.source,
            size_bytes=orm.size_bytes,
            mime_type=orm.mime_type,
            checksum=orm.checksum,
            author=orm.author or "unknown",
        )

        address = ObjectAddress.from_uri(orm.object_address)

        artifact = Artifact(
            collection_id=CollectionID.from_hex(orm.collection_id),
            identity=ArtifactID.from_hex(orm.id),
            metadata=metadata,
            address=address,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

        return artifact

    @staticmethod
    def from_domain(
        domain: Artifact, collection_id: CollectionID, *args: Any, **kwargs: Any
    ) -> ArtifactsTable:
        """Convert domain entity to ORM model."""
        return ArtifactsTable(
            id=str(domain.identity),
            collection_id=str(collection_id),
            object_address=domain.address.s3_uri,
            filename=domain.metadata.filename,
            source=str(domain.metadata.source),
            size_bytes=domain.metadata.size_bytes,
            mime_type=domain.metadata.mime_type,
            checksum=domain.metadata.checksum,
            author=domain.metadata.author,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )


class ArtifactMetadataRepository(Repository):
    """Repository for persisting and retrieving Artifact entities."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._client: Optional[async_sessionmaker[AsyncSession]] = None
        self._engine: Optional[AsyncEngine] = None

    async def _connect(self) -> None:
        """Connect to database."""
        self._engine = create_async_engine(
            self.connection_string, echo=True, pool_pre_ping=True, poolclass=NullPool
        )

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

    async def save_artifact(
        self, artifact: Artifact, collection_id: CollectionID
    ) -> None:
        """Save an artifact to the database."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                orm = ArtifactMetadataAcl.from_domain(artifact, collection_id)
                session.add(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save artifact: {e}") from e

    async def get_artifact_by_id(self, artifact_id: ArtifactID) -> Optional[Artifact]:
        """Retrieve an artifact by ID."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(ArtifactsTable).where(ArtifactsTable.id == str(artifact_id))
                )
                orm = result.scalar_one_or_none()
                if orm is None:
                    return None
                return ArtifactMetadataAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve artifact: {e}") from e

    async def get_artifacts_by_collection_id(
        self, collection_id: CollectionID
    ) -> List[Artifact]:
        """Retrieve all artifacts in a collection."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(ArtifactsTable).where(
                        ArtifactsTable.collection_id == str(collection_id)
                    )
                )
                orm_list = result.scalars().all()
                return [ArtifactMetadataAcl.to_domain(orm) for orm in orm_list]
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve artifacts by collection ID: {e}"
            ) from e

    async def get_artifact_by_filename(
        self, collection_id: CollectionID, filename: str
    ) -> Optional[Artifact]:
        """Retrieve an artifact by collection ID and filename."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(ArtifactsTable).where(
                        (ArtifactsTable.collection_id == str(collection_id))
                        & (ArtifactsTable.filename == filename)
                    )
                )
                orm = result.scalar_one_or_none()
                if orm is None:
                    return None
                return ArtifactMetadataAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve artifact by filename: {e}"
            ) from e

    async def delete_artifact(self, artifact_id: ArtifactID) -> None:
        """Delete an artifact by ID."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                await session.execute(
                    delete(ArtifactsTable).where(ArtifactsTable.id == str(artifact_id))
                )
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to delete artifact: {e}") from e

    async def delete_artifacts_by_collection_id(
        self, collection_id: CollectionID
    ) -> None:
        """Delete all artifacts in a collection."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                await session.execute(
                    delete(ArtifactsTable).where(
                        ArtifactsTable.collection_id == str(collection_id)
                    )
                )
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to delete artifacts by collection ID: {e}"
            ) from e

    async def update_artifact(
        self, artifact: Artifact, collection_id: CollectionID
    ) -> None:
        """Update an artifact in the database."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                orm = ArtifactMetadataAcl.from_domain(artifact, collection_id)
                await session.merge(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to update artifact: {e}") from e

    async def list_artifacts(self) -> List[Artifact]:
        """List all artifacts."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(select(ArtifactsTable))
                orm_list = result.scalars().all()
                return [ArtifactMetadataAcl.to_domain(orm) for orm in orm_list]
        except Exception as e:
            raise DatabaseOperationError(f"Failed to list artifacts: {e}") from e
