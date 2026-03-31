import hashlib
from logging import getLogger
from typing import Any

from pydantic import BaseModel, PrivateAttr

from dacke.domain.values.artifact import ArtifactID, ObjectAddress
from dacke.domain.values.attachment import AttachmentPayload, Content
from dacke.domain.values.pipeline import PipelineID

logging = getLogger(__name__)


class Attachment(BaseModel):
    identity: ArtifactID
    location: ObjectAddress
    metadata: dict[str, Any]

    _data: Content | None = PrivateAttr()

    @property
    def type(self) -> str:
        return self.__class__.__name__.lower().replace("attachment", "")

    @classmethod
    def create(
        cls,
        pipeline_id: PipelineID,
        location: ObjectAddress,
        metadata: dict[str, Any],
        content: Content | None = None,
    ) -> "Attachment":
        """Factory method to create an Attachment with a deterministic ID based on its location and pipeline namespace."""
        instance = cls(
            identity=ArtifactID.from_checksum(location.s3_uri, pipeline_id),
            location=location,
            metadata=metadata,
        )

        if content is not None:
            instance.set_content(content)

        return instance

    def set_content(self, content: Content) -> None:
        self._data = content

    @property
    def data(self) -> Content | None:
        return self._data

    @property
    def hash(self) -> str:
        hasher = hashlib.sha256()
        if self._data is not None:
            hasher.update(self._data.hash.encode("utf-8"))
        return hasher.hexdigest()

    @property
    def repr(self) -> str:
        raise NotImplementedError

    @property
    def payload(self) -> AttachmentPayload:
        return AttachmentPayload(
            type=self.type,
            description=self.repr,
            reference=self.location.s3_uri,
        )


class ImageAttachment(Attachment):
    """An attachment representing an image."""

    @property
    def repr(self) -> str:
        caption = str(self.metadata.get("caption", "")).strip()
        description = str(self.metadata.get("description", "")).strip()

        parts = []
        if caption:
            parts.append(f"Caption: {caption}")
        if description:
            parts.append(f"Description: {description}")
        return "\n".join(parts) if parts else "image description not available"


class TableAttachment(Attachment):
    """An attachment representing a table."""

    @property
    def repr(self) -> str:
        caption = str(self.metadata.get("caption", "")).strip()
        description = str(self.metadata.get("description", "")).strip()

        parts = []
        if caption:
            parts.append(f"Caption: {caption}")
        if description:
            parts.append(f"Description: {description}")
        return "\n".join(parts) if parts else "table description not available"
