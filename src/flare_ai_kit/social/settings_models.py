"""Settings for Social."""

from pydantic import BaseModel, Field, SecretStr


class SocialSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    x_api_key: SecretStr | None = Field(
        None,
        description="API key for X.",
    )
    x_api_key_secret: SecretStr | None = Field(
        None,
        description="API key secret for X.",
    )
    x_access_token: SecretStr | None = Field(
        None,
        description="Access token key for X.",
    )
    x_access_token_secret: SecretStr | None = Field(
        None,
        description="Access token secret for X.",
    )
    telegram_api_token: SecretStr | None = Field(
        None,
        description="API key for Telegram.",
    )
