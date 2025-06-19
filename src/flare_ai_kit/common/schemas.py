"""Dataclass schemas used in Flare AI Kit."""

from dataclasses import dataclass
from enum import Enum
from typing import override


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
