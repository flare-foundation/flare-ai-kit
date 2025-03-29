"""Settings for TEE."""

from pydantic import BaseModel, Field, SecretStr


class TeeSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    simulate_attestation: bool = Field(
        ...,
        description="API key for using Google Gemini.",
    )
    openrouter_api_key: SecretStr | None = Field(
        None,
        description="API key for OpenRouter.",
    )
