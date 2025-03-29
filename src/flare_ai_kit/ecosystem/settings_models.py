"""Settings for Ecosystem."""

from pydantic import BaseModel, Field, HttpUrl


class EcosystemSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    flare_rpc_url: HttpUrl = Field(
        ...,
        description="Flare RPC endpoint URL.",
    )
    block_explorer_url: HttpUrl = Field(
        ...,
        description="Flare Block Explorer URL.",
    )
