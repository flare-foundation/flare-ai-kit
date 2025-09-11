"""Exposes the core components for the Vector RAG system."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .embedding import BaseEmbedding, GeminiEmbedding
    from .factory import VectorRAGPipeline, create_vector_rag_pipeline
    from .indexer import (
        BaseChunker,
        BaseIndexer,
        FixedSizeChunker,
        LocalFileIndexer,
        ingest_and_embed,
        upsert_to_qdrant,
    )
    from .responder import BaseResponder
    from .retriever import BaseRetriever, QdrantRetriever

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
    """Lazy import for vector RAG components."""
    if name == "BaseEmbedding":
        from .embedding import BaseEmbedding

        return BaseEmbedding
    if name == "GeminiEmbedding":
        from .embedding import GeminiEmbedding

        return GeminiEmbedding
    if name == "VectorRAGPipeline":
        from .factory import VectorRAGPipeline

        return VectorRAGPipeline
    if name == "create_vector_rag_pipeline":
        from .factory import create_vector_rag_pipeline

        return create_vector_rag_pipeline
    if name == "BaseChunker":
        from .indexer import BaseChunker

        return BaseChunker
    if name == "BaseIndexer":
        from .indexer import BaseIndexer

        return BaseIndexer
    if name == "FixedSizeChunker":
        from .indexer import FixedSizeChunker

        return FixedSizeChunker
    if name == "LocalFileIndexer":
        from .indexer import LocalFileIndexer

        return LocalFileIndexer
    if name == "ingest_and_embed":
        from .indexer import ingest_and_embed

        return ingest_and_embed
    if name == "upsert_to_qdrant":
        from .indexer import upsert_to_qdrant

        return upsert_to_qdrant
    if name == "BaseResponder":
        from .responder import BaseResponder

        return BaseResponder
    if name == "BaseRetriever":
        from .retriever import BaseRetriever

        return BaseRetriever
    if name == "QdrantRetriever":
        from .retriever import QdrantRetriever

        return QdrantRetriever
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
