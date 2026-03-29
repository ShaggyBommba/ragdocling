from pydantic import BaseModel

from dacke.domain.entities.chunk import Chunk
from dacke.domain.values.chunk import ChunkID
from dacke.domain.values.embedding import EmbeddingID, EmbeddingMetadata


class Embedding(BaseModel):
    """
    Domain entity representing a vector embedding produced from a Chunk.

    Identity is deterministic: same chunk always produces the same EmbeddingID,
    so re-embedding is idempotent at the identity level.

    Attributes:
        identity:   Unique identifier derived from the source chunk.
        chunk_id:   Reference back to the chunk this embedding was produced from.
        vector:     The raw floating-point embedding vector.
        metadata:   Model name, vector dimensions, and token usage captured at embed time.
    """

    identity: EmbeddingID
    chunk_id: ChunkID
    vector: list[float]
    metadata: EmbeddingMetadata

    @classmethod
    def create(
        cls,
        chunk: Chunk,
        model: str,
        vector: list[float],
        prompt_tokens: int | None = None,
    ) -> "Embedding":
        return cls(
            identity=EmbeddingID.from_chunk(chunk.identity),
            chunk_id=chunk.identity,
            vector=vector,
            metadata=EmbeddingMetadata(
                model=model,
                dimensions=len(vector),
                prompt_tokens=prompt_tokens,
            ),
        )
