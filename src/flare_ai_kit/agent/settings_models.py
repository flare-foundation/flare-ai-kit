"""Settings for Agent."""

from pydantic import BaseModel, Field, SecretStr


class AgentSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    # For local/test runs, uncomment the next line to set a default:
    # gemini_api_key: SecretStr = Field(SecretStr("dummy"), description="API key for using Google Gemini (https://aistudio.google.com/app/apikey).",)
    # For production, require the API key to be set via environment variable or .env file:
    gemini_api_key: SecretStr = Field(
        ...,
        description="API key for using Google Gemini (https://aistudio.google.com/app/apikey).",
    )
    gemini_model: str = Field(
        "gemini-2.5-flash",
        description="Gemini model to use (e.g. gemini-2.5-flash, gemini-2.5-pro)",
    )
    openrouter_api_key: SecretStr | None = Field(
        None,
        description="API key for OpenRouter.",
    )
