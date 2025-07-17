import os
from collections.abc import Iterator
from typing import Any

from .base import BaseChunker, BaseIndexer


class LocalFileIndexer(BaseIndexer):
    """Indexes local files from a directory, chunks their content, and yields chunked data with metadata."""

    def __init__(
        self,
        root_dir: str,
        chunker: BaseChunker,
        allowed_extensions: set[str] | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.chunker = chunker
        self.allowed_extensions = allowed_extensions or {".md", ".txt", ".py"}

    def ingest(self) -> Iterator[dict[str, Any]]:
        """
        Recursively scan the root directory for allowed files, read and chunk their content,
        and yield each chunk with metadata (file path, chunk index).
        """
        for dirpath, _, filenames in os.walk(self.root_dir):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in self.allowed_extensions:
                    continue
                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    # Optionally log or skip unreadable files
                    continue
                chunks = self.chunker.chunk(text)
                for idx, chunk in enumerate(chunks):
                    yield {
                        "text": chunk,
                        "metadata": {
                            "file_path": file_path,
                            "chunk_index": idx,
                            "total_chunks": len(chunks),
                            "file_name": filename,
                        },
                    }
