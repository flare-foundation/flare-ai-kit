"""Dataclass schemas used in Flare AI Kit."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, override

from pydantic import BaseModel, Field


# --- Schemas for Text Chunking and Embeddings ---
@dataclass(frozen=True)
class ChunkMetadata:
    """
    Immutable metadata associated with a text chunk during embedding.

    Attributes:
        original_filepath: Path to the source file of the chunk.
        chunk_id: Unique identifier for the chunk within its source file.
        start_index: Starting character index of the chunk in the original text.
        end_index: Ending character index of the chunk in the original text.

    """

    original_filepath: str
    chunk_id: int
    start_index: int
    end_index: int

    @override
    def __str__(self) -> str:
        return (
            f"original_filepath={self.original_filepath}, "
            f"self.chunk_id={self.chunk_id}, "
            f"start_index={self.start_index}, "
            f"end_index={self.end_index}"
        )


@dataclass(frozen=True)
class Chunk:
    """
    Immutable representation of a text chunk and its associated metadata.

    Attributes:
        text: The actual text content of the chunk.
        metadata: The ChunkMetadata object associated with this chunk.

    """

    text: str
    metadata: ChunkMetadata


# --- Schemas for Search Results ---
@dataclass(frozen=True)
class SemanticSearchResult:
    """
    Immutable result obtained from a semantic search query.

    Attributes:
        text: The text content of the search result chunk.
        score: The similarity score (e.g., cosine similarity) of the result
               relative to the query. Higher usually means more relevant.
        metadata: A dictionary containing arbitrary metadata associated with
                  the search result, often derived from the original ChunkMetadata
                  (e.g., {'original_filepath': '...', 'chunk_id': 1, ...}).

    """

    text: str
    score: float
    metadata: dict[str, str]


# --- FTSO ---
class FtsoFeedCategory(str, Enum):
    """Enum for FTSO Feed Categories. See https://dev.flare.network/ftso/feeds."""

    CRYPTO = "01"
    FOREX = "02"
    COMMODITY = "03"
    STOCK = "04"
    CUSTOMFEED = "05"


@dataclass(frozen=True)
class Prediction:
    """Prediction from an agent."""

    agent_id: str
    prediction: float | str
    confidence: float = 1.0


# --- FAssets ---
class FAssetType(str, Enum):
    """Enum for supported FAsset types."""

    FXRP = "FXRP"
    FBTC = "FBTC"
    FDOGE = "FDOGE"


class FAssetStatus(str, Enum):
    """Enum for FAsset status states."""

    NORMAL = "NORMAL"
    CCB = "CCB"  # Collateral Call Band
    LIQUIDATION = "LIQUIDATION"
    FULL_LIQUIDATION = "FULL_LIQUIDATION"


class CollateralType(str, Enum):
    """Enum for collateral types in FAssets."""

    VAULT_COLLATERAL = "VAULT_COLLATERAL"  # FLR/SGB
    POOL_COLLATERAL = "POOL_COLLATERAL"  # Stablecoins
    UNDERLYING = "UNDERLYING"  # BTC/XRP/DOGE


@dataclass(frozen=True)
class FAssetInfo:
    """Information about a specific FAsset."""

    symbol: str
    name: str
    asset_manager_address: str
    f_asset_address: str
    underlying_symbol: str
    decimals: int
    is_active: bool


@dataclass(frozen=True)
class AgentInfo:
    """Information about an FAssets agent."""

    agent_address: str
    name: str
    description: str
    icon_url: str
    info_url: str
    vault_collateral_token: str
    fee_share: int
    mint_count: int
    remaining_wnat: int
    free_underlying_balance_usd: int
    all_lots: int
    available_lots: int


@dataclass(frozen=True)
class CollateralInfo:
    """Information about collateral in FAssets."""

    collateral_type: CollateralType
    token_address: str
    amount: int
    usd_value: float
    ratio: float


@dataclass(frozen=True)
class MintingRequest:
    """Request details for FAssets minting."""

    asset_type: FAssetType
    lots: int
    max_minting_fee_bips: int
    max_executor_fee_nat: int
    executor_address: str
    recipient_address: str


@dataclass(frozen=True)
class RedemptionRequest:
    """Request details for FAssets redemption."""

    asset_type: FAssetType
    lots: int
    max_redemption_fee_bips: int
    max_executor_fee_nat: int
    executor_address: str
    recipient_underlying_address: str


# --- Agents ---

AgentRole = Literal["user", "system", "assistant", "summarizer", "critic", "filter"]

# --- DA Layer ---
# This uses Pydantic for stricter validation.


class AttestationRequest(BaseModel):
    """Represents an attestation request structure."""

    attestation_type: str
    source_id: str
    message_integrity_code: str
    request_body: dict[str, Any]


class AttestationResponse(BaseModel):
    """Represents an attestation response structure."""

    attestation_type: str
    source_id: str
    voting_round: int
    lowest_used_timestamp: int
    request_body: dict[str, Any]
    response_body: dict[str, Any]


class MerkleProof(BaseModel):
    """Represents a Merkle proof for attestation verification."""

    merkle_proof: list[str]
    leaf_index: int
    total_leaves: int


class AttestationData(BaseModel):
    """Complete attestation data including response and proof."""

    response: AttestationResponse
    proof: MerkleProof


class VotingRound(BaseModel):
    """Voting round id and timestamp."""

    voting_round_id: int
    start_timestamp: int


class VotingRoundData(BaseModel):
    """Data for a specific voting round."""

    voting_round: int
    merkle_root: str
    timestamp: int
    total_attestations: int
    finalized: bool


class FTSOAnchorFeed(BaseModel):
    """FTSO anchor feed data structure."""

    feed_id: str
    feed_name: str


class FTSOAnchorFeedBody(BaseModel):
    """FTSO anchor feed values."""

    voting_round_id: int = Field(alias="votingRoundId")
    feed_id: str = Field(alias="id")
    value: int
    turnout_bips: int = Field(alias="turnoutBIPS")
    decimals: int


class FTSOAnchorFeedsWithProof(BaseModel):
    """FTSO anchor feeds with proof for a specific voting round."""

    body: FTSOAnchorFeedBody
    proof: list[str]
