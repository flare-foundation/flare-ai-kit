"""Indexer for processing and indexing content from GitHub repos into Qdrant."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

import structlog
from git import GitCommandError, Repo

from flare_ai_kit.common import Chunk, ChunkMetadata
from flare_ai_kit.rag.vector.retriever import QdrantRetriever
from flare_ai_kit.rag.vector.settings_models import VectorDbSettingsModel

logger = structlog.get_logger(__name__)


class GitHubIndexer:
    """
    Indexes content from GitHub repositories into a Qdrant vector collection.

    This class orchestrates the process of cloning a repository, extracting
    relevant text content based on configuration (file extensions, ignored paths),
    chunking the text, and using an injected QdrantRetriever instance to
    generate embeddings and upsert the data into a specified Qdrant collection.
    """

    def __init__(
        self,
        qdrant_retriever: QdrantRetriever,
        settings: VectorDbSettingsModel,
    ) -> None:
        """
        Initializes the GitHubIndexer.

        Args:
            qdrant_retriever: An initialized QdrantRetriever instance responsible
                              for embedding and Qdrant communication.
            settings: A VectorDbSettingsModel instance containing configuration
                      for indexing (allowed extensions, ignored items,
                      chunking parameters).

        """
        self.qdrant_retriever = qdrant_retriever
        self.allowed_extensions = settings.indexer_allowed_extensions
        self.ignored_dirs = settings.indexer_ignored_dirs
        self.ignored_files = settings.indexer_ignored_files
        self.chunk_size = settings.embeddings_chunk_size
        self.chunk_overlap = settings.embeddings_chunk_overlap

        logger.info(
            "GitHubRAGIndexer initialized",
            allowed_extensions=len(self.allowed_extensions),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def _clone_repo(
        self, repo_url_or_name: str, branch: str | None = None
    ) -> Path | None:
        """
        Clones a public GitHub repository to a temporary directory.

        Handles repository URL parsing and uses GitPython for cloning. Cleans up
        the temporary directory automatically if cloning fails.

        Args:
            repo_url_or_name: The repository URL (e.g., "https://github.com/owner/repo")
                              or short name format (e.g., "owner/repo").
            branch: The specific branch to clone. If None, clones the repository's
                    default branch.

        Returns:
            A Path object pointing to the temporary directory containing the
            cloned repository, or None if cloning failed.

        """
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
            # Ensure it ends with .git for cloning
            parsed = urlparse(repo_url_or_name)
            repo_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if not repo_url.endswith(".git"):
                repo_url += ".git"

        temp_dir: str | None = None
        temp_dir_path: Path | None = None
        try:
            # Create a temp directory using tempfile context manager for safer cleanup
            temp_dir = tempfile.mkdtemp()
            temp_dir_path = Path(temp_dir)

            logger.info(
                "Attempting to clone repository",
                repo_url=repo_url,
                branch=branch or "default",
                dest_dir=str(temp_dir_path),
            )

            Repo.clone_from(url=repo_url, to_path=temp_dir_path, branch=branch)

            logger.info(
                "Successfully cloned repository",
                repo_url=repo_url,
                dest_dir=str(temp_dir_path),
            )

        except GitCommandError as e:
            logger.exception(
                "Git command failed during clone. Check URL/name, branch, network, "
                "permissions, and local Git installation.",
                repo_url=repo_url,
                branch=branch,
                error=str(e),
                # Safely access stderr if it exists
                stderr=getattr(e, "stderr", "N/A").strip(),
            )
            # Fall through to finally for cleanup
        except Exception as e:
            # Catch other potential errors (network, permissions, etc.)
            logger.exception(
                "An unexpected error occurred during cloning.",
                repo_url=repo_url,
                error=str(e),
            )
            # Fall through to finally for cleanup
        else:
            return temp_dir_path  # Return the path if successful
        finally:
            # Cleanup only if cloning failed within this function
            if temp_dir_path and not temp_dir_path.exists() and temp_dir_path.is_dir():
                try:
                    shutil.rmtree(temp_dir_path)
                    logger.debug(
                        "Cleaned up failed clone directory", path=str(temp_dir_path)
                    )
                except Exception as cleanup_error:
                    logger.exception(
                        "Failed to cleanup temporary clone directory on error",
                        path=str(temp_dir_path),
                        error=str(cleanup_error),
                    )
        return None  # Explicitly return None on any failure

    def _extract_text_from_repo(
        self, repo_path: Path
    ) -> Generator[dict[str, str], None, None]:
        """
        Walks through a cloned repository, extracts text from allowed files.

        Filters files based on configured allowed extensions/filenames and
        ignored directories/filenames. Reads files as UTF-8, ignoring decoding errors.

        Args:
            repo_path: The Path object pointing to the root of the cloned repository.

        Yields:
            Dictionaries for each valid file found, containing:
                'file_path': Relative path to the file within the repo (as string).
                'content': The text content of the file.

        """
        logger.info("Starting text extraction", repo_path=str(repo_path))
        processed_files = 0
        skipped_files = 0

        # Use Path.glob recursively
        for file_path in repo_path.glob("**/*"):
            # Skip directories and only process files
            if not file_path.is_file():
                continue

            # Skip files in ignored directories
            if any(parent.name in self.ignored_dirs for parent in file_path.parents):
                continue

            # Get relative path
            try:
                rel_path = file_path.relative_to(repo_path).as_posix()
            except ValueError:
                logger.warning(
                    "Could not determine relative path, skipping.", file=str(file_path)
                )
                skipped_files += 1
                continue

            # Skip files based on name or extension
            filename = file_path.name
            file_suffix = file_path.suffix.lower()

            if filename in self.ignored_files or (
                file_suffix not in self.allowed_extensions
                and filename not in self.allowed_extensions
            ):
                skipped_files += 1
                continue

            # Read file content
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                if content.strip():
                    yield {"file_path": rel_path, "content": content}
                    processed_files += 1
                else:
                    skipped_files += 1
            except Exception:
                logger.exception("Could not read file. Skipping.", file=rel_path)
                skipped_files += 1

        logger.info(
            "Text extraction finished",
            processed_files=processed_files,
            skipped_files=skipped_files,
        )

    def _chunk_text(self, file_path: str, content: str) -> list[Chunk]:
        """
        Splits a string of text content into smaller, overlapping chunks.

        Uses the `chunk_size` and `chunk_overlap` configured during initialization.
        Generates `Chunk` objects containing the text and `ChunkMetadata`.

        Args:
            file_path: The relative path of the file being chunked (used in metadata).
            content: The text content of the file to be chunked.

        Returns:
            A list of Chunk objects, each representing a text chunk with metadata.
            Returns an empty list if the input content is empty or whitespace only.

        """
        if not content or not content.strip():
            return []

        chunks: list[Chunk] = []
        start_index = 0
        chunk_id = 0
        content_len = len(content)

        while start_index < content_len:
            end_index = start_index + self.chunk_size
            chunk_text = content[start_index:end_index]

            # Create metadata and chunk object
            metadata = ChunkMetadata(
                original_filepath=file_path,
                chunk_id=chunk_id,
                start_index=start_index,
                end_index=min(end_index, len(content)),
            )
            chunk = Chunk(text=chunk_text, metadata=metadata)
            chunks.append(chunk)
            chunk_id += 1

            # Calculate start index for the next chunk based on overlap
            next_start = start_index + self.chunk_size - self.chunk_overlap

            # Prevent infinite loops: ensure progression if overlap is too large
            # or content is very short compared to chunk size.
            if next_start <= start_index:
                next_start = (
                    start_index + 1
                )  # Force progression by at least 1 character

            # Break if the next start is already past the content end
            if next_start >= content_len:
                break

            start_index = next_start

        return chunks

    def _prepare_data_for_qdrant(self, repo_path: Path) -> list[Chunk] | None:
        """
        Extracts text from repository files and chunks them into a list of Chunk.

        This method combines the output of `_extract_text_from_repo` and `_chunk_text`.

        Args:
            repo_path: The Path object pointing to the root of the cloned repository.

        Returns:
            A list of Chunk objects ready for embedding and indexing, or None if
            no processable text content was found in the repository.

        """
        all_chunks: list[Chunk] = []
        file_count = 0
        for file_data in self._extract_text_from_repo(repo_path):
            file_path = file_data["file_path"]
            content = file_data["content"]
            try:
                file_chunks = self._chunk_text(file_path, content)
                all_chunks.extend(file_chunks)
                file_count += 1
            except Exception as e:
                logger.exception(
                    "Error chunking file, skipping file.", file=file_path, error=str(e)
                )

        if not all_chunks:
            logger.warning(
                "No processable text content found or chunked in the repository.",
                repo_path=str(repo_path),
                processed_files=file_count,
            )
            return None

        logger.info(
            "Data preparation complete.",
            repo_path=str(repo_path),
            processed_files=file_count,
            total_chunks=len(all_chunks),
        )
        return all_chunks

    def index_repo_to_qdrant(
        self,
        collection_name: str,
        repo_url_or_name: str,
        branch: str | None = None,
        cleanup: bool = True,
    ) -> bool:
        """
        Indexes a GitHub repository into the specified Qdrant collection.

        This is the main entry point method. It orchestrates the cloning,
        data preparation (extraction, chunking), and indexing pipeline.
        Embeddings are generated and data is upserted via the configured
        `QdrantRetriever`.

        Args:
            collection_name: The name of the Qdrant collection to index into.
            repo_url_or_name: The repository URL (e.g., "https://github.com/owner/repo")
                              or short name format (e.g., "owner/repo").
            branch: The specific branch to clone. Defaults to the repo's default branch.
            cleanup: If True (default), the temporary directory holding the cloned
                     repository will be deleted after indexing attempt
                     (success or failure). Set to False for debugging purposes.

        Returns:
            True if the indexing process was successfully initiated and completed
            without critical errors during cloning or data preparation phases.
            False if cloning failed, no processable content was found, or an
            unhandled exception occurred during the pipeline initiation.
            Note: Successful return does not guarantee all documents were indexed
            if non-critical errors occurred during upsertion (check logs).

        """
        repo_path = None
        try:
            # 1. Clone Repo
            logger.info(
                "Starting indexing pipeline",
                repo=repo_url_or_name,
                branch=branch or "default",
            )
            repo_path = self._clone_repo(repo_url_or_name, branch)
            if not repo_path:
                return False  # Cloning failed, logged in _clone_repo

            # 2. Prepare Data (Extract, Chunk, Format)
            logger.info("Repository cloned, preparing data...", repo=repo_url_or_name)
            chunk_data = self._prepare_data_for_qdrant(repo_path)
            if not chunk_data:
                logger.warning(
                    "Pipeline finished: No data suitable for indexing found.",
                    repo=repo_url_or_name,
                )
                return False

            # 3. Index Data using QdrantRetriever
            logger.info(
                "Data prepared, initiating embedding and indexing via QdrantRetriever.",
                repo=repo_url_or_name,
                num_chunks=len(chunk_data),
                collection_name=collection_name,
            )
            self.qdrant_retriever.embed_and_upsert(
                data=chunk_data,
                collection_name=collection_name,
            )
            logger.info(
                "Indexing pipeline successfully submitted data to QdrantRetriever.",
                repo=repo_url_or_name,
            )
        except Exception:
            logger.exception(
                "An error occurred during the indexing pipeline",
                repo=repo_url_or_name,
                collection_name=collection_name,
            )
            return False
        else:
            return True
        finally:
            # 4. Cleanup
            if repo_path and cleanup and repo_path.exists():
                try:
                    shutil.rmtree(repo_path)
                    logger.info(
                        "Cleaned up temporary repository directory", path=repo_path
                    )
                except Exception as e:
                    logger.exception(
                        "Failed to cleanup temporary directory",
                        path=repo_path,
                        error=str(e),
                    )
