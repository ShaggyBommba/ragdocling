from typing import Any, Literal

from pydantic import BaseModel, Field


class ComputeSettings(BaseModel):
    device: str = "auto"  # "auto", "cpu", "cuda", etc.
    num_threads: int = 4


class OcrSettings(BaseModel):
    enabled: bool = True
    languages: list[str] = Field(default_factory=lambda: ["en"])


class TableSettings(BaseModel):
    enabled: bool = True
    quality: Literal["fast", "balanced", "accurate"] = "accurate"


class EnrichmentSettings(BaseModel):
    code: bool = True
    formulas: bool = True
    picture_classification: bool = False
    picture_description: bool = True


class ImageSettings(BaseModel):
    scale: float = 1.5
    page_images: bool = True
    picture_images: bool = True
    parsed_pages: bool = False


class DescriptionServiceSettings(BaseModel):
    use_remote_api: bool = True
    url: str = "http://localhost:1234/api/v1/chat"
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "qwen3.5-9b-mlx",
            "seed": 42,
            "max_completion_tokens": 200,
        }
    )
    timeout: float = 90.0
    concurrency: int = 1
    prompt: str = "Describe this image in a few sentences. Be concise and accurate."


class EmbeddingSettings(BaseModel):
    model: str = "mlx-community/Qwen3-Embedding-4B-4bit-DWQ"
    max_tokens: int = 512


class PipelineRuntimeSettings(BaseModel):
    document_timeout: float | None = 120.0
    artifacts_path: str | None = None
    allow_external_plugins: bool = False
    force_backend_text: bool = False
    ocr_batch_size: int = 4
    layout_batch_size: int = 4
    table_batch_size: int = 4
    batch_polling_interval_seconds: float = 0.5
    queue_max_size: int = 100


class ExtractionSettings(BaseModel):
    compute: ComputeSettings = Field(default_factory=ComputeSettings)
    ocr: OcrSettings = Field(default_factory=OcrSettings)
    tables: TableSettings = Field(default_factory=TableSettings)
    enrichments: EnrichmentSettings = Field(default_factory=EnrichmentSettings)
    images: ImageSettings = Field(default_factory=ImageSettings)
    description: DescriptionServiceSettings = Field(
        default_factory=DescriptionServiceSettings
    )
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    runtime: PipelineRuntimeSettings = Field(default_factory=PipelineRuntimeSettings)
