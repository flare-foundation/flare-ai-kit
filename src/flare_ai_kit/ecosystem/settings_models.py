"""Settings for Ecosystem."""

from pydantic import BaseModel, Field, HttpUrl


class EcosystemSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    web3_provider_url: HttpUrl = Field(
        HttpUrl(
            "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"
        ),
        description="Flare RPC endpoint URL.",
    )
    block_explorer_url: HttpUrl = Field(
        HttpUrl("https://flare-explorer.flare.network/api"),
        description="Flare Block Explorer URL.",
    )
    block_explorer_timeout: int = Field(
        10,
        description="Flare Block Explorer query timeout (in seconds).",
    )
