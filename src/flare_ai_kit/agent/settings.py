"""Settings for Agent."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Configuration specific to the Flare ecosystem interactions."""

    model_config = SettingsConfigDict(
        env_prefix="AGENT__",
        env_file=".env",
        extra="ignore",
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="API key for using Google Gemini (https://aistudio.google.com/app/apikey).",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use (e.g. gemini-2.5-flash, gemini-2.5-pro)",
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="API key for OpenRouter.",
    )
