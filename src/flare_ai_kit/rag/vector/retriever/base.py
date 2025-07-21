"""Base class for VectorDB retriever."""

from abc import ABC, abstractmethod

from flare_ai_kit.common import SemanticSearchResult


class BaseRetriever(ABC):
    """
    Abstract base class for retrieval modules.

    Handles querying the vector database and returning relevant documents.
    """

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

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[SemanticSearchResult]:
        """
        Retrieve the top-k most relevant documents for a given query.

        Args:
            query (str): The search query string.
            top_k (int): Number of top results to return.

        Returns:
            list[SemanticSearchResult]: List of documents with content and metadata.

        """
