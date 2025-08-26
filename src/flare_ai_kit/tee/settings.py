"""Settings for TEE."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TeeSettings(BaseSettings):
    """Configuration specific to the Flare ecosystem interactions."""

    model_config = SettingsConfigDict(
        env_prefix="TEE__",
        env_file=".env",
        extra="ignore",
    )
    simulate_attestation_token: bool = Field(
        True,
        description="Use a pregenerated attestation token for testing.",
    )
