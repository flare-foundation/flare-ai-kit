"""Module providing tools for vector and graph based RAG."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vector import (
        BaseChunker,
        BaseEmbedding,
        BaseIndexer,
        BaseResponder,
        BaseRetriever,
        FixedSizeChunker,
        GeminiEmbedding,
        LocalFileIndexer,
        QdrantRetriever,
        VectorRAGPipeline,
        create_vector_rag_pipeline,
        ingest_and_embed,
        upsert_to_qdrant,
    )

__all__ = [
    "BaseChunker",
    "BaseEmbedding",
    "BaseIndexer",
    "BaseResponder",
    "BaseRetriever",
    "FixedSizeChunker",
    "GeminiEmbedding",
    "LocalFileIndexer",
    "QdrantRetriever",
    "VectorRAGPipeline",
    "create_vector_rag_pipeline",
    "ingest_and_embed",
    "upsert_to_qdrant",
]


def __getattr__(name: str):
    """Lazy import for RAG components."""
    if name == "BaseChunker":
        from .vector import BaseChunker

        return BaseChunker
    if name == "BaseEmbedding":
        from .vector import BaseEmbedding

        return BaseEmbedding
    if name == "BaseIndexer":
        from .vector import BaseIndexer

        return BaseIndexer
    if name == "BaseResponder":
        from .vector import BaseResponder

        return BaseResponder
    if name == "BaseRetriever":
        from .vector import BaseRetriever

        return BaseRetriever
    if name == "FixedSizeChunker":
        from .vector import FixedSizeChunker

        return FixedSizeChunker
    if name == "GeminiEmbedding":
        from .vector import GeminiEmbedding

        return GeminiEmbedding
    if name == "LocalFileIndexer":
        from .vector import LocalFileIndexer

        return LocalFileIndexer
    if name == "QdrantRetriever":
        from .vector import QdrantRetriever

        return QdrantRetriever
    if name == "VectorRAGPipeline":
        from .vector import VectorRAGPipeline

        return VectorRAGPipeline
    if name == "create_vector_rag_pipeline":
        from .vector import create_vector_rag_pipeline

        return create_vector_rag_pipeline
    if name == "ingest_and_embed":
        from .vector import ingest_and_embed

        return ingest_and_embed
    if name == "upsert_to_qdrant":
        from .vector import upsert_to_qdrant

        return upsert_to_qdrant
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
