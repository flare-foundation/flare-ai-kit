"""Base Embeddings interactions."""

from abc import ABC, abstractmethod

from google.generativeai.embedding import (
    EmbeddingTaskType,
)


class BaseEmbedding(ABC):
    """Base Embeddings interactions."""

    @abstractmethod
    def embed_content(
        self,
        embedding_model: str,
        contents: str,
        task_type: EmbeddingTaskType | None = None,
        title: str | None = None,
    ) -> list[float]:
        """Generate embedding over content."""
