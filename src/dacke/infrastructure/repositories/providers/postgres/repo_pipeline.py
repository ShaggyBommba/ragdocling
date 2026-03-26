"""Pipeline repository implementation."""

from typing import Any, List, Optional

from dacke.application.ports.repository import AclLayer, Repository
from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.values.collection import CollectionID
from dacke.domain.values.extraction import ExtractionSettings
from dacke.domain.values.pipeline import PipelineID, PipelineLifecycle
from dacke.domain.values.transformer import TransformerSettings
from dacke.infrastructure.exceptions import (
    DatabaseOperationError,
)
from dacke.infrastructure.repositories.providers.postgres.models import PipelinesTable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class PipelineAcl(AclLayer[Pipeline, PipelinesTable]):
    """Translation layer between Pipeline domain and ORM."""

    @staticmethod
    def to_domain(orm: PipelinesTable, *args: Any, **kwargs: Any) -> Pipeline:
        """Convert ORM model to domain aggregate."""
        return Pipeline(
            identity=PipelineID.from_hex(orm.id),
            name=orm.name,
            collection_id=CollectionID.from_hex(orm.collection_id),
            lifecycle=orm.lifecycle,
            extraction_settings=ExtractionSettings.model_validate(
                orm.extraction_settings
            ),
            transformations_settings=[
                TransformerSettings.model_validate(item)
                for item in orm.transformations_settings
            ],
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def from_domain(domain: Pipeline, *args: Any, **kwargs: Any) -> PipelinesTable:
        """Convert domain aggregate to ORM model."""
        return PipelinesTable(
            id=str(domain.identity),
            name=domain.name,
            collection_id=str(domain.collection_id),
            extraction_settings=domain.extraction_settings.model_dump(mode="json"),
            transformations_settings=[
                transformer.model_dump(mode="json")
                for transformer in domain.transformations_settings
            ],
            lifecycle=domain.lifecycle.value,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )


class PipelineRepository(Repository):
    """Repository for persisting and retrieving Pipeline aggregates."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._client: Optional[async_sessionmaker[AsyncSession]] = None
        self._engine: Optional[AsyncEngine] = None

    async def _connect(self) -> None:
        """Connect to database."""
        # Create the asynchronous engine
        self._engine = create_async_engine(
            self.connection_string, echo=True, pool_pre_ping=True
        )

        # Create a session factory and assign it to self._client
        self._client = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _disconnect(self) -> None:
        """Disconnect from database."""
        if self._engine:
            await self._engine.dispose()
        self._engine = None
        self._client = None

    async def save_pipeline(self, pipeline: Pipeline) -> None:
        """Save a pipeline to the database."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                orm = PipelineAcl.from_domain(pipeline)
                session.add(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save pipeline: {e}") from e

    async def get_pipeline_by_id(self, pipeline_id: PipelineID) -> Optional[Pipeline]:
        """Retrieve a pipeline by ID."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(PipelinesTable).where(PipelinesTable.id == str(pipeline_id))
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return None
                return PipelineAcl.to_domain(orm)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve pipeline: {e}") from e

    async def get_pipelines_by_collection(
        self, collection_id: CollectionID
    ) -> List[Pipeline]:
        """Retrieve all pipelines in a collection."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(PipelinesTable).where(
                        PipelinesTable.collection_id == str(collection_id)
                    )
                )
                orm_list = result.unique().scalars().all()
                return [PipelineAcl.to_domain(orm) for orm in orm_list]
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve pipelines: {e}") from e

    async def delete_pipeline(self, pipeline_id: PipelineID) -> None:
        """Delete a pipeline by ID."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(PipelinesTable).where(PipelinesTable.id == str(pipeline_id))
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return
                await session.delete(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to delete pipeline: {e}") from e

    async def change_lifecycle(
        self, pipeline_id: PipelineID, stage: PipelineLifecycle
    ) -> None:
        """Change the lifecycle status of a pipeline."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(
                    select(PipelinesTable).where(PipelinesTable.id == str(pipeline_id))
                )
                orm = result.unique().scalar_one_or_none()
                if orm is None:
                    return

                domain = PipelineAcl.to_domain(orm)
                if stage == PipelineLifecycle.PRODUCTION:
                    domain.deploy()
                elif stage == PipelineLifecycle.STAGING:
                    domain.stage()
                elif stage == PipelineLifecycle.ARCHIVED:
                    domain.archive()

                orm = PipelineAcl.from_domain(domain)

                await session.merge(orm)
                await session.commit()
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to change pipeline lifecycle: {e}"
            ) from e

    async def list_pipelines(self) -> List[Pipeline]:
        """List all pipelines."""
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            async with self._client() as session:
                result = await session.execute(select(PipelinesTable))
                orm_list = result.unique().scalars().all()
                return [PipelineAcl.to_domain(orm) for orm in orm_list]
        except Exception as e:
            raise DatabaseOperationError(f"Failed to list pipelines: {e}") from e
