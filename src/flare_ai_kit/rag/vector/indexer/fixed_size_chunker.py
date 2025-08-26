"""Fixed-size chunker implementation for text splitting."""

from .base import BaseChunker


class FixedSizeChunker(BaseChunker):
    """Splits text into chunks of a fixed number of words."""

    def __init__(self, chunk_size: int = 200, overlap: int = 0) -> None:
        """
        Initialize the FixedSizeChunker.

        Args:
            chunk_size (int): Number of words per chunk.
            overlap (int): Number of words to overlap between chunks.

        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        """
        Split input text into a list of fixed-size word chunks.

        Args:
            text (str): The raw text to split.

        Returns:
            list[str]: List of text chunks.

        """
        words: list[str] = text.split()
        chunks: list[str] = []
        i = 0
        while i < len(words):
            chunk = words[i : i + self.chunk_size]
            chunks.append(" ".join(chunk))
            if self.overlap > 0:
                i += self.chunk_size - self.overlap
            else:
                i += self.chunk_size
        return chunks
