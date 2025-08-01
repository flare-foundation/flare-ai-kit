"""Embeddings using Gemini."""

from typing import override

import structlog
from google import genai  # pyright: ignore[reportMissingTypeStubs]
from google.genai import types  # pyright: ignore[reportMissingTypeStubs]

from flare_ai_kit.common import EmbeddingsError

from .base import BaseEmbedding

logger = structlog.get_logger(__name__)


class GeminiEmbedding(BaseEmbedding):
    """Generates text embeddings using Google's Gemini models."""

    def __init__(
        self, api_key: str, model: str, output_dimensionality: int | None
    ) -> None:
        """
        Initializes the GeminiEmbedding client.

        Args:
            api_key: Your Google API key for accessing Gemini models.
            model: The specific Gemini embedding model identifier
                   (e.g., "models/embedding-001").
            output_dimensionality: Optional integer to specify a reduced dimension
                                   for the output embeddings if supported by the model.

        Raises:
            ImportError: If the `google-generativeai` library is not installed.
            # Note: google.genai.Client initialization doesn't typically raise
            # auth errors immediately, they usually occur on the first API call.

        """
        self.model = model
        self.output_dimensionality = output_dimensionality
        self.client = genai.Client(api_key=api_key)

    @override
    def embed_content(
        self,
        contents: str | list[str],
        title: str | None = None,
        task_type: str | None = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        """
        Generates embeddings for the provided content(s) using configured Gemini model.

        Args:
            contents: The text content to embed. Can be a single string or a
                      list of strings for batch processing.
            title: An optional title, useful for task_type='RETRIEVAL_DOCUMENT'.
            task_type: The task type hint (e.g., "RETRIEVAL_DOCUMENT",
                       "SEMANTIC_SIMILARITY"). Defaults to "RETRIEVAL_DOCUMENT".

        Returns:
            A list containing one or more embedding vectors (list of floats).

        Raises:
            EmbeddingsError: If the input is invalid, the API call fails (e.g., auth,
                             rate limits, server errors), or no embeddings are returned.
            ValueError: If the input contents list is empty.

        """
        if not contents:
            # Handle empty string or empty list input gracefully
            logger.warning("Embeddings requested for empty content.")
            return []  # Return empty list for empty input

        # Ensure contents is a list, even if single string
        contents_list = [contents] if isinstance(contents, str) else contents

        num_items = len(contents_list)
        logger.debug(
            "Requesting Gemini embeddings",
            model=self.model,
            num_items=num_items,
            task_type=task_type,
            has_title=bool(title),
            output_dimensionality=self.output_dimensionality,
        )

        response = self.client.models.embed_content(  # pyright: ignore[reportUnknownMemberType]
            model=self.model,
            contents=contents_list,  # type: ignore[reportArgumentType]
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality,
                task_type=task_type,
                title=title,
            ),
        )

        if hasattr(response, "embeddings") and response.embeddings:
            # Ignore return type check due to potential incomplete stubs
            embedding_values = [list(embedding) for embedding in response.embeddings]

            if len(embedding_values) != num_items:
                logger.warning(
                    "Mismatch between number of inputs and embeddings returned",
                    inputs=num_items,
                    outputs=len(embedding_values),
                )
                # Raising error for now to indicate inconsistency.
                msg = f"Expected {num_items} embeddings, but received "
                f"{len(embedding_values)}"
                raise EmbeddingsError(msg)

            logger.debug(
                "Successfully generated Gemini embeddings.",
                num_embeddings=len(embedding_values),
            )
            return embedding_values  # pyright: ignore[reportReturnType]
        # Handle cases where the API call succeeded but returned no embeddings
        logger.error(
            "Gemini API returned no embeddings.", response_details=str(response)
        )
        msg = "Gemini API call succeeded but returned no embeddings."
        raise EmbeddingsError(msg)
