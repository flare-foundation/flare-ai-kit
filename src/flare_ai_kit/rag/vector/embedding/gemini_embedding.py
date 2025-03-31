"""Gemini Embedding Provider."""

from typing import override

import structlog
from google.generativeai.client import (
    configure,  # type: ignore[reportUnknownVariableType]
)
from google.generativeai.embedding import (
    EmbeddingTaskType,
)
from google.generativeai.embedding import (
    embed_content as _embed_content,  # type: ignore[reportUnknownVariableType]
)

from .base import BaseEmbedding

logger = structlog.get_logger(__name__)


class GeminiEmbedding(BaseEmbedding):
    """Class to generate Gemini embeddings."""

    def __init__(self, api_key: str) -> None:
        """
        Initialize Gemini with API credentials.

        This client uses google.generativeai.

        Args:
            api_key (str): Google API key for authentication

        """
        configure(api_key=api_key)

    @override
    def embed_content(
        self,
        embedding_model: str,
        contents: str,
        task_type: EmbeddingTaskType | None = None,
        title: str | None = None,
    ) -> list[float]:
        """
        Generate text embeddings using Gemini.

        Args:
            embedding_model (str): The embedding model to use
                (e.g., "text-embedding-004").
            contents (str): The text to be embedded.
            task_type: Type of embedding task
            title: Title for content

        Returns:
            list[float]: The generated embedding vector.

        """
        response = _embed_content(
            model=embedding_model, content=contents, task_type=task_type, title=title
        )
        try:
            embedding = response["embedding"]
        except (KeyError, IndexError) as e:
            msg = "Failed to extract embedding from response."
            raise ValueError(msg) from e
        return embedding
