"""Shared helpers for transformer unit tests."""

from unittest.mock import MagicMock

from pydantic import AnyUrl

from dacke.domain.aggregates.document import Document
from dacke.domain.entities.chunk import Chunk
from dacke.domain.values.document import DocumentID, DocumentMetadata

_ORIGIN = AnyUrl("https://example.com/doc.pdf")


def make_doc(*contents: str) -> Document:
    """Build a Document with one Chunk per content string."""
    doc_id = DocumentID.generate()
    chunks = [
        Chunk.create(
            content=content,
            document_id=doc_id,
            reference=f"chunk-{i}",
            origin=_ORIGIN,
        )
        for i, content in enumerate(contents)
    ]
    return Document(
        identity=doc_id,
        metadata=DocumentMetadata(
            title="Test Doc",
            origin=_ORIGIN,
            source_url=_ORIGIN,
        ),
        chunks=chunks,
    )


def llm_response(content: str) -> MagicMock:
    """Return a mock httpx Response for a chat-completions LLM call."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return mock_resp
