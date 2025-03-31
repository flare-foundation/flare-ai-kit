"""Indexer for GitHub repositories."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

import structlog
from git import GitCommandError, Repo  # GitPython

from flare_ai_kit.common import Chunk, ChunkMetadata
from flare_ai_kit.rag.vector.retriever import QdrantRetriever
from flare_ai_kit.rag.vector.settings_models import VectorDbSettingsModel

logger = structlog.get_logger(__name__)


class GitHubIndexer:
    """
    Indexes content from GitHub repositories into a Qdrant collection for RAG.

    Handles cloning, text extraction, chunking, embedding, and indexing.
    """

    def __init__(
        self,
        qdrant_retriever: QdrantRetriever,
        settings: VectorDbSettingsModel,
    ) -> None:
        """
        Initialize the GitHubRAGIndexer.

        :param qdrant_retriever: An initialized QdrantRetriever instance.
        :param allowed_extensions: Set of file extensions to process.
        :param ignored_dirs: Set of directory names to ignore.
        :param ignored_files: Set of file names to ignore.
        :param chunk_size: Target size for text chunks (in characters).
        :param chunk_overlap: Overlap between consecutive chunks (in characters).
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
        Clones a public GitHub repository to a temporary directory using pathlib.

        :param repo_url_or_name: Repository URL (e.g., https://github.com/owner/repo)
                                    or name (e.g., owner/repo).
        :param branch: Specific branch to clone (defaults to the repo's default branch).
        :return: Path object to the temporary directory where the repo was cloned,
            or None on failure.
        """
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

        # Create a Path object for the temporary directory
        temp_dir_path = Path(tempfile.mkdtemp())
        logger.info(
            "Attempting to clone repository",
            repo_url=repo_url,
            branch=branch or "default",
            dest_dir=str(temp_dir_path),  # Log path as string for clarity if needed
        )

        try:
            # Pass the Path object directly to clone_from
            Repo.clone_from(url=repo_url, to_path=temp_dir_path, branch=branch)
            logger.info(
                "Successfully cloned repository",
                repo_url=repo_url,
                dest_dir=str(temp_dir_path),
            )
        except GitCommandError as e:
            logger.exception(
                "Failed to clone repository. Check URL/name, permissions, "
                "and if git is installed.",
                repo_url=repo_url,
                branch=branch,
                error=str(e),
                stderr=e.stderr.strip() if hasattr(e, "stderr") else "N/A",
            )
            # shutil.rmtree works with Path objects
            shutil.rmtree(temp_dir_path)  # Clean up failed clone attempt
            return None
        except Exception as e:
            logger.exception(
                "An unexpected error occurred during cloning.",
                repo_url=repo_url,
                error=str(e),
            )
            # shutil.rmtree works with Path objects
            shutil.rmtree(temp_dir_path)
            return None
        else:
            # Return the Path object
            return temp_dir_path

    def _extract_text_from_repo(
        self, repo_path: Path
    ) -> Generator[dict[str, str], None, None]:
        """
        Extracts content from files in a repository.

        Filtering by file extensions and names.
        Uses pathlib for all file system operations.

        :param repo_path: Path object for the cloned repository.
        :yield: Dictionaries containing 'file_path' (as string) and 'content'.
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
        Splits content into smaller chunks with overlap.

        :param file_path: The relative path of the file being chunked.
        :param content: The text content of the file.
        :return: A list of dictionaries, each representing a chunk with metadata.
        """
        chunks: list[Chunk] = []
        start_index = 0
        chunk_id = 0

        if not content:
            return []

        while start_index < len(content):
            end_index = start_index + self.chunk_size
            chunk_text = content[start_index:end_index]

            # Only add non-empty chunks
            if chunk_text.strip():
                metadata = ChunkMetadata(
                    original_filepath=file_path,
                    chunk_id=chunk_id,
                    start_index=start_index,
                    end_index=min(end_index, len(content)),
                )
                chunk = Chunk(text=chunk_text, metadata=metadata)
                chunks.append(chunk)
                chunk_id += 1

            # Move start index for the next chunk, considering overlap
            next_start = start_index + self.chunk_size - self.chunk_overlap
            # If overlap is large or chunk size small, prevent infinite loop
            if next_start <= start_index:
                next_start = start_index + 1  # Move at least one character

            start_index = next_start

            # Break if we somehow aren't advancing
            if start_index >= len(content):
                break

        return chunks

    def _prepare_data_for_qdrant(self, repo_path: Path) -> list[Chunk] | None:
        """
        Extracts, chunks, and formats data into a DataFrame for Qdrant indexing.

        :param repo_path: Path to the cloned repository.
        :return: Pandas DataFrame ready for qdrant_retriever.index_dataframe,
            or None if no data.
        """
        all_chunks_data: list[Chunk] = []
        for file_data in self._extract_text_from_repo(repo_path):
            file_path = file_data["file_path"]
            content = file_data["content"]
            file_chunks = self._chunk_text(file_path, content)
            all_chunks_data.extend(file_chunks)

        if not all_chunks_data:
            logger.warning(
                "No processable text content found in the repository.",
                repo_path=repo_path,
            )
            return None

        return all_chunks_data

    def index_repo_to_qdrant(
        self,
        collection_name: str,
        repo_url_or_name: str,
        branch: str | None = None,
        cleanup: bool = True,
    ) -> bool:
        """
        Main method to index a GitHub repository.

        Clones the repo, extracts text, chunks it, generates embeddings
        (via QdrantRetriever), and indexes into the configured Qdrant collection.

        :param repo_url_or_name: Repository URL (e.g., https://github.com/owner/repo)
                                 or name (e.g., owner/repo).
        :param branch: Specific branch to clone.
        :param cleanup: If True, delete the cloned repository directory after indexing.
        :param qdrant_batch_size: Batch size for upserting points to Qdrant.
        :return: True if indexing process started successfully
                (doesn't guarantee all docs indexed),
                 False otherwise (e.g., clone failed, no content found).
        """
        repo_path = None
        try:
            # 1. Clone Repo
            repo_path = self._clone_repo(repo_url_or_name, branch)
            if not repo_path:
                return False  # Cloning failed, logged in _clone_repo

            # 2. Prepare Data (Extract, Chunk, Format)
            data = self._prepare_data_for_qdrant(repo_path)
            if not data:
                logger.warning("No data prepared for indexing.", repo=repo_url_or_name)
                return False

            # 3. Index Data using QdrantRetriever
            # The QdrantRetriever's index_dataframe handles embedding generation
            # and upserting to Qdrant, including collection creation/recreation.
            logger.info(
                "Starting Qdrant indexing",
                repo=repo_url_or_name,
                num_chunks=len(data),
            )
            self.qdrant_retriever.embed_and_upsert(
                data=data,
                collection_name=collection_name,
            )
            # index_dataframe logs its own completion/errors

            logger.info(
                "Successfully initiated indexing for repository", repo=repo_url_or_name
            )
        except Exception as e:
            logger.exception(
                "An error occurred during the indexing pipeline",
                repo=repo_url_or_name,
                error=str(e),
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
