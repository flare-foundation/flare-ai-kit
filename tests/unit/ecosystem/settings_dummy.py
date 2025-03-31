"""Dummy settings for Ecosystem."""

from pydantic import BaseModel, HttpUrl


class EcosystemSettingsDummy(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    web3_provider_url: HttpUrl = HttpUrl("https://explorer.example.com/api")
    block_explorer_url: HttpUrl = HttpUrl("https://explorer.example.com/api")
    block_explorer_timeout: int = 10
