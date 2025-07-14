"""Base class for VectorDB retriever."""

from abc import ABC, abstractmethod
from typing import Any

from flare_ai_kit.common import SemanticSearchResult


class BaseRetriever(ABC):
    """
    Abstract base class for retrieval modules.
    Handles querying the vector database and returning relevant documents.
    """

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
        pass
