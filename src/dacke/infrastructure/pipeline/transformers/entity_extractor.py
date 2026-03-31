import asyncio
import json
from logging import getLogger
from typing import Any

import httpx

from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document
from dacke.domain.entities.chunk import Chunk

logging = getLogger(__name__)

_SYSTEM_PROMPT = (
    "Extract all named entities from the text passage. "
    "Include: people, organizations, locations, dates, products, and technologies.\n\n"
    "Return ONLY a JSON array of strings, one entity per element. "
    "Use the exact form as it appears in the text. No explanation, no markdown, just the array.\n\n"
    'Example: ["Anthropic", "Claude", "San Francisco", "2024", "GPT-4"]'
)

_USER_PROMPT = "{text}"


class EntityExtractorTransformer(Transformer[Document, Document]):
    """Extracts named entities from each chunk and appends them to metadata['tags'].

    Entities are deduplicated and merged with any tags already present
    (e.g. from PatternMatchTransformer), so transformers compose cleanly
    regardless of execution order.
    """

    def __init__(
        self,
        url: str = "http://localhost:1234/v1/chat/completions",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 120.0,
        concurrency: int = 2,
    ) -> None:
        self._url = url
        self._params = params or {
            "model": "qwen3.5-9b-mlx",
            "max_completion_tokens": 300,
            "enable_thinking": False,
        }
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _extract(self, client: httpx.AsyncClient, chunk: Chunk) -> list[str]:
        payload = {
            **self._params,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT.format(text=chunk.content[:2000])},
            ],
        }
        async with self._semaphore:
            try:
                response = await client.post(
                    self._url,
                    headers=self._headers,
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                entities = json.loads(content)
                return [str(e) for e in entities if e]
            except Exception as e:
                logging.warning(f"Chunk {chunk.identity}: entity extraction failed — {e}")
                return []

    async def transform(self, document: Document) -> Document:
        chunks = document.chunks
        logging.info(f"EntityExtractorTransformer: extracting entities from {len(chunks)} chunk(s)")

        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[self._extract(client, chunk) for chunk in chunks]
            )

        total_entities = 0
        for chunk, entities in zip(chunks, results):
            if not entities:
                continue
            existing = list(chunk.metadata.get("tags") or [])
            merged = existing + [e for e in entities if e not in existing]
            chunk.metadata["tags"] = merged
            total_entities += len(entities)
            logging.debug(f"Chunk {chunk.identity}: {len(entities)} entities extracted")

        logging.info(f"EntityExtractorTransformer: done — {total_entities} entities across {len(chunks)} chunk(s)")
        return document
