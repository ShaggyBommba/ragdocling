from abc import ABC, abstractmethod

from dacke.domain.entities.chunk import Chunk
from dacke.domain.entities.embedding import Embedding
from dacke.domain.values.extraction import EmbeddingSettings


class Embedder(ABC):
    """Port for embedding services.

    Implementations receive a Chunk and return an Embedding produced
    by whatever model/endpoint is configured via EmbeddingSettings.
    """

    @abstractmethod
    async def embed(self, chunk: Chunk, settings: EmbeddingSettings) -> Embedding:
        """Embed a single chunk and return the resulting Embedding entity."""
        ...

    @abstractmethod
    async def embed_many(
        self, chunks: list[Chunk], settings: EmbeddingSettings
    ) -> list[Embedding]:
        """Embed multiple chunks in one request where the backend supports batching."""
        ...
