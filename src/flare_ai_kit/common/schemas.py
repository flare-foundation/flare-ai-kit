"""Dataclass schemas used in Flare AI Kit."""

from dataclasses import dataclass
from typing import override


@dataclass
class ChunkMetadata:
    """Metadata associated with text chunk when embedding."""

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


@dataclass
class Chunk:
    """Text chunk to use when embedding."""

    text: str
    metadata: ChunkMetadata


@dataclass
class SemanticSearchResult:
    """Result when performing semantic search."""

    text: str
    score: float
    metadata: dict[str, str]
