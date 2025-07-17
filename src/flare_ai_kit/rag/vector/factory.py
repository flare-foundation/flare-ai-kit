"""Factory functions for creating RAG (Retrieval-Augmented Generation) pipelines."""

from dataclasses import dataclass

import structlog
from qdrant_client import QdrantClient

from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.common import FlareAIKitError
from flare_ai_kit.rag.vector.embedding import GeminiEmbedding
from flare_ai_kit.rag.vector.retriever import QdrantRetriever
from flare_ai_kit.rag.vector.settings import VectorDbSettings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class VectorRAGPipeline:
    """
    A container for the components of a vector-based RAG pipeline.

    This object provides easy access to the configured indexer for populating
    the vector database and the retriever for searching it.

    Attributes:
        retriever: A retriever instance (e.g., QdrantRetriever) used to
                   embed chunks, store them, and perform semantic search.

    """

    retriever: QdrantRetriever


def create_vector_rag_pipeline(
    vector_db_settings: VectorDbSettings, agent_settings: AgentSettings
) -> VectorRAGPipeline:
    """
    Builds and configures a complete vector RAG pipeline.

    This factory function initializes and wires together all the necessary
    components for a vector-based RAG system, including the embedding model,
    the vector database client, the data indexer, and the retriever.

    Args:
        vector_db_settings: Configuration specific to the vector database and
                            data chunking/indexing process.
        agent_settings: Configuration for the AI agent, which includes the
                        necessary API keys for the embedding model.

    Returns:
        A `VectorRAGPipeline` object containing the fully configured indexer
        and retriever.

    Raises:
        FlareAIKitError: If essential configuration like the Qdrant URL or
                         the Gemini API key is missing.

    """
    logger.info("Creating vector RAG pipeline...")

    if not vector_db_settings.qdrant_url:
        msg = "Qdrant URL is not configured. Please set VECTOR_DB__QDRANT_URL."
        logger.error(msg)
        raise FlareAIKitError(msg)

    if not agent_settings.gemini_api_key:
        msg = "Gemini API key is not configured. Please set AGENT__GEMINI_API_KEY."
        logger.error(msg)
        raise FlareAIKitError(msg)

    # Initialize Components
    try:
        # 1. Embedding Client
        embedding_client = GeminiEmbedding(
            api_key=agent_settings.gemini_api_key.get_secret_value(),
            model=vector_db_settings.embeddings_model,
            output_dimensionality=vector_db_settings.embeddings_output_dimensionality,
        )
        logger.debug("GeminiEmbedding client initialized.")

        # 2. Vector DB Client
        qdrant_client = QdrantClient(url=str(vector_db_settings.qdrant_url))
        logger.debug("QdrantClient initialized.", url=vector_db_settings.qdrant_url)

        # 3. Retriever (handles embedding and searching)
        retriever = QdrantRetriever(
            qdrant_client=qdrant_client,
            embedding_client=embedding_client,
            settings=vector_db_settings,
        )
        logger.debug("QdrantRetriever initialized.")

    except Exception as e:
        logger.exception("Failed to initialize a component for the RAG pipeline.")
        msg = "Could not create vector RAG pipeline."
        raise FlareAIKitError(msg) from e

    pipeline = VectorRAGPipeline(retriever=retriever)
    logger.info("Vector RAG pipeline created successfully.")

    return pipeline
