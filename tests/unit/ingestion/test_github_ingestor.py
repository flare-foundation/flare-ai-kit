from pathlib import Path
from typing import ClassVar

import pytest

from flare_ai_kit.common import Chunk, ChunkMetadata
from flare_ai_kit.ingestion.github_ingestor import GithubIngestor  # adjust if needed


class DummySettings:
    github_allowed_extensions: ClassVar[set[str]] = {".txt"}  # Only .txt is allowed
    github_ignored_dirs: ClassVar[set[str]] = set()
    github_ignored_files: ClassVar[set[str]] = set()
    chunk_size: int = 10
    chunk_overlap: int = 2


@pytest.fixture
def tmp_repo_dir(tmp_path: Path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("abcdefghijklmnopqrstuvwxyz")
    file2 = tmp_path / "file2.md"  # ignored
    file2.write_text("ignored")
    return tmp_path


def test_chunk_text_splits_correctly():
    s = DummySettings()
    ingestor = GithubIngestor(s)

    chunks = ingestor._chunk_text("file.txt", "abcdefghijklmnopqrstuvwxyz")
    assert isinstance(chunks[0], Chunk)
    assert all(isinstance(c.metadata, ChunkMetadata) for c in chunks)
    assert chunks[0].metadata.end_index - chunks[0].metadata.start_index == s.chunk_size
    assert chunks[1].metadata.start_index < chunks[0].metadata.end_index


def test_extract_text_filters_extensions(tmp_repo_dir: Path):
    s = DummySettings()
    ingestor = GithubIngestor(s)

    results = list(ingestor._extract_text_from_repo(tmp_repo_dir))
    assert len(results) == 1
    assert results[0]["file_path"].endswith("file1.txt")
    assert "abc" in results[0]["content"]


def test_ingest_yields_chunks(monkeypatch, tmp_repo_dir: Path):
    s = DummySettings()
    ingestor = GithubIngestor(s)

    monkeypatch.setattr(ingestor, "_clone_repo", lambda *_: tmp_repo_dir)
    monkeypatch.setattr(
        ingestor,
        "_extract_text_from_repo",
        lambda _: [{"file_path": "file1.txt", "content": "abcdefghij"}],
    )

    chunks = list(ingestor.ingest("owner/repo"))
    assert len(chunks) > 0
    assert isinstance(chunks[0], Chunk)
    assert chunks[0].metadata.original_filepath == "file1.txt"


def test_clone_repo_invalid_name(monkeypatch):
    s = DummySettings()
    ingestor = GithubIngestor(s)

    monkeypatch.setattr(
        "flare_ai_kit.ingestion.github_ingestor.porcelain.clone",
        lambda **_: None,
    )

    assert ingestor._clone_repo("invalidname") is None
