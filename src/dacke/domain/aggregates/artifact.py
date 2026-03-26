import hashlib
import io
from dataclasses import replace
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, PrivateAttr

from dacke.domain.exceptions import DomainError
from dacke.domain.values.artifact import (
    ArtifactID,
    ArtifactMetadata,
    Blob,
    ObjectAddress,
)
from dacke.domain.values.collection import CollectionID


class Artifact(BaseModel):
    """
    A Domain Entity representing a stored file/document.
    Unlike Value Objects, Entities are defined by their unique identity.

    Attributes:
        identity: Unique identifier (ArtifactID) for the artifact.
        metadata: Immutable metadata (filename, source, size, mime type, checksum, author).
        address: Storage location (S3/MinIO bucket, prefix, filename).
        created_at: Timestamp when the artifact was created.
        updated_at: Timestamp when the artifact was last modified.
        _content: Internal binary content (lazy-loaded, not persisted).

    Invariants:
        - Identity is deterministic and unique for the same storage address.
        - Metadata.size_bytes must match actual content length when content is loaded.
        - Address must point to a valid storage location (bucket + key).
        - Address.filename must match metadata.filename.
        - created_at must be <= updated_at.
        - updated_at must reflect the last time content or metadata changed.
        - Content is optional (lazy-loaded) but when present, must be non-empty bytes.
        - Metadata checksum must be valid for the stored content (if verified).
        - All value objects (identity, metadata, address) must be immutable.

    """

    identity: ArtifactID
    metadata: ArtifactMetadata
    address: ObjectAddress
    collection_id: CollectionID = Field(
        ..., description="ID of the collection this artifact belongs to"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Internal binary content, excluded from repr to avoid memory issues
    _content: Optional[bytes] = PrivateAttr(default=None)

    @classmethod
    def create(
        cls,
        collection_id: CollectionID,
        metadata: ArtifactMetadata,
        address: ObjectAddress,
        content: Optional[bytes] = None,
    ) -> "Artifact":
        instance = cls(
            collection_id=collection_id,
            identity=ArtifactID.from_checksum(
                metadata.checksum, namespace=collection_id
            ),
            metadata=metadata,
            address=address,
        )

        if content is not None:
            instance.set_content(content)

        return instance

    @property
    def size_kb(self) -> float:
        return self.metadata.size_kb

    @property
    def size_mb(self) -> float:
        return self.metadata.size_mb

    def set_content(self, content: Union[bytes, io.BytesIO]) -> None:
        """
        Assigns content from raw bytes or a BytesIO stream.
        Automatically handles stream seeking and metadata updates.
        """
        if isinstance(content, io.BytesIO):
            content.seek(0)
            self._content = content.read()
        else:
            self._content = content

        checksum = hashlib.md5(self._content).hexdigest()
        self.metadata = replace(
            self.metadata, size_bytes=len(self._content), checksum=checksum
        )
        self.updated_at = datetime.now()

    @property
    def as_blob(self) -> Blob:
        """
        Converts the entity's current state into a Blob Value Object.
        Renamed from 'read' to 'as_blob' to indicate a type conversion.
        """
        if self._content is None:
            raise DomainError(f"Content for artifact {self.identity} is not loaded.")

        return Blob(
            address=self.address,
            content=self._content,
            media_type=self.metadata.mime_type,
        )

    @property
    def content(self) -> bytes:
        if self._content is None:
            raise DomainError(f"Content for artifact {self.identity} is not loaded.")
        return self._content

    @property
    def has_content(self) -> bool:
        return self._content is not None
