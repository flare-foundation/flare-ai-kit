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


class PDFFieldExtractionSettings(BaseSettings):
    """Specifies fields to extract from a PDF and their locations."""

    field_name: str = Field(description="The name of the field to extract.")
    data_type: str = Field(
        "string",
        description="The data type of the field (e.g., 'string', 'integer', 'date').",
    )
    # For deterministic extraction pipeline
    x0: int | None = Field(
        default=None, description="The starting x-coordinate of the bounding box."
    )
    y0: int | None = Field(
        default=None, description="The starting y-coordinate of the bounding box."
    )
    x1: int | None = Field(
        default=None, description="The ending x-coordinate of the bounding box."
    )
    y1: int | None = Field(
        default=None, description="The ending y-coordinate of the bounding box."
    )


class PDFTemplateSettings(BaseSettings):
    """Defines a template for a specific type of PDF document."""

    template_name: str = Field(description="A unique name for this PDF template.")
    fields: list[PDFFieldExtractionSettings] = Field(
        description="A list of fields to extract from this template."
    )


class OnchainContractSettings(BaseSettings):
    """Settings for the smart contract to post data to."""

    contract_address: str = Field(
        description="The address of the OnchainDataRegistry smart contract."
    )
    abi_name: str = Field(
        description="ABI file name for the smart contract (under flare-ai-kit/abi/)."
    )
    function_name: str = Field(
        "registerDocument",
        description="The name of the function to call on the smart contract.",
    )


class PDFIngestionSettings(BaseSettings):
    """Settings for the PDF ingestion and on-chain posting service."""

    templates: list[PDFTemplateSettings] = Field(
        description="A list of PDF templates to use for extraction."
    )
    contract_settings: OnchainContractSettings = Field(
        description="Settings for the on-chain contract."
    )
    use_ocr: bool = Field(False, description="Whether to use OCR for text extraction.")


class IngestionSettings(BaseSettings):
    """Configuration for Vector Database connections used in RAG."""

    model_config = SettingsConfigDict(
        env_prefix="INGESTION__",
        env_file=".env",
        extra="ignore",
    )
    chunk_size: PositiveInt = Field(
        default=5000,
        description="Target size for text chunks before embedding (in characters).",
        gt=0,  # Ensure chunk size is positive
    )
    chunk_overlap: PositiveInt = Field(
        default=500,
        description="Overlap between consecutive text chunks (in characters).",
        ge=0,  # Ensure overlap is non-negative
    )
    github_allowed_extensions: set[str] = Field(
        default=DEFAULT_ALLOWED_EXTENSIONS,
        description="File extensions indexed by the indexer.",
    )
    github_ignored_dirs: set[str] = Field(
        default=DEFAULT_IGNORED_DIRS, description="Directories ignored by the indexer."
    )
    github_ignored_files: set[str] = Field(
        default=DEFAULT_IGNORED_FILES, description="Files ignored by the indexer."
    )
    pdf_ingestion: PDFIngestionSettings | None = Field(
        default=None, description="Settings for PDF ingestion."
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
