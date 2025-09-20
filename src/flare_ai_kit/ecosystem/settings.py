"""Settings for Ecosystem."""

from typing import cast

from eth_typing import ChecksumAddress
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    PositiveInt,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContractAddresses(BaseModel):
    """A model for storing contract addresses for a single network."""

    sparkdex_universal_router: ChecksumAddress | None = None
    sparkdex_swap_router: ChecksumAddress | None = None
    kinetic_comptroller: ChecksumAddress | None = None
    kinetic_ksflr: ChecksumAddress | None = None


class Contracts(BaseModel):
    """A model for storing contract addresses for all supported networks."""

    # Tell pyright that Pydantic will cast these as ChecksumAddress during runtime
    flare: ContractAddresses = ContractAddresses(
        sparkdex_universal_router=cast(
            "ChecksumAddress", "0x0f3D8a38D4c74afBebc2c42695642f0e3acb15D3"
        ),
        sparkdex_swap_router=cast(
            "ChecksumAddress", "0x8a1E35F5c98C4E85B36B7B253222eE17773b2781"
        ),
        kinetic_comptroller=cast(
            "ChecksumAddress", "0xeC7e541375D70c37262f619162502dB9131d6db5"
        ),
        kinetic_ksflr=cast(
            "ChecksumAddress", "0x291487beC339c2fE5D83DD45F0a15EFC9Ac45656"
        ),
    )
    coston2: ContractAddresses = ContractAddresses()

    @model_validator(mode="after")
    def enforce_flare_addresses(self) -> "Contracts":
        """Ensure that all contract addresses are set for Flare mainnet."""
        # Iterate over the fields defined in the ContractAddresses model
        for field_name in ContractAddresses.model_fields:
            if getattr(self.flare, field_name) is None:
                msg = f"'{field_name}' must be set for mainnet contracts"
                raise ValueError(msg)
        return self


class EcosystemSettings(BaseSettings):
    """Configuration specific to the Flare ecosystem interactions."""

    model_config = SettingsConfigDict(
        env_prefix="ECOSYSTEM__",
        env_file=".env",
        extra="ignore",
    )
    is_testnet: bool = Field(
        default=False,
        description="Set True if interacting with Flare Testnet Coston2.",
        examples=["env var: ECOSYSTEM__IS_TESTNET"],
    )
    web3_provider_url: HttpUrl = Field(
        default=HttpUrl(
            "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"
        ),
        description="Flare RPC endpoint URL.",
    )
    web3_provider_timeout: PositiveInt = Field(
        default=5,
        description="Timeout when interacting with web3 provider (in s).",
    )
    block_explorer_url: HttpUrl = Field(
        default=HttpUrl("https://flare-explorer.flare.network/api"),
        description="Flare Block Explorer URL.",
    )
    block_explorer_timeout: PositiveInt = Field(
        default=10,
        description="Flare Block Explorer query timeout (in seconds).",
    )
    max_retries: PositiveInt = Field(
        default=3,
        description="Max retries for Flare transactions.",
    )
    retry_delay: PositiveInt = Field(
        default=5,
        description="Delay between retries for Flare transactions (in seconds).",
    )
    account_address: ChecksumAddress | None = Field(
        default=None,
        description="Account address to use when interacting onchain.",
    )
    account_private_key: SecretStr | None = Field(
        default=None,
        description="Account private key to use when interacting onchain.",
    )
    contracts: Contracts = Field(
        default_factory=Contracts,
        description="dApp contract addresses on each supported network.",
    )
    da_layer_base_url: HttpUrl = Field(
        default=HttpUrl("https://flr-data-availability.flare.network/api/"),
        description="Flare Data Availability Layer API base URL.",
    )
    da_layer_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for Flare Data Availability Layer.",
    )
