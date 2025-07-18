"""Settings for Social."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SocialSettings(BaseSettings):
    """Configuration specific to the Flare ecosystem interactions."""

    model_config = SettingsConfigDict(
        env_prefix="SOCIAL__",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )
    x_api_key: SecretStr | None = Field(
        default=None,
        description="API key for X.",
    )
    x_api_key_secret: SecretStr | None = Field(
        default=None,
        description="API key secret for X.",
    )
    x_access_token: SecretStr | None = Field(
        default=None,
        description="Access token key for X.",
    )
    x_access_token_secret: SecretStr | None = Field(
        default=None,
        description="Access token secret for X.",
    )
    telegram_api_token: SecretStr | None = Field(
        default=None,
        description="API key for Telegram.",
    )
