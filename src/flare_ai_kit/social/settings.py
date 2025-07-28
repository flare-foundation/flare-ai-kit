"""Settings for Social."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class SocialSettings(BaseSettings):
    """Configuration specific to the Flare ecosystem interactions."""

    # x(twitter) settings
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
    # telegram settings
    telegram_api_token: SecretStr | None = Field(
        default=None,
        description="API key for Telegram.",
    )
    telegram_bot_token: SecretStr | None = Field(
        None,
        description="API key for Telegram.",
    )
    telegram_chat_id: SecretStr | None = Field(
        None,
        description="API key for Telegram.",
    )

    # Discord settings
    discord_bot_token: SecretStr | None = Field(
        None,
        description="Bot token for Discord.",
    )
    discord_channel_id: SecretStr | None = Field(
        None,
        description="Channel ID for Discord.",
    )

    # Slack settings
    slack_bot_token: SecretStr | None = Field(
        None,
        description="Bot token for Slack.",
    )
    slack_channel_id: SecretStr | None = Field(
        None,
        description="Channel name for Slack.",
    )

    # Farcaster settings
    farcaster_api_key: SecretStr | None = Field(
        None,
        description="API key for Farcaster.",
    )
    farcaster_signer_uuid: SecretStr | None = Field(
        None,
        description="Signer UUID for Farcaster.",
    )
    farcaster_fid: SecretStr | None = Field(
        None,
        description="Farcaster FID.",
    )
    farcaster_api_url: SecretStr | None = Field(
        None,
        description="Base URL for Farcaster API.",
    )

    # Github settings
    github_token: SecretStr | None = Field(
        None,
        description="Token for github.",
    )
    github_repo: SecretStr | None = Field(
        None,
        description="Repository for github.",
    )
