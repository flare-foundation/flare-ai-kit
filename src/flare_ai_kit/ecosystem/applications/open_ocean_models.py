from pydantic import BaseModel, Field


class OpenOceanQuoteRequest(BaseModel):
    chain: str = Field(
        default="flare", description="Target chain (e.g., 'flare', 'bsc')"
    )
    in_token_address: str
    out_token_address: str
    amount_decimals: str = Field(
        ..., description="Amount with decimals (e.g., 5000000000000000000)"
    )
    gas_price_decimals: str | None = None
    slippage: str = Field(
        default="1", description="Slippage as percentage string (e.g., '1')"
    )
    enabled_dex_ids: str | None = None
    disabled_dex_ids: str | None = None
    account: str | None = None


class TokenInfo(BaseModel):
    address: str
    decimals: int
    symbol: str
    name: str
    usd: str | None = None
    volume: float | None = None


class DexInfo(BaseModel):
    id: str
    name: str
    url: str | None = None
    logo: str | None = None
    liquidity: str | None = None


class SwapQuoteResponse(BaseModel):
    in_token: TokenInfo = Field(alias="inToken")
    out_token: TokenInfo = Field(alias="outToken")
    in_amount: str
    out_amount: str
    min_out_amount: str
    estimated_gas: str
    gas_price: str | None = None
    gas_token_price: str | None = None
    slippage: str | None = None
    path: list[str] | None = None
    dex_ids: list[str] | None = Field(default=None, alias="dexIds")


class TokenListResponse(BaseModel):
    tokens: list[TokenInfo]


class DexListResponse(BaseModel):
    dexes: list[DexInfo]


class TransactionInfo(BaseModel):
    hash: str
    from_address: str = Field(alias="from")
    to_address: str = Field(alias="to")
    value: str
    gas_price: str
    gas_used: str | None = None
    status: int | None = None
    block_number: str | None = None
    timestamp: str | None = None


class TransactionResponse(BaseModel):
    data: TransactionInfo
