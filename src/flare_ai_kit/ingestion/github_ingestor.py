"""Indexer for processing and yielding content from GitHub repos as Chunks."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

import structlog
from dulwich import porcelain

from flare_ai_kit.common import Chunk, ChunkMetadata
from flare_ai_kit.ingestion.settings import IngestionSettings

logger = structlog.get_logger(__name__)


class GithubIngestor:
    """
    Ingests content from a public GitHub repository.

    This class implements the BaseIngestor interface. It clones a repository,
    extracts text from allowed files, splits the text into chunks, and yields
    each chunk for further processing.
    """

    def __init__(self, settings: IngestionSettings) -> None:
        """
        Initializes the GitHubIndexer.

        Args:
            settings: A VectorDbSettings instance containing configuration
                      for file filtering (allowed extensions, ignored paths) and
                      chunking parameters.

        """
        self.allowed_extensions = settings.github_allowed_extensions
        self.ignored_dirs = settings.github_ignored_dirs
        self.ignored_files = settings.github_ignored_files
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

        logger.info(
            "GitHubIndexer initialized",
            allowed_extensions=len(self.allowed_extensions),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def ingest(
        self,
        repo_url_or_name: str,
        branch: str | None = None,
        cleanup: bool = True,
    ) -> Generator[Chunk, None, None]:
        """
        Clones a GitHub repository, processes its files, and yields text chunks.

        This is the main entry point method for the ingestor. It orchestrates
        the cloning, data preparation, and chunking pipeline, yielding each
        `Chunk` as it's generated.

        Args:
            repo_url_or_name: The repository URL or short name (e.g., "owner/repo").
            branch: The specific branch to clone. Defaults to the repo's default.
            cleanup: If True, the temporary directory will be deleted after completion.

        Yields:
            A generator of `Chunk` objects from the repository's content.

        """
        repo_path: Path | None = None
        try:
            logger.info(
                "Starting ingestion pipeline",
                repo=repo_url_or_name,
                branch=branch or "default",
            )
            repo_path = self._clone_repo(repo_url_or_name, branch)
            if not repo_path:
                # Error logged in _clone_repo, just stop the generator
                return

            # Process files and yield chunks directly
            file_count = 0
            chunk_count = 0
            for file_data in self._extract_text_from_repo(repo_path):
                file_path = file_data["file_path"]
                content = file_data["content"]
                file_count += 1
                try:
                    for chunk in self._chunk_text(file_path, content):
                        yield chunk
                        chunk_count += 1
                except Exception as e:
                    logger.exception(
                        "Error chunking file, skipping.", file=file_path, error=str(e)
                    )
            logger.info(
                "Ingestion pipeline complete.",
                processed_files=file_count,
                total_chunks=chunk_count,
            )

        finally:
            # Cleanup the temporary directory
            if repo_path and cleanup and repo_path.exists():
                try:
                    shutil.rmtree(repo_path)
                    logger.info(
                        "Cleaned up temporary repository directory", path=str(repo_path)
                    )
                except Exception as e:
                    logger.exception(
                        "Failed to cleanup temporary directory",
                        path=str(repo_path),
                        error=str(e),
                    )

    def _clone_repo(
        self, repo_url_or_name: str, branch: str | None = None
    ) -> Path | None:
        """Clones a public GitHub repository to a temporary directory."""
        repo_url: str
        if "github.com" not in repo_url_or_name:
            if "/" not in repo_url_or_name:
                logger.error(
                    "Invalid repository name format. Use 'owner/repo'.",
                    repo=repo_url_or_name,
                )
                return None
            repo_url = f"https://github.com/{repo_url_or_name}.git"
        else:
            parsed = urlparse(repo_url_or_name)
            repo_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if not repo_url.endswith(".git"):
                repo_url += ".git"

        temp_dir_path = Path(tempfile.mkdtemp())

        try:
            logger.info("Cloning with Dulwich", url=repo_url, branch=branch)
            porcelain.clone(  # type: ignore[reportUnknownMemberType]
                source=repo_url.encode(),
                target=temp_dir_path,
                checkout=True,
                depth=1,
                branch=(branch or b"refs/heads/main"),
            )
        except Exception as e:
            logger.exception("Dulwich clone failed", error=str(e))
            shutil.rmtree(temp_dir_path)
            return None
        else:
            logger.info("Repository cloned successfully", path=str(temp_dir_path))
            return temp_dir_path

    def _extract_text_from_repo(
        self, repo_path: Path
    ) -> Generator[dict[str, str], None, None]:
        """Walks through a repo, yielding text from allowed files."""
        logger.info("Starting text extraction", repo_path=str(repo_path))
        processed_files = 0
        for file_path in repo_path.glob("**/*"):
            if not file_path.is_file():
                continue
            if any(parent.name in self.ignored_dirs for parent in file_path.parents):
                continue

            rel_path = file_path.relative_to(repo_path).as_posix()
            filename = file_path.name
            file_suffix = file_path.suffix.lower()

            if filename in self.ignored_files or (
                file_suffix not in self.allowed_extensions
                and filename not in self.allowed_extensions
            ):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if content.strip():
                    yield {"file_path": rel_path, "content": content}
                    processed_files += 1
            except Exception:
                logger.exception("Could not read file, skipping.", file=rel_path)

        logger.info("Text extraction finished.", processed_files=processed_files)

    def _chunk_text(self, file_path: str, content: str) -> list[Chunk]:
        """Splits text content into smaller, overlapping chunks."""
        if not content or not content.strip():
            return []

        chunks: list[Chunk] = []
        start_index = 0
        chunk_id = 0
        content_len = len(content)

        while start_index < content_len:
            end_index = start_index + self.chunk_size
            chunk_text = content[start_index:end_index]

            metadata = ChunkMetadata(
                original_filepath=file_path,
                chunk_id=chunk_id,
                start_index=start_index,
                end_index=min(end_index, len(content)),
            )
            chunk = Chunk(text=chunk_text, metadata=metadata)
            chunks.append(chunk)
            chunk_id += 1

            next_start = start_index + self.chunk_size - self.chunk_overlap
            if next_start <= start_index:
                next_start = start_index + 1
            start_index = next_start

        return chunks
