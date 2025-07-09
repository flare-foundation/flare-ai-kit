from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Flare AI Kit API Wrapper")

# Example input model
class FtsoRequest(BaseModel):
    asset: str

# Example output model
class FtsoResponse(BaseModel):
    price: float
    asset: str

class SemanticSearchRequest(BaseModel):
    query: str

class SemanticSearchResponse(BaseModel):
    result: str  # Replace with actual data structure later

class ConsensusLearningRequest(BaseModel):
    data: list[str]

class ConsensusLearningResponse(BaseModel):
    consensus: str

class PostMessageRequest(BaseModel):
    platform: str  # "twitter" or "telegram"
    message: str


class OnChainTransactionRequest(BaseModel):
    to_address: str
    amount: float
    asset: str

class OnChainTransactionResponse(BaseModel):
    tx_hash: str



@app.get("/")
def health_check():
    return {"status": "running"}

@app.get("/ftso/price", response_model=FtsoResponse)
def get_ftso_price(asset: str):
    # Placeholder logic - replace with actual SDK call
    if asset.lower() == "flare":
        return FtsoResponse(price=0.042, asset="flare")
    raise HTTPException(status_code=404, detail="Asset not found")

@app.post("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search(req: SemanticSearchRequest):
    # Placeholder logic — replace with real retriever call
    if req.query:
        return SemanticSearchResponse(result=f"Search results for: {req.query}")
    raise HTTPException(status_code=400, detail="Query is empty")

@app.post("/consensus-learning", response_model=ConsensusLearningResponse)
def consensus_learning(req: ConsensusLearningRequest):
    # Placeholder logic
    if req.data:
        return ConsensusLearningResponse(consensus="Consensus reached")
    raise HTTPException(status_code=400, detail="No data provided")

@app.post("/post-message")
def post_message(req: PostMessageRequest):
    # Replace with actual integration logic
    if req.platform == "twitter":
        return {"status": "Posted to Twitter"}
    elif req.platform == "telegram":
        return {"status": "Posted to Telegram"}
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    

@app.post("/send-tx", response_model=OnChainTransactionResponse)
def send_tx(req: OnChainTransactionRequest):
    # Replace with SDK interaction
    return OnChainTransactionResponse(tx_hash="0x123abc")
