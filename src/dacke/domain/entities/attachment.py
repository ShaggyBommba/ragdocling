import hashlib
from logging import getLogger
from typing import Any

from pydantic import BaseModel, PrivateAttr

from dacke.domain.values.artifact import ArtifactID, ObjectAddress
from dacke.domain.values.attachment import AttachmentTypes, Content
from dacke.domain.values.pipeline import PipelineID

logging = getLogger(__name__)


class Attachment(BaseModel):
    identity: ArtifactID
    location: ObjectAddress
    type: AttachmentTypes
    metadata: dict[str, Any]

    _data: Content | None = PrivateAttr()

    @classmethod
    def create(
        cls,
        pipeline_id: PipelineID,
        location: ObjectAddress,
        attachment_type: AttachmentTypes,
        metadata: dict[str, Any],
        content: Content | None = None,
    ) -> "Attachment":
        """Factory method to create an Attachment with a deterministic ID based on its location and pipeline namespace."""

        instance = cls(
            identity=ArtifactID.from_checksum(location.s3_uri, pipeline_id),
            location=location,
            type=attachment_type,
            metadata=metadata,
        )

        if content is not None:
            instance.set_content(content)

        return instance

    def set_content(self, content: Content) -> None:
        """Set the content of the attachment."""
        self._data = content

    @property
    def data(self) -> Content | None:
        """Get the content of the attachment, if available."""
        return self._data

    @property
    def hash(self) -> str:
        """Compute a hash of the attachment content and metadata for deterministic ID generation."""

        hasher = hashlib.sha256()
        if self._data is not None:
            hasher.update(self._data.hash.encode("utf-8"))

        return hasher.hexdigest()
