"""Settings for A2A."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class A2ASettings(BaseSettings):
    """Configuration specific to the Flare ecosystem interactions."""

    model_config = SettingsConfigDict(
        env_prefix="A2A__",
        env_file=".env",
        extra="ignore",
    )
    sqlite_db_path: Path = Field(
        default=Path.cwd() / "flare_a2a.db",
        description="Use a pregenerated attestation token for testing.",
    )
    client_timeout: float = Field(
        default=30.0,
        description="Timeout for HTTP requests to A2A servers.",
    )
