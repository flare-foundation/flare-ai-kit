"""Defines the abstract base class for embedding interactions within Flare AI Kit."""

from abc import ABC, abstractmethod


class BaseEmbedding(ABC):
    """
    Abstract base class for embedding models.

    Subclasses must implement the `embed_content` method to provide
    functionality for generating text embeddings.
    """

    @abstractmethod
    def embed_content(
        self,
        contents: str | list[str],
        title: str | None = None,
        task_type: str | None = None,
    ) -> list[list[float]]:
        """
        Generates embeddings for the provided text content(s).

        Args:
            contents: The text content to embed. Can be a single string or a
                      list of strings for batch processing.
            title: An optional title associated with the content, which might
                   be used by some models (e.g., for RETRIEVAL_DOCUMENT task type).
            task_type: An optional task type hint (e.g., "RETRIEVAL_DOCUMENT",
                       "SEMANTIC_SIMILARITY") to potentially optimize the embeddings
                       for a specific use case, depending on the model.

        Returns:
            A list of embedding vectors (each vector being a list of floats).
            The list will contain one vector if a single string was input, or
            multiple vectors corresponding to the input list order.

        Raises:
            EmbeddingsError: If the embedding generation fails (e.g., API errors,
                             invalid input, no embeddings returned). Specific details
                             should be included in the exception message or cause.
            NotImplementedError: If the method is not implemented by a subclass.

        """
