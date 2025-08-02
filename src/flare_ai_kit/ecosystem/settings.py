"""Settings for Ecosystem."""

from typing import cast

from eth_typing import ChecksumAddress
from pydantic import BaseModel, Field, HttpUrl, PositiveInt, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContractAddresses(BaseModel):
    """A model for storing contract addresses for a single network."""

    sparkdex_universal_router: ChecksumAddress | None = None
    sparkdex_swap_router: ChecksumAddress | None = None
    kinetic_comptroller: ChecksumAddress | None = None
    kinetic_ksflr: ChecksumAddress | None = None
    stargate_FeeLibV1ETH: ChecksumAddress | None = None
    stargate_FeeLibV1USDC: ChecksumAddress | None = None
    stargate_FeeLibV1USDT: ChecksumAddress | None = None
    stargate_OFTTokenETH: ChecksumAddress | None = None
    stargate_StargateOFTETH: ChecksumAddress | None = None
    stargate_StargateOFTUSDC: ChecksumAddress | None = None
    stargate_StargateOFTUSDT: ChecksumAddress | None = None
    stargate_TokenMessaging: ChecksumAddress | None = None
    stargate_Treasurer: ChecksumAddress | None = None
    kinetic_kwETH: ChecksumAddress | None = None
    kinetic_ksFLR: ChecksumAddress | None = None
    kinetic_kUSDCe: ChecksumAddress | None = None
    kinetic_kUSDT: ChecksumAddress | None = None
    kinetic_kFLRETH: ChecksumAddress | None = None
    kinetic_Unitroller: ChecksumAddress | None = None
    cyclo_cysFLR: ChecksumAddress | None = None
    cyclo_cywETH: ChecksumAddress | None = None
    openocean_exchangeV2: ChecksumAddress | None = None
    weth: ChecksumAddress | None = None
    wflr: ChecksumAddress | None = None
    sflr: ChecksumAddress | None = None
    flreth: ChecksumAddress | None = None
    usdce: ChecksumAddress | None = None
    usdt: ChecksumAddress | None = None


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
        stargate_FeeLibV1ETH=cast(
            "ChecksumAddress", "0xCd4302D950e7e6606b6910Cd232758b5ad423311"
        ),
        stargate_FeeLibV1USDC=cast(
            "ChecksumAddress", "0x711b5aAFd4d0A5b7B863Ca434A2678D086830d8E"
        ),
        stargate_FeeLibV1USDT=cast(
            "ChecksumAddress", "0x8c1014B5936dD88BAA5F4DB0423C3003615E03a0"
        ),
        stargate_OFTTokenETH=cast(
            "ChecksumAddress", "0x1502FA4be69d526124D453619276FacCab275d3D"
        ),
        stargate_StargateOFTETH=cast(
            "ChecksumAddress", "0x8e8539e4CcD69123c623a106773F2b0cbbc58746"
        ),
        stargate_StargateOFTUSDC=cast(
            "ChecksumAddress", "0x77C71633C34C3784ede189d74223122422492a0f"
        ),
        stargate_StargateOFTUSDT=cast(
            "ChecksumAddress", "0x1C10CC06DC6D35970d1D53B2A23c76ef370d4135"
        ),
        stargate_TokenMessaging=cast(
            "ChecksumAddress", "0x45d417612e177672958dC0537C45a8f8d754Ac2E"
        ),
        stargate_Treasurer=cast(
            "ChecksumAddress", "0x090194F1EEDc134A680e3b488aBB2D212dba8c01"
        ),
        kinetic_kwETH=cast(
            "ChecksumAddress", "0x5C2400019017AE61F811D517D088Df732642DbD0"
        ),
        kinetic_ksFLR=cast(
            "ChecksumAddress", "0x291487beC339c2fE5D83DD45F0a15EFC9Ac45656"
        ),
        kinetic_kUSDCe=cast(
            "ChecksumAddress", "0xDEeBaBe05BDA7e8C1740873abF715f16164C29B8"
        ),
        kinetic_kUSDT=cast(
            "ChecksumAddress", "0x1e5bBC19E0B17D7d38F318C79401B3D16F2b93bb"
        ),
        kinetic_kFLRETH=cast(
            "ChecksumAddress", "0x40eE5dfe1D4a957cA8AC4DD4ADaf8A8fA76b1C16"
        ),
        kinetic_Unitroller=cast(
            "ChecksumAddress", "0x8041680Fb73E1Fe5F851e76233DCDfA0f2D2D7c8"
        ),
        cyclo_cysFLR=cast(
            "ChecksumAddress", "0x19831cfB53A0dbeAD9866C43557C1D48DfF76567"
        ),
        cyclo_cywETH=cast(
            "ChecksumAddress", "0xd8BF1d2720E9fFD01a2F9A2eFc3E101a05B852b4"
        ),
        openocean_exchangeV2=cast(
            "ChecksumAddress", "0x6352a56caadC4F1E25CD6c75970Fa768A3304e64"
        ),
        weth=cast("ChecksumAddress", "0x1502FA4be69d526124D453619276FacCab275d3D"),
        wflr=cast("ChecksumAddress", "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d"),
        sflr=cast("ChecksumAddress", "0x12e605bc104e93B45e1aD99F9e555f659051c2BB"),
        flreth=cast("ChecksumAddress", "0x26A1faB310bd080542DC864647d05985360B16A5"),
        usdce=cast("ChecksumAddress", "0xFbDa5F676cB37624f28265A144A48B0d6e87d3b6"),
        usdt=cast("ChecksumAddress", "0x0B38e83B86d491735fEaa0a791F65c2B99535396"),
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


class EcosystemSettingsModel(BaseSettings):
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
    openocean_token_list: str | None = Field(
        "https://open-api.openocean.finance/v4/flare/tokenList",
        description="OpenOcean token list URL",
    )
    openocean_gas_price: str | None = Field(
        "https://open-api.openocean.finance/v4/bsc/gasPrice",
        description="OpenOcean gas price URL",
    )
    openocean_swap: str | None = Field(
        "https://open-api.openocean.finance/v4/flare/swap",
        description="OpenOcean swap URL",
    )
    contracts: Contracts = Field(
        default_factory=Contracts,
        description="dApp contract addresses on each supported network.",
    )

    da_layer_base_url: HttpUrl = Field(
        HttpUrl("https://flr-data-availability.flare.network/api/v1/"),
        description="Flare Data Availability Layer API base URL.",
    )
    da_layer_api_key: SecretStr | None = Field(
        None,
        description="Optional API key for Flare Data Availability Layer.",
    )

    model_config = SettingsConfigDict(
        # This enables .env file support
        env_file=".env",
        # If .env file is not found, don't raise an error
        env_file_encoding="utf-8",
        # Optional: you can also specify multiple .env files
        extra="ignore",
    )


class ChainIds(BaseModel):
    """A model for storing chain IDs for supported networks."""

    flare: PositiveInt | None = None
    coston2: PositiveInt | None = None
    ethereum: PositiveInt | None = None
    bnb_chain: PositiveInt | None = None
    avalanche: PositiveInt | None = None
    polygon: PositiveInt | None = None
    arbitrum: PositiveInt | None = None
    op_mainnet: PositiveInt | None = None
    metis: PositiveInt | None = None
    linea: PositiveInt | None = None
    mantle: PositiveInt | None = None
    base: PositiveInt | None = None
    kava: PositiveInt | None = None
    scroll: PositiveInt | None = None
    aurora: PositiveInt | None = None
    core: PositiveInt | None = None
    sonic: PositiveInt | None = None
    unichain: PositiveInt | None = None
    gnosis: PositiveInt | None = None
    soneium: PositiveInt | None = None
    kaia: PositiveInt | None = None
    iota: PositiveInt | None = None
    taiko: PositiveInt | None = None
    rari_chain: PositiveInt | None = None
    sei: PositiveInt | None = None
    gravity: PositiveInt | None = None
    lightlink: PositiveInt | None = None
    abstract: PositiveInt | None = None
    flow: PositiveInt | None = None
    goat: PositiveInt | None = None
    berachain: PositiveInt | None = None
    rootstock: PositiveInt | None = None
    hemi: PositiveInt | None = None
    vana: PositiveInt | None = None
    ink: PositiveInt | None = None
    glue: PositiveInt | None = None
    fuse: PositiveInt | None = None
    superposition: PositiveInt | None = None
    degen: PositiveInt | None = None
    codex: PositiveInt | None = None
    story: PositiveInt | None = None
    apechain: PositiveInt | None = None
    telosevm: PositiveInt | None = None
    plume_phoenix: PositiveInt | None = None
    xdc: PositiveInt | None = None
    nibiru: PositiveInt | None = None


class ChainIdConfig(BaseModel):
    """A model for storing chain IDs for all supported networks."""

    chains: ChainIds = ChainIds(
        flare=30295,
        coston2=None,
        ethereum=30101,
        bnb_chain=30102,
        avalanche=30106,
        polygon=30109,
        arbitrum=30110,
        op_mainnet=30111,
        metis=30151,
        linea=30183,
        mantle=30181,
        base=30184,
        kava=30177,
        scroll=30214,
        aurora=30211,
        core=30153,
        sonic=30332,
        unichain=30320,
        gnosis=30145,
        soneium=30340,
        kaia=30150,
        iota=30284,
        taiko=30290,
        rari_chain=30235,
        sei=30280,
        gravity=30294,
        lightlink=30309,
        abstract=30324,
        flow=30336,
        goat=30361,
        berachain=30262,
        rootstock=30333,
        hemi=30329,
        vana=30330,
        ink=30339,
        glue=30342,
        fuse=30138,
        superposition=30327,
        degen=30267,
        codex=30323,
        story=30364,
        apechain=30312,
        telosevm=30199,
        plume_phoenix=30370,
        xdc=30365,
        nibiru=30369,
    )

    @model_validator(mode="after")
    def enforce_flare_chain_id(self) -> "ChainIdConfig":
        """Ensure that the Flare mainnet chain ID is set."""
        if self.chains.flare is None:
            raise ValueError("'flare' chain ID must be set for mainnet")
        return self

