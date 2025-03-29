"""Settings for Vector RAG."""

from pydantic import BaseModel, Field, HttpUrl, PostgresDsn, SecretStr


class VectorDbSettingsModel(BaseModel):
    """Configuration for Vector Database connections used in RAG."""

    qdrant_url: HttpUrl | None = Field(None, description="URL for the Qdrant instance.")
    qdrant_api_key: SecretStr | None = Field(
        None, description="API Key for Qdrant Cloud."
    )
    postgres_dsn: PostgresDsn | None = Field(
        None, description="DSN for PostgreSQL connection string."
    )
