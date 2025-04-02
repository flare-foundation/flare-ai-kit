"""Settings for Vector RAG."""

from pydantic import BaseModel, Field, HttpUrl, PostgresDsn, model_validator

DEFAULT_ALLOWED_EXTENSIONS = {
    ".py",
    ".ipynb",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".java",
    ".go",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".scala",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rs",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".tf",
    ".md",
    ".rst",
    ".txt",
    ".dockerfile",
    "Dockerfile",
    ".env.example",
}


DEFAULT_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "target",
    "build",
}

DEFAULT_IGNORED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "uv.lock",
}


class VectorDbSettingsModel(BaseModel):
    """Configuration for Vector Database connections used in RAG."""

    qdrant_url: HttpUrl | None = Field(
        None,
        description="Host and port for the Qdrant instance.",
        examples=["env var: VECTOR_DB__QDRANT_URL"],
    )
    qdrant_vector_size: int = Field(768, description="Dimension of vectors to use.")
    qdrant_batch_size: int = Field(
        100, description="Batch size for upserting points to Qdrant."
    )
    embeddings_model: str = Field(
        "gemini-embedding-exp-03-07",
        description="Embedding model name (e.g., 'gemini-embedding-exp-03-07').",
        examples=[
            "gemini-embedding-exp-03-07",
            "text-embedding-004",
        ],
    )
    embeddings_output_dimensionality: int | None = Field(
        None,
        description="Reduced dimension for the output embedding. Leave None for max.",
    )
    embeddings_chunk_size: int = Field(
        5000,
        description="Target size for text chunks before embedding (in characters).",
        gt=0,  # Ensure chunk size is positive
    )
    embeddings_chunk_overlap: int = Field(
        500,
        description="Overlap between consecutive text chunks (in characters).",
        ge=0,  # Ensure overlap is non-negative
    )
    indexer_allowed_extensions: set[str] = Field(
        DEFAULT_ALLOWED_EXTENSIONS,
        description="File extensions indexed by the indexer.",
    )
    indexer_ignored_dirs: set[str] = Field(
        DEFAULT_IGNORED_DIRS, description="Directories ignored by the indexer."
    )
    indexer_ignored_files: set[str] = Field(
        DEFAULT_IGNORED_FILES, description="Files ignored by the indexer."
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
