"""Dynamic per-pipeline embedding repository."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from dacke.application.ports.repository import Repository
from dacke.domain.entities.embedding import Embedding
from dacke.domain.values.pipeline import PipelineID
from dacke.infrastructure.exceptions import DatabaseOperationError


class EmbeddingAcl:
    """Translates Embedding domain entity to a plain dict row."""

    @staticmethod
    def from_domain(embedding: Embedding) -> dict[str, Any]:
        return {
            "id": str(embedding.identity),
            "chunk_id": str(embedding.chunk_id),
            "vector": embedding.vector,
            "model": embedding.metadata["model"],
            "dimensions": embedding.metadata["dimensions"],
            "prompt_tokens": embedding.metadata.get("prompt_tokens"),
            "created_at": datetime.now(),
        }


class PostgresEmbeddingRepository(Repository):
    """Stores embeddings in dynamically created per-pipeline tables."""

    def __init__(self, connection_string: str) -> None:
        super().__init__()
        self.connection_string = connection_string
        self._client: Optional[async_sessionmaker[AsyncSession]] = None
        self._engine: Optional[AsyncEngine] = None
        self._table_cache: dict[str, Table] = {}
        self._metadata = MetaData()

    async def _connect(self) -> None:
        self._engine = create_async_engine(
            self.connection_string, echo=True, pool_pre_ping=True, poolclass=NullPool
        )
        self._client = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _disconnect(self) -> None:
        try:
            if self._engine:
                await self._engine.dispose()
        except Exception as e:
            raise DatabaseOperationError(f"Failed to disconnect from database: {e}") from e
        finally:
            self._engine = None
            self._client = None

    def _build_table(self, pipeline_hex: str) -> Table:
        table_name = f"embeddings_{pipeline_hex}"
        if table_name in self._metadata.tables:
            return self._metadata.tables[table_name]
        return Table(
            table_name,
            self._metadata,
            Column("id", String(32), primary_key=True, nullable=False),
            Column("chunk_id", String(32), nullable=False),
            Column("vector", ARRAY(Float), nullable=False),
            Column("model", String(255), nullable=False),
            Column("dimensions", Integer, nullable=False),
            Column("prompt_tokens", Integer, nullable=True),
            Column("created_at", DateTime, nullable=False),
        )

    async def _ensure_table(self, pipeline_hex: str) -> Table:
        if pipeline_hex not in self._table_cache:
            assert self._engine is not None
            table = self._build_table(pipeline_hex)
            async with self._engine.begin() as conn:
                await conn.run_sync(table.create, checkfirst=True)
            self._table_cache[pipeline_hex] = table
        return self._table_cache[pipeline_hex]

    async def save_many(
        self, embeddings: list[Embedding], pipeline_id: PipelineID
    ) -> None:
        if not embeddings:
            return
        if self._engine is None:
            await self._connect()
        try:
            assert self._engine is not None
            pipeline_hex = str(pipeline_id)
            table = await self._ensure_table(pipeline_hex)
            rows = [EmbeddingAcl.from_domain(e) for e in embeddings]
            stmt = pg_insert(table).values(rows).on_conflict_do_nothing(index_elements=["id"])
            async with self._engine.begin() as conn:
                await conn.execute(stmt)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save embeddings: {e}") from e
