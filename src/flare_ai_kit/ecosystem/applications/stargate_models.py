# flare_ai_kit/ecosystem/applications/stargate_models.py
from pydantic import BaseModel


class StargateQuoteFee(BaseModel):
    token: str
    chainKey: str
    amount: str
    type: str


class StargateQuoteDuration(BaseModel):
    estimated: float


class StargateQuoteTransaction(BaseModel):
    data: str
    to: str
    value: str
    from_: str  # renamed because `from` is a reserved keyword

    class Config:
        fields = {"from_": "from"}


class StargateQuoteStep(BaseModel):
    type: str
    sender: str
    chainKey: str
    transaction: StargateQuoteTransaction


class StargateQuote(BaseModel):
    route: str
    error: str | None
    srcAmount: str
    dstAmount: str
    srcAmountMax: str
    dstAmountMin: str
    srcToken: str
    dstToken: str
    srcAddress: str
    dstAddress: str
    srcChainKey: str
    dstChainKey: str
    dstNativeAmount: str
    duration: StargateQuoteDuration
    fees: list[StargateQuoteFee]
    steps: list[StargateQuoteStep]


class StargateQuoteResponse(BaseModel):
    quotes: list[StargateQuote]
