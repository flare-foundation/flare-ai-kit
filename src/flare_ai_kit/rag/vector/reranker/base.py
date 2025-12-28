"""Base class for reranking retrieved passages."""

from abc import ABC, abstractmethod

from flare_ai_kit.common import SemanticSearchResult


class BaseReranker(ABC):
    """
    Abstract base class for reranking modules.

    Rerankers take a query and a list of candidate passages from initial
    retrieval and re-score them based on relevance to the query.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[SemanticSearchResult],
        top_k: int | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Rerank candidate passages based on relevance to the query.

        Args:
            query: The user query to score passages against.
            candidates: List of SemanticSearchResult from initial retrieval.
            top_k: Optional limit on number of results to return.
                   If None, returns all candidates that pass the threshold.

        Returns:
            Reranked list of SemanticSearchResult sorted by relevance score
            (highest first). The score field will contain the reranker score
            normalized to 0-1 range.

        """
