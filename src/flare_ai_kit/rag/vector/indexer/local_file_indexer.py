"""Local file indexer for chunking and metadata extraction."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import structlog

from .base import BaseChunker, BaseIndexer

logger = structlog.get_logger(__name__)


class LocalFileIndexer(BaseIndexer):
    """Indexes local files, chunks and extracts metadata."""

    def __init__(
        self,
        root_dir: str,
        chunker: BaseChunker,
        allowed_extensions: set[str] | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.chunker = chunker
        self.allowed_extensions = allowed_extensions or {".md", ".txt", ".py"}

    def ingest(self) -> Iterator[dict[str, Any]]:
        """Scan directory for files with allowed extensions."""
        for file_path in self.root_dir.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in self.allowed_extensions:
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except Exception:
                logger.exception("Failed to read file", file_path=str(file_path))
                continue
            chunks = self.chunker.chunk(text)
            for idx, chunk in enumerate(chunks):
                yield {
                    "text": chunk,
                    "metadata": {
                        "file_path": str(file_path),
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "file_name": file_path.name,
                    },
                }
