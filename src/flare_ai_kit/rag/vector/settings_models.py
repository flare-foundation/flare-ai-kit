"""Settings for Vector RAG."""

from pydantic import BaseModel, Field, HttpUrl, PostgresDsn, SecretStr, model_validator


class VectorDbSettingsModel(BaseModel):
    """Configuration for Vector Database connections used in RAG."""

    qdrant_url: HttpUrl | None = Field(  # Use Optional[] for clarity
        None, description="Host and port for the Qdrant instance."
    )
    qdrant_vector_size: int = Field(768, description="Dimension of vectors to use.")
    qdrant_batch_size: int = Field(
        100, description="Batch size for upserting points to Qdrant."
    )
    embeddings_model: str = Field(
        # Example using a known Gemini model name convention
        "gemini-embedding-exp-03-07",
        description="Embedding model name (e.g., 'gemini-embedding-exp-03-07').",
    )
    embeddings_chunk_size: int = Field(
        1500,
        description="Target size for text chunks before embedding (in characters).",
        gt=0,  # Ensure chunk size is positive
    )
    embeddings_chunk_overlap: int = Field(
        150,
        description="Overlap between consecutive text chunks (in characters).",
        ge=0,  # Ensure overlap is non-negative
    )

    qdrant_api_key: SecretStr | None = Field(
        None, description="API Key for Qdrant Cloud."
    )
    postgres_dsn: PostgresDsn | None = Field(
        None, description="DSN for PostgreSQL connection string."
    )

    @model_validator(mode="after")
    def check_chunk_overlap_less_than_size(self) -> "VectorDbSettingsModel":
        """Validate that chunk overlap does not exceed chunk size."""
        chunk_size = self.embeddings_chunk_size
        chunk_overlap = self.embeddings_chunk_overlap

        if (
            chunk_overlap >= chunk_size
        ):  # Check if overlap is greater than OR EQUAL TO size
            msg = (
                f"embeddings_chunk_overlap ({chunk_overlap}) must be strictly "
                f"less than embeddings_chunk_size ({chunk_size})."
            )
            raise ValueError(msg)
        # Always return self for mode='after' validators
        return self
