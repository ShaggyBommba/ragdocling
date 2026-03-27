from pydantic import BaseModel

from dacke.domain.entities.chunk import Chunk
from dacke.domain.values.document import DocumentID, DocumentMetadata


class Document(BaseModel):
    identity: DocumentID
    metadata: DocumentMetadata
    chunks: list[Chunk] = []

    # Get methods for chunks
    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Return a chunk by its ID, or None if not found."""
        for chunk in self.chunks:
            if str(chunk.identity) == chunk_id:
                return chunk
        return None

    def get_chunks(self) -> list[Chunk]:
        """Return the list of chunks associated with the document."""
        return self.chunks

    # Modification methods for chunks
    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk to the document."""
        if chunk.document_id != self.identity:
            raise ValueError("Chunk's document_id does not match Document's identity")
        self.chunks.append(chunk)

    def remove_chunk(self, chunk_id: str) -> None:
        """Remove a chunk from the document by its ID."""
        self.chunks = [
            chunk for chunk in self.chunks if str(chunk.identity) != chunk_id
        ]
