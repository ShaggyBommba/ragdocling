"""OpenAI-compatible embedding service.

Works with any endpoint that implements the OpenAI embeddings API,
including LM Studio (http://localhost:1234/v1) and OpenAI itself.
"""

import logging

import httpx

from dacke.application.ports.embedder import Embedder
from dacke.domain.entities.chunk import Chunk
from dacke.domain.entities.embedding import Embedding
from dacke.domain.values.extraction import EmbeddingSettings

logger = logging.getLogger(__name__)


class OpenAIEmbedder(Embedder):
    """Calls an OpenAI-compatible /v1/embeddings endpoint."""

    def __init__(self, base_url: str, api_key: str = "lm-studio") -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def embed(self, chunk: Chunk, settings: EmbeddingSettings) -> Embedding:
        results = await self.embed_many([chunk], settings)
        return results[0]

    async def embed_many(
        self, chunks: list[Chunk], settings: EmbeddingSettings
    ) -> list[Embedding]:
        texts = [chunk.content for chunk in chunks]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": settings.model, "input": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        embeddings = sorted(data["data"], key=lambda item: item["index"])

        prompt_tokens: int | None = data.get("usage", {}).get("prompt_tokens")

        logger.info(
            f"Embedded {len(chunks)} chunk(s) with model '{settings.model}' "
            f"({len(embeddings[0]['embedding'])} dims, {prompt_tokens} tokens)"
        )

        return [
            Embedding.create(
                chunk=chunk, model=settings.model, vector=item["embedding"]
            )
            for chunk, item in zip(chunks, embeddings, strict=True)
        ]
