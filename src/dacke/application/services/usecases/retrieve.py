from pydantic import AnyUrl
from qdrant_client.http.models import ScoredPoint  # noqa: TCH002

from dacke.application.ports.embedder import Embedder
from dacke.application.ports.reranker import Reranker
from dacke.application.ports.usecase import UseCase
from dacke.domain.entities.chunk import Chunk
from dacke.domain.values.document import DocumentID
from dacke.domain.values.pipeline import PipelineID
from dacke.dto.retrieve import RetrieveDTO, RetrieveResultDTO
from dacke.infrastructure.repositories.providers.postgres.repo_pipeline import (
    PipelineRepository,
)
from dacke.infrastructure.repositories.providers.qdrant.repo_embedding import (
    QdrantEmbeddingRepository,
)


class RetrieveUseCase(UseCase[RetrieveDTO, list[RetrieveResultDTO]]):
    def __init__(
        self,
        embedder: Embedder,
        embedding_repo: QdrantEmbeddingRepository,
        pipeline_repo: PipelineRepository,
        reranker: Reranker,
    ) -> None:
        self.embedder = embedder
        self.embedding_repo = embedding_repo
        self.pipeline_repo = pipeline_repo
        self.reranker = reranker

    async def execute(self, dto: RetrieveDTO) -> list[RetrieveResultDTO]:
        pipeline = await self.pipeline_repo.get_pipeline_by_id(dto.pipeline_id)
        if pipeline is None:
            return []

        query_chunk = Chunk.create(
            content=dto.query,
            document_id=DocumentID.generate(),
            reference="query",
            origin=AnyUrl("http://query"),
        )
        embedding = await self.embedder.embed(
            query_chunk, pipeline.extraction_settings.embedding
        )

        reranker_settings = dto.reranker
        fetch_k = (
            reranker_settings.oversample
            if reranker_settings and reranker_settings.enabled
            else dto.top_k
        )

        points = await self.embedding_repo.search(
            query_vector=embedding.vector,
            pipeline_id=dto.pipeline_id,
            top_k=fetch_k,
            tags=dto.tags,
            origins=dto.origins,
        )

        if reranker_settings and reranker_settings.enabled and points:
            texts = [p.payload.get("text", "") if p.payload else "" for p in points]
            ranked = await self.reranker.rerank(
                query=dto.query,
                documents=texts,
                top_n=dto.top_k,
                model=reranker_settings.model,
                base_url=reranker_settings.base_url,
            )
            pairs: list[tuple[ScoredPoint, float]] = [(points[r.index], r.score) for r in ranked]
            if dto.expand_links:
                pairs = await self._expand_links(pairs, dto.pipeline_id)
            total = len(pairs)
            return [
                RetrieveResultDTO.from_point(p, index=i + 1, total=total, score_override=score)
                for i, (p, score) in enumerate(pairs)
            ]

        plain_pairs: list[tuple[ScoredPoint, float]] = [(p, p.score) for p in points]
        if dto.expand_links:
            plain_pairs = await self._expand_links(plain_pairs, dto.pipeline_id)
        total = len(plain_pairs)
        return [
            RetrieveResultDTO.from_point(p, index=i + 1, total=total, score_override=score)
            for i, (p, score) in enumerate(plain_pairs)
        ]

    async def _expand_links(
        self,
        ranked_pairs: list[tuple[ScoredPoint, float]],
        pipeline_id: PipelineID,
    ) -> list[tuple[ScoredPoint, float]]:
        seen_ids: set = {p.id for p, _ in ranked_pairs}

        linked_origins: list[str] = []
        for point, _ in ranked_pairs:
            payload = point.payload or {}
            for url in payload.get("references") or []:
                if url not in linked_origins:
                    linked_origins.append(url)

        if not linked_origins:
            return ranked_pairs

        linked_points = await self.embedding_repo.fetch_by_origin(
            origins=linked_origins,
            pipeline_id=pipeline_id,
        )

        expansion: list[tuple[ScoredPoint, float]] = []
        for lp in linked_points:
            if lp.id not in seen_ids:
                seen_ids.add(lp.id)
                expansion.append((lp, 0.0))

        return ranked_pairs + expansion
