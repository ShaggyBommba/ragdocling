from pydantic import BaseModel

from dacke.domain.entities.attachment import Attachment
from dacke.domain.values.chunk import ChunkID, ChunkMetadata
from dacke.domain.values.document import DocumentID


class Chunk(BaseModel):
    identity: ChunkID
    document_id: DocumentID
    content: str
    metadata: ChunkMetadata
    attachments: list[Attachment] = []

    @classmethod
    def create(
        cls,
        content: str,
        document_id: DocumentID,
        reference: str,
        pages: list[int] | None = None,
        title: str | None = None,
        attachments: list[Attachment] | None = None,
    ) -> "Chunk":
        """Factory method to create a new Chunk with a generated ID."""
        return cls(
            identity=ChunkID.from_ref(reference, namespace=document_id),
            document_id=document_id,
            content=content,
            metadata=ChunkMetadata(pages=pages, order=None, title=title),
            attachments=attachments or [],
        )

    # Get methods for attachments
    def get_attachments(self) -> list[Attachment]:
        """Return the list of attachments associated with the chunk."""
        return self.attachments

    def get_attachment(self, attachment_id: str) -> Attachment | None:
        """Return an attachment by its ID, or None if not found."""
        for att in self.attachments:
            if str(att.identity) == attachment_id:
                return att
        return None

    # Modification methods for attachments
    def add_attachment(self, attachment: Attachment) -> None:
        """Add an attachment to the chunk."""
        self.attachments.append(attachment)

    def remove_attachment(self, attachment_id: str) -> None:
        """Remove an attachment from the chunk by its ID."""
        self.attachments = [
            att for att in self.attachments if str(att.identity) != attachment_id
        ]
