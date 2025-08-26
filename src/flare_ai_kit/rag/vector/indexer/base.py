"""Base classes for vector indexers and chunkers."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class BaseIndexer(ABC):
    """
    Abstract base class for data ingestion modules.

    Responsible for processing raw data from a source and yielding cleaned,
    chunked text with metadata.
    """

    @abstractmethod
    def ingest(self) -> Iterator[dict[str, Any]]:
        """

        Process the data source and yield dictionaries containing.

        - 'text': The chunked text content
        - 'metadata': Associated metadata (e.g., source, title, url)


        Yields:
            dict[str, Any]: A dictionary with 'text' and 'metadata' keys.

        """


class BaseChunker(ABC):
    """
    Abstract base class for text chunking strategies.

    Splits raw text into smaller, meaningful chunks for embedding.
    """

    @abstractmethod
    def chunk(self, text: str) -> list[str]:
        """
        Split input text into a list of chunks.

        Args:
            text (str): The raw text to split.

        Returns:
            list[str]: List of text chunks.

        """
