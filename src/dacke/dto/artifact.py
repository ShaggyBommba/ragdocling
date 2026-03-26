import hashlib

from pydantic import BaseModel

from dacke.domain.aggregates.artifact import Artifact
from dacke.domain.values.artifact import ArtifactMetadata, ObjectAddress
from dacke.domain.values.collection import CollectionID


class ArtifactUploadDTO(BaseModel):
    collection_id: str
    file: bytes
    filename: str
    content_type: str

    def to_domain(self) -> Artifact:
        location = ObjectAddress.create(
            bucket="dacke",
            prefix=f"collections/{self.collection_id}/files",
            filename=self.filename,
        )
        metadata = ArtifactMetadata.create(
            filename=self.filename,
            source="upload",
            size_bytes=len(self.file),
            mime_type=self.content_type,
            checksum=hashlib.md5(self.file).hexdigest(),
        )
        artifact = Artifact.create(
            collection_id=CollectionID.from_hex(self.collection_id),
            metadata=metadata,
            address=location,
            content=self.file,
        )
        return artifact


class ArtifactDeleteDTO(BaseModel):
    collection_id: str
    artifact_id: str


class ArtifactDTO(BaseModel):
    id: str
    location: str

    @classmethod
    def from_domain(cls, artifact: Artifact) -> "ArtifactDTO":
        return cls(
            id=str(artifact.identity),
            location=artifact.address.s3_uri,
        )
