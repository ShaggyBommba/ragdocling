import asyncio
from logging import getLogger
from typing import Any

import httpx

from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document
from dacke.domain.entities.chunk import Chunk

logging = getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a text editor. You will receive a raw text passage extracted from a document. "
    "Your job is to clean and improve it while preserving all factual content exactly.\n\n"
    "Fix:\n"
    "- Broken line wrapping and awkward hyphenation from PDF extraction\n"
    "- Garbled characters, encoding artifacts, or OCR errors where obvious\n"
    "- Inconsistent whitespace and stray punctuation\n"
    "- Fragmented sentences caused by column or page breaks\n\n"
    "Do NOT:\n"
    "- Add, remove, or change any facts, names, numbers, or technical terms\n"
    "- Summarise or shorten the text\n"
    "- Add headings, bullet points, or any formatting not already present\n\n"
    "Return ONLY the improved text, nothing else."
)

_USER_PROMPT = "{text}"


class TextEnhancerTransformer(Transformer[Document, Document]):
    """Rewrites each chunk's content using an LLM to fix extraction artefacts.

    Targets common issues from PDF/DOCX extraction: broken line wrapping,
    hyphenation, encoding noise, and fragmented sentences. The factual
    content of each chunk is preserved; only presentation is improved.

    The original content is replaced in-place on chunk.content.
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
            "max_completion_tokens": 1500,
            "enable_thinking": False,
        }
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _enhance(self, client: httpx.AsyncClient, chunk: Chunk) -> str:
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
                enhanced: str = response.json()["choices"][0]["message"][
                    "content"
                ].strip()
                if not enhanced:
                    return chunk.content
                return enhanced
            except Exception as e:
                logging.warning(
                    f"Chunk {chunk.identity}: text enhancement failed — {e}"
                )
                return chunk.content

    async def transform(self, document: Document) -> Document:
        chunks = document.chunks
        logging.info(f"TextEnhancerTransformer: enhancing {len(chunks)} chunk(s)")

        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[self._enhance(client, chunk) for chunk in chunks]
            )

        for chunk, enhanced in zip(chunks, results, strict=False):
            chunk.content = enhanced

        logging.info(f"TextEnhancerTransformer: done — {len(chunks)} chunk(s) enhanced")
        return document
