"""
Settings Configuration Module

This module defines the configuration settings for the AI Agent API
using Pydantic's BaseSettings. It handles environment variables and
provides default values for various service configurations.

The settings can be overridden by environment variables or through a .env file.
Environment variables take precedence over values defined in the .env file.
"""

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """
    Application settings model that provides configuration for all components.
    """

    # Flag to enable/disable attestation simulation
    simulate_attestation: bool = True
    # Restrict backend listener to specific IPs
    cors_origins: list[str] = ["*"]
    # API key for accessing Google's Gemini AI service
    gemini_api_key: str = ""
    # The Gemini model identifier to use
    gemini_model: str = "gemini-1.5-flash"
    # API version to use at the backend
    api_version: str = "v1"
    # URL for the Flare Network RPC provider
    web3_provider_url: str = (
        "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"
    )
    # URL for the Flare Network block explorer
    web3_explorer_url: str = "https://flare-explorer.flare.network/api"

    model_config = SettingsConfigDict(
        # This enables .env file support
        env_file=".env",
        # If .env file is not found, don't raise an error
        env_file_encoding="utf-8",
        # Optional: you can also specify multiple .env files
        extra="ignore",
    )


# Create a global settings instance
settings = Settings()
logger.debug("settings", settings=settings.model_dump())
