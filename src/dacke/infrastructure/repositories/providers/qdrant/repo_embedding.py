"""Qdrant-backed per-pipeline embedding repository."""

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    Record,
    ScoredPoint,
    VectorParams,
)

from dacke.application.ports.repository import Repository
from dacke.domain.entities.embedding import Embedding
from dacke.domain.values.pipeline import PipelineID
from dacke.infrastructure.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)


class QdrantEmbeddingRepository(Repository):
    """Stores embeddings in per-pipeline Qdrant collections.

    Each pipeline maps to a Qdrant collection named `embeddings_{pipeline_hex}`.
    Collections are created on first write with COSINE distance.
    """

    def __init__(self, qdrant_url: str) -> None:
        super().__init__()
        self.qdrant_url = qdrant_url
        self._client: AsyncQdrantClient | None = None
        self._collection_cache: set[str] = set()

    async def _connect(self) -> None:
        self._client = AsyncQdrantClient(url=self.qdrant_url)

    async def _disconnect(self) -> None:
        try:
            if self._client is not None:
                await self._client.close()
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to disconnect from Qdrant: {e}"
            ) from e
        finally:
            self._client = None
            self._collection_cache.clear()

    async def _ensure_collection(self, collection_name: str, vector_size: int) -> None:
        if collection_name in self._collection_cache:
            return
        assert self._client is not None
        exists = await self._client.collection_exists(collection_name)
        if not exists:
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(
                f"Created Qdrant collection '{collection_name}' (dims={vector_size})"
            )
        self._collection_cache.add(collection_name)

    async def save_many(
        self, embeddings: list[Embedding], pipeline_id: PipelineID
    ) -> None:
        if not embeddings:
            return
        if self._client is None:
            await self._connect()

        try:
            assert self._client is not None
            collection_name = f"embeddings_{pipeline_id}"
            vector_size = len(embeddings[0].vector)
            await self._ensure_collection(collection_name, vector_size)

            points = [
                PointStruct(
                    id=str(embedding.identity),
                    vector=embedding.vector,
                    payload={**embedding.metadata},
                )
                for embedding in embeddings
            ]
            await self._client.upsert(
                collection_name=collection_name, points=points, wait=True
            )
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to save embeddings to Qdrant: {e}"
            ) from e

    async def search(
        self,
        query_vector: list[float],
        pipeline_id: PipelineID,
        top_k: int = 5,
        tags: list[str] | None = None,
        origins: list[str] | None = None,
    ) -> list[ScoredPoint]:
        if self._client is None:
            await self._connect()
        assert self._client is not None
        collection_name = f"embeddings_{pipeline_id}"

        conditions: list[FieldCondition] = []
        if tags:
            conditions.extend(
                FieldCondition(key="tags", match=MatchValue(value=tag)) for tag in tags
            )
        if origins:
            conditions.append(FieldCondition(key="origin", match=MatchAny(any=origins)))
        query_filter = Filter(must=conditions) if conditions else None

        try:
            result = await self._client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
                query_filter=query_filter,
            )
            return result.points
        except (UnexpectedResponse, ValueError):
            return []
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to search Qdrant collection '{collection_name}': {e}"
            ) from e

    async def delete_by_origin(
        self,
        origins: list[str],
        pipeline_id: PipelineID,
    ) -> None:
        """Delete all points whose 'origin' payload field matches any value in *origins*."""
        if not origins:
            return
        if self._client is None:
            await self._connect()
        assert self._client is not None

        collection_name = f"embeddings_{pipeline_id}"
        delete_filter = Filter(
            must=[FieldCondition(key="origin", match=MatchAny(any=origins))]
        )

        try:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=delete_filter,
                wait=True,
            )
        except (UnexpectedResponse, ValueError):
            pass
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to delete by origin from Qdrant collection '{collection_name}': {e}"
            ) from e

    async def fetch_by_origin(
        self,
        origins: list[str],
        pipeline_id: PipelineID,
    ) -> list[ScoredPoint]:
        """Return all points whose 'origin' payload field matches any value in *origins*.

        Results are returned as ScoredPoint with score=0.0.
        """
        if not origins:
            return []
        if self._client is None:
            await self._connect()
        assert self._client is not None

        collection_name = f"embeddings_{pipeline_id}"
        scroll_filter = Filter(
            must=[FieldCondition(key="origin", match=MatchAny(any=origins))]
        )

        records: list[Record] = []
        next_offset = None

        try:
            while True:
                batch, next_offset = await self._client.scroll(  # type: ignore[assignment]
                    collection_name=collection_name,
                    scroll_filter=scroll_filter,
                    limit=100,
                    offset=next_offset,
                    with_payload=True,
                    with_vectors=False,
                )
                records.extend(batch)
                if next_offset is None:
                    break
        except (UnexpectedResponse, ValueError):
            return []
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to fetch by origin from Qdrant collection '{collection_name}': {e}"
            ) from e

        return [
            ScoredPoint(
                id=record.id,
                version=0,
                score=0.0,
                payload=record.payload,
                vector=None,
            )
            for record in records
        ]
