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
    sceptre_sflr: ChecksumAddress | None = None
    cyclo_cysflr_vault: ChecksumAddress | None = None
    cyclo_cysflr_receipt: ChecksumAddress | None = None
    firelight_stxrp_vault: ChecksumAddress | None = None
    stargate_token_messaging: ChecksumAddress | None = None
    stargate_treasurer: ChecksumAddress | None = None
    stargate_eth_oft: ChecksumAddress | None = None
    stargate_usdc_oft: ChecksumAddress | None = None
    stargate_usdt_oft: ChecksumAddress | None = None


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
        sceptre_sflr=cast(
            "ChecksumAddress", "0x12e605bc104e93B45e1aD99F9e555f659051c2BB"
        ),
        cyclo_cysflr_vault=cast(
            "ChecksumAddress", "0x19831cfB53A0dbeAD9866C43557C1D48DfF76567"
        ),
        cyclo_cysflr_receipt=cast(
            "ChecksumAddress", "0xd387FC43E19a63036d8FCeD559E81f5dDeF7ef09"
        ),
        firelight_stxrp_vault=cast(
            "ChecksumAddress", "0x4C18Ff3C89632c3Dd62E796c0aFA5c07c4c1B2b3"
        ),
        stargate_token_messaging=cast(
            "ChecksumAddress", "0x45d417612e177672958dC0537C45a8f8d754Ac2E"
        ),
        stargate_treasurer=cast(
            "ChecksumAddress", "0x090194F1EEDc134A680e3b488aBB2D212dba8c01"
        ),
        stargate_eth_oft=cast(
            "ChecksumAddress", "0x8e8539e4CcD69123c623a106773F2b0cbbc58746"
        ),
        stargate_usdc_oft=cast(
            "ChecksumAddress", "0x77C71633C34C3784ede189d74223122422492a0f"
        ),
        stargate_usdt_oft=cast(
            "ChecksumAddress", "0x1C10CC06DC6D35970d1D53B2A23c76ef370d4135"
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
