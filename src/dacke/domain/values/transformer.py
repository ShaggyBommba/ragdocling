from typing import Any

from pydantic import BaseModel, Field


class TransformerSettings(BaseModel):
    name: str
    args: list[Any] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
