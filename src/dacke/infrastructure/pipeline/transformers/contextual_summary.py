import asyncio
from logging import getLogger
from typing import Any

import httpx

from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document
from dacke.domain.entities.chunk import Chunk

logging = getLogger(__name__)

_SYSTEM_PROMPT = (
    "Generate a 1-2 sentence summary of the passage below that captures its main topic "
    "and key claims. Return ONLY the summary, nothing else."
)

_USER_PROMPT = "{text}"


class ContextualSummaryTransformer(Transformer[Document, Document]):
    """Prepends an LLM-generated summary to each chunk's content.

    Based on Anthropic's contextual retrieval approach: embedding both the
    summary and the full text improves recall because queries often match
    the summarised form rather than the raw extraction.

    The summary is prepended as: "{summary}\\n\\n{original_content}"
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
            "max_completion_tokens": 150,
            "enable_thinking": False,
        }
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _summarise(self, client: httpx.AsyncClient, chunk: Chunk) -> str:
        payload = {
            **self._params,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT.format(text=chunk.content)},
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
                summary: str = response.json()["choices"][0]["message"][
                    "content"
                ].strip()
                return summary
            except Exception as e:
                logging.warning(
                    f"Chunk {chunk.identity}: summary generation failed — {e}"
                )
                return ""

    async def transform(self, document: Document) -> Document:
        chunks = document.chunks
        logging.info(
            f"ContextualSummaryTransformer: summarising {len(chunks)} chunk(s)"
        )

        async with httpx.AsyncClient() as client:
            summaries = await asyncio.gather(
                *[self._summarise(client, chunk) for chunk in chunks]
            )

        enriched = 0
        for chunk, summary in zip(chunks, summaries, strict=False):
            if summary:
                chunk.content = f"{summary}\n\n{chunk.content}"
                enriched += 1

        logging.info(
            f"ContextualSummaryTransformer: done — {enriched}/{len(chunks)} chunk(s) enriched"
        )
        return document
