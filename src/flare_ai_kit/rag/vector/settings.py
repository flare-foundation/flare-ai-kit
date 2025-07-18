"""Settings for Vector RAG."""

from pydantic import Field, HttpUrl, PositiveInt, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class VectorDbSettings(BaseSettings):
    """Configuration for Vector Database connections used in RAG."""

    model_config = SettingsConfigDict(
        env_prefix="VECTORDB__",
        env_file=".env",
        extra="ignore",
    )
    qdrant_url: HttpUrl | None = Field(
        default=None,
        description="Host and port for the Qdrant instance.",
        examples=["env var: VECTOR_DB__QDRANT_URL"],
    )
    qdrant_vector_size: PositiveInt = Field(
        default=768, description="Dimension of vectors to use."
    )
    qdrant_batch_size: PositiveInt = Field(
        default=100, description="Batch size for upserting points to Qdrant."
    )
    embeddings_model: str = Field(
        default="gemini-embedding-exp-03-07",
        description="Embedding model name (e.g., 'gemini-embedding-exp-03-07').",
        examples=[
            "gemini-embedding-exp-03-07",
            "text-embedding-004",
        ],
    )
    embeddings_output_dimensionality: PositiveInt | None = Field(
        default=None,
        description="Reduced dimension for the output embedding. Leave None for max.",
    )

    postgres_dsn: PostgresDsn | None = Field(
        default=None, description="DSN for PostgreSQL connection string."
    )
