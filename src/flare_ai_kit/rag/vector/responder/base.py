"""Defines the abstract base class for generating responses in a RAG system."""

from abc import ABC, abstractmethod

from flare_ai_kit.common import SemanticSearchResult


class BaseResponder(ABC):
    """Abstract class for generating a final response query and retrieved context."""

    @abstractmethod
    def generate_response(self, query: str, context: list[SemanticSearchResult]) -> str:
        """
        Generates a coherent response based on the user's query and retrieved documents.

        Args:
            query: The original user query.
            context: A list of SemanticSearchResult objects containing the
                     retrieved text chunks and their relevance scores.

        Returns:
            A string containing the synthesized answer.

        """
