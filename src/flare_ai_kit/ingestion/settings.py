"""Settings for Vector RAG."""

from pydantic import Field, PositiveInt, model_validator
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


class IngestionSettings(BaseSettings):
    """Configuration for Vector Database connections used in RAG."""

    model_config = SettingsConfigDict(
        env_prefix="INGESTION__",
        env_file=".env",
        extra="ignore",
    )
    chunk_size: PositiveInt = Field(
        5000,
        description="Target size for text chunks before embedding (in characters).",
        gt=0,  # Ensure chunk size is positive
    )
    chunk_overlap: PositiveInt = Field(
        500,
        description="Overlap between consecutive text chunks (in characters).",
        ge=0,  # Ensure overlap is non-negative
    )
    github_allowed_extensions: set[str] = Field(
        DEFAULT_ALLOWED_EXTENSIONS,
        description="File extensions indexed by the indexer.",
    )
    github_ignored_dirs: set[str] = Field(
        DEFAULT_IGNORED_DIRS, description="Directories ignored by the indexer."
    )
    github_ignored_files: set[str] = Field(
        DEFAULT_IGNORED_FILES, description="Files ignored by the indexer."
    )

    @model_validator(mode="after")
    def check_chunk_overlap_less_than_size(self) -> "IngestionSettings":
        """Validate that chunk overlap does not exceed chunk size."""
        if (
            self.chunk_overlap >= self.chunk_size
        ):  # Check if overlap is greater than OR EQUAL TO size
            msg = (
                f"embeddings_chunk_overlap ({self.chunk_overlap}) must be strictly "
                f"less than embeddings_chunk_size ({self.chunk_size})."
            )
            raise ValueError(msg)
        # Always return self for mode='after' validators
        return self
