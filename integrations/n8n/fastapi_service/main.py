"""Main FastAPI service for Flare AI Kit integration with n8n."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Flare AI Kit API Wrapper")


# Example input model
class FtsoRequest(BaseModel):
    """Request model for FTSO price lookup."""

    asset: str


# Example output model
class FtsoResponse(BaseModel):
    """Response model for FTSO price lookup."""

    price: float
    asset: str


class SemanticSearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str


class SemanticSearchResponse(BaseModel):
    """Response model for semantic search."""

    result: str  # Replace with actual data structure later


class ConsensusLearningRequest(BaseModel):
    """Request model for consensus learning."""

    data: list[str]


class ConsensusLearningResponse(BaseModel):
    """Response model for consensus learning."""

    consensus: str


class PostMessageRequest(BaseModel):
    """Request model for posting messages to social media."""

    platform: str  # "twitter" or "telegram"
    message: str


class OnChainTransactionRequest(BaseModel):
    """Request model for on-chain transactions."""

    to_address: str
    amount: float
    asset: str


class OnChainTransactionResponse(BaseModel):
    """Response model for on-chain transactions."""

    tx_hash: str


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "running"}


@app.get("/ftso/price", response_model=FtsoResponse)
def get_ftso_price(asset: str) -> FtsoResponse:
    """Endpoint to get FTSO price for a given asset."""
    # Placeholder logic - replace with actual SDK call
    if asset.lower() == "flare":
        return FtsoResponse(price=0.042, asset="flare")
    raise HTTPException(status_code=404, detail="Asset not found")


@app.post("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search(req: SemanticSearchRequest) -> SemanticSearchResponse:
    """Endpoint for semantic search."""
    # Placeholder logic — replace with real retriever call
    if req.query:
        return SemanticSearchResponse(result=f"Search results for: {req.query}")
    raise HTTPException(status_code=400, detail="Query is empty")


@app.post("/consensus-learning", response_model=ConsensusLearningResponse)
def consensus_learning(req: ConsensusLearningRequest) -> ConsensusLearningResponse:
    """Endpoint for consensus learning."""
    # Placeholder logic
    if req.data:
        return ConsensusLearningResponse(consensus="Consensus reached")
    raise HTTPException(status_code=400, detail="No data provided")


@app.post("/post-message")
def post_message(req: PostMessageRequest):
    # Replace with actual integration logic
    if req.platform == "twitter":
        return {"status": "Posted to Twitter"}
    if req.platform == "telegram":
        return {"status": "Posted to Telegram"}
    raise HTTPException(status_code=400, detail="Unsupported platform")


@app.post("/send-tx", response_model=OnChainTransactionResponse)
def send_tx(req: OnChainTransactionRequest):  # noqa: ARG001
    # Replace with SDK interaction
    return OnChainTransactionResponse(tx_hash="0x123abc")
