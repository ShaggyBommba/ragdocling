"""LM Studio generation-based reranking service.

qwen3-reranker (and similar models) are exposed via LM Studio's /api/v1/chat
endpoint. Each query-document pair is scored individually: the model outputs
"yes" (relevant) or "no" (not relevant). Requests are sent concurrently.
"""

import asyncio
import logging

import httpx

from dacke.application.ports.reranker import RankedResult, Reranker

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Judge whether the following [document] is relevant to the [query]. "
    "Only output 'yes' or 'no'."
)


class OpenAIReranker(Reranker):
    """Calls the LM Studio /api/v1/chat endpoint to score query-document pairs."""

    def __init__(self, api_key: str = "lm-studio") -> None:
        self._api_key = api_key

    async def _score_one(
        self,
        client: httpx.AsyncClient,
        index: int,
        query: str,
        document: str,
        model: str,
        base_url: str,
    ) -> RankedResult:
        url = base_url.rstrip("/") + "/api/v1/chat"
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "system_prompt": _SYSTEM_PROMPT,
                "input": f"[query]: {query}\n[document]: {document}",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        # Log the raw response once so we can see the shape
        logger.info(f"Reranker raw response: {data}")

        # Extract the generated text — handle both str and list values
        raw = (
            data.get("data", {}).get("output")
            or data.get("output")
            or data.get("response")
            or ""
        )
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        output = str(raw).strip().lower()

        score = 1.0 if output.startswith("yes") else 0.0
        return RankedResult(index=index, score=score)

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int,
        model: str,
        base_url: str,
    ) -> list[RankedResult]:
        async with httpx.AsyncClient() as client:
            tasks = [
                self._score_one(client, i, query, doc, model, base_url)
                for i, doc in enumerate(documents)
            ]
            results: list[RankedResult] = await asyncio.gather(*tasks)

        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:top_n]

        logger.info(
            f"Reranked {len(documents)} document(s) with model '{model}', "
            f"returning top {len(results)}"
        )
        return results
