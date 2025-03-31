"""Base Embeddings interactions."""

from abc import ABC, abstractmethod


class BaseEmbedding(ABC):
    """Base Embeddings interactions."""

    @abstractmethod
    def embed_content(
        self, contents: str, title: str | None = None, task_type: str | None = None
    ) -> list[list[float]]:
        """Generate embedding over content."""
