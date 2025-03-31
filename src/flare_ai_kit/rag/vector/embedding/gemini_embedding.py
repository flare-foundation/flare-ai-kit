"""Embeddings using Gemini."""

from typing import override

from google import genai  # type: ignore[reportMissingTypeStubs]
from google.genai import types  # type: ignore[reportMissingTypeStubs]

from flare_ai_kit.common import EmbeddingsError

from .base import BaseEmbedding


class GeminiEmbedding(BaseEmbedding):
    """Embeddings using Gemini."""

    def __init__(
        self, api_key: str, model: str, output_dimensionality: int | None
    ) -> None:
        self.model = model
        self.output_dimensionality = output_dimensionality
        self.client = genai.Client(api_key=api_key)

    @override
    def embed_content(
        self,
        contents: str,
        title: str | None = None,
        task_type: str | None = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        response = self.client.models.embed_content(  # type: ignore[reportUnknownMemberType]
            model=self.model,
            contents=contents,
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality,
                task_type=task_type,
                title=title,
            ),
        )
        if response.embeddings and len(response.embeddings) >= 1:
            return [embedding.values for embedding in response.embeddings]  # type: ignore[reportReturnType]
        msg = f"Failed to generate embeddings for title={title}"
        raise EmbeddingsError(msg)
