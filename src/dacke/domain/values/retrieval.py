from pydantic import BaseModel


class RerankerSettings(BaseModel):
    enabled: bool = False
    model: str = "jina-reranker-v2-base-en"
    base_url: str = "http://localhost:1234"
    oversample: int = 20
