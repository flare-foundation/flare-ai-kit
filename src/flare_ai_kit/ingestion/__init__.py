"""Module providing tools for data ingestion pipelines."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .github_ingestor import GithubIngestor
    from .pdf_processor import PDFProcessor

__all__ = ["GithubIngestor", "PDFProcessor"]


def __getattr__(name: str):
    """Lazy import for ingestion components."""
    if name == "GithubIngestor":
        from .github_ingestor import GithubIngestor

        return GithubIngestor
    if name == "PDFProcessor":
        from .pdf_processor import PDFProcessor

        return PDFProcessor
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
