"""Base class for VectorDB retriever."""

from abc import ABC, abstractmethod

from flare_ai_kit.common import SemanticSearchResult


class BaseRetriever(ABC):
    """Base class for VectorDB retriever."""

    @abstractmethod
    def semantic_search(
        self, query: str, collection_name: str, top_k: int = 5
    ) -> list[SemanticSearchResult]:
        """Perform semantic search using vector embeddings."""

    @abstractmethod
    def keyword_search(
        self, keywords: list[str], collection_name: str, top_k: int = 5
    ) -> list[SemanticSearchResult]:
        """Perform semantic search using vector embeddings."""
