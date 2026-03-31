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
    "You are a search query generator. Given a text passage, generate realistic "
    "search queries a user might type. Return ONLY a JSON object with two keys:\n"
    '  "positive": list of 3 queries this passage directly answers\n'
    '  "negative": list of 3 queries this passage does NOT answer\n'
    "No explanation, no markdown, just the JSON object."
)

_USER_PROMPT = "Text passage:\n\n{text}"


class QueryGenerationTransformer(Transformer[Document, Document]):
    """Generates positive and negative search queries for each chunk using
    an OpenAI-compatible chat completions endpoint.

    Positive queries: questions this chunk directly answers.
    Negative queries: plausible-sounding questions this chunk does NOT answer.

    Results are stored in chunk.metadata['positive_queries'] and
    chunk.metadata['negative_queries'].
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
        self._params = params or {"model": "qwen3.5-9b-mlx", "max_completion_tokens": 300, "enable_thinking": False}
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _generate(self, client: httpx.AsyncClient, chunk: Chunk) -> tuple[list[str], list[str]]:
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
                data = json.loads(content)
                positive = [str(q) for q in data.get("positive", [])]
                negative = [str(q) for q in data.get("negative", [])]
                return positive, negative
            except Exception as e:
                logging.warning(f"Chunk {chunk.identity}: query generation failed — {e}")
                return [], []

    async def transform(self, document: Document) -> Document:
        chunks = document.chunks
        logging.info(f"QueryGenerationTransformer: generating queries for {len(chunks)} chunk(s)")

        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[self._generate(client, chunk) for chunk in chunks]
            )

        positive_total = 0
        negative_total = 0
        for chunk, (positive, negative) in zip(chunks, results):
            chunk.metadata["positive_queries"] = positive if positive else None
            chunk.metadata["negative_queries"] = negative if negative else None
            positive_total += len(positive)
            negative_total += len(negative)
            logging.debug(
                f"Chunk {chunk.identity}: {len(positive)} positive, {len(negative)} negative queries"
            )

        logging.info(
            f"QueryGenerationTransformer: done — "
            f"{positive_total} positive, {negative_total} negative queries across {len(chunks)} chunk(s)"
        )
        return document
