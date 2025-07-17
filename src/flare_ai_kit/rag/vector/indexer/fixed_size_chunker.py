from .base import BaseChunker


class FixedSizeChunker(BaseChunker):
    """Splits text into chunks of a fixed number of words."""

    def __init__(self, chunk_size: int = 200, overlap: int = 0) -> None:
        """
        Args:
            chunk_size (int): Number of words per chunk.
            overlap (int): Number of words to overlap between chunks.

        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = words[i : i + self.chunk_size]
            chunks.append(" ".join(chunk))
            if self.overlap > 0:
                i += self.chunk_size - self.overlap
            else:
                i += self.chunk_size
        return chunks
