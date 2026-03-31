from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RankedResult:
    index: int
    score: float


class Reranker(ABC):
    """Port for reranking services.

    Implementations receive a query and a list of document texts and return
    scored results sorted by relevance descending.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int,
        model: str,
        base_url: str,
    ) -> list[RankedResult]:
        """Rerank documents against a query.

        Returns up to top_n RankedResult items sorted by score descending.
        Each result's index refers to the position in the input documents list.
        """
        ...
