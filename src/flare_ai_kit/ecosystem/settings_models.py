"""Settings for Ecosystem."""

from eth_typing import ChecksumAddress
from pydantic import BaseModel, Field, HttpUrl, PositiveInt, SecretStr


class EcosystemSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    is_testnet: bool = Field(
        False,  # noqa: FBT003
        description="Set True if interacting with testnets (Coston or Coston2).",
        examples=["env var: ECOSYSTEM__IS_TESTNET"],
    )
    web3_provider_url: HttpUrl = Field(
        HttpUrl(
            "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"
        ),
        description="Flare RPC endpoint URL.",
    )
    web3_provider_timeout: PositiveInt = Field(
        5,
        description="Timeout when interacting with web3 provider (in s).",
    )
    block_explorer_url: HttpUrl = Field(
        HttpUrl("https://flare-explorer.flare.network/api"),
        description="Flare Block Explorer URL.",
    )
    block_explorer_timeout: PositiveInt = Field(
        10,
        description="Flare Block Explorer query timeout (in seconds).",
    )
    max_retries: PositiveInt = Field(
        3,
        description="Max retries for Flare transactions.",
    )
    retry_delay: PositiveInt = Field(
        5,
        description="Delay between retries for Flare transactions (in seconds).",
    )
    account_address: ChecksumAddress | None = Field(
        None,
        description="Account address to use when interacting onchain.",
    )
    account_private_key: SecretStr | None = Field(
        None,
        description="Account private key to use when interacting onchain.",
    )
