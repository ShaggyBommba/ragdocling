from pydantic import BaseModel

from dacke.domain.aggregates.pipeline import Pipeline
from dacke.domain.values.collection import CollectionID


class CreatePipelineDTO(BaseModel):
    name: str
    collection_id: str

    def to_domain(self) -> Pipeline:
        return Pipeline.create(
            name=self.name, collection_id=CollectionID.from_hex(self.collection_id)
        )


class UpdatePipelineDTO(BaseModel):
    id: str
    lifecycle: str


class PipelineDTO(BaseModel):
    id: str
    name: str
    collection_id: str
    lifecycle: str
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, pipeline: Pipeline) -> "PipelineDTO":
        return cls(
            id=str(pipeline.identity),
            name=pipeline.name,
            collection_id=str(pipeline.collection_id),
            lifecycle=pipeline.lifecycle.value,
            created_at=pipeline.created_at.isoformat(),
            updated_at=pipeline.updated_at.isoformat(),
        )
