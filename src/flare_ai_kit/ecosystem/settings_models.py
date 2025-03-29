"""Settings for Ecosystem."""

from pydantic import BaseModel, Field, HttpUrl


class EcosystemSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    flare_rpc_url: HttpUrl = Field(
        HttpUrl(
            "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"
        ),
        description="Flare RPC endpoint URL.",
    )
    block_explorer_url: HttpUrl = Field(
        HttpUrl("https://flare-explorer.flare.network"),
        description="Flare Block Explorer URL.",
    )
