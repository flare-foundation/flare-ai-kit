"""Factory functions for creating RAG (Retrieval-Augmented Generation) pipelines."""

from dataclasses import dataclass, field

import structlog
from qdrant_client import QdrantClient

from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.common import FlareAIKitError, SemanticSearchResult
from flare_ai_kit.rag.vector.embedding import GeminiEmbedding
from flare_ai_kit.rag.vector.reranker import BaseReranker, GeminiPointwiseReranker
from flare_ai_kit.rag.vector.retriever import QdrantRetriever
from flare_ai_kit.rag.vector.settings import RerankerSettings, VectorDbSettings

logger = structlog.get_logger(__name__)


@dataclass
class VectorRAGPipeline:
    """
    A container for the components of a vector-based RAG pipeline.

    This object provides easy access to the configured indexer for populating
    the vector database and the retriever for searching it.

    Attributes:
        retriever: A retriever instance (e.g., QdrantRetriever) used to
                   embed chunks, store them, and perform semantic search.
        reranker: Optional reranker instance for improving retrieval quality.

    """

    retriever: QdrantRetriever
    reranker: BaseReranker | None = field(default=None)

    async def retrieve_and_rerank(
        self,
        query: str,
        collection_name: str,
        top_k_retrieve: int = 20,
        top_k_rerank: int = 5,
        score_threshold: float | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Retrieve candidates and optionally rerank them.

        This is the main entry point for RAG retrieval with reranking.
        First retrieves top_k_retrieve candidates, then reranks them
        (if reranker is configured) and returns top_k_rerank results.

        Args:
            query: The search query string.
            collection_name: Name of the Qdrant collection to search.
            top_k_retrieve: Number of candidates to retrieve initially.
            top_k_rerank: Number of results to return after reranking.
            score_threshold: Optional minimum similarity score for retrieval.

        Returns:
            List of SemanticSearchResult, reranked if reranker is configured.

        """
        # Initial retrieval
        candidates = self.retriever.semantic_search(
            query=query,
            collection_name=collection_name,
            top_k=top_k_retrieve,
            score_threshold=score_threshold,
        )

        if not candidates:
            return []

        # Rerank if configured
        if self.reranker:
            return await self.reranker.rerank(query, candidates, top_k=top_k_rerank)

        # No reranker - just return top_k results
        return candidates[:top_k_rerank]


def create_vector_rag_pipeline(
    vector_db_settings: VectorDbSettings,
    agent_settings: AgentSettings,
    reranker_settings: RerankerSettings | None = None,
) -> VectorRAGPipeline:
    """
    Builds and configures a complete vector RAG pipeline.

    This factory function initializes and wires together all the necessary
    components for a vector-based RAG system, including the embedding model,
    the vector database client, the data indexer, the retriever, and optionally
    a reranker for improved retrieval quality.

    Args:
        vector_db_settings: Configuration specific to the vector database and
                            data chunking/indexing process.
        agent_settings: Configuration for the AI agent, which includes the
                        necessary API keys for the embedding model.
        reranker_settings: Optional configuration for LLM-based reranking.
                          If None or disabled, no reranker is initialized.

    Returns:
        A `VectorRAGPipeline` object containing the fully configured indexer,
        retriever, and optionally a reranker.

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

        # 4. Optional Reranker
        reranker: BaseReranker | None = None
        if reranker_settings and reranker_settings.enabled:
            reranker = GeminiPointwiseReranker(
                api_key=agent_settings.gemini_api_key.get_secret_value(),
                model=reranker_settings.model,
                num_batches=reranker_settings.num_batches,
                timeout_seconds=reranker_settings.timeout_seconds,
                score_threshold=reranker_settings.score_threshold,
                few_shot_examples=reranker_settings.few_shot_examples,
            )
            logger.debug(
                "GeminiPointwiseReranker initialized.",
                model=reranker_settings.model,
                num_batches=reranker_settings.num_batches,
            )

    except Exception as e:
        logger.exception("Failed to initialize a component for the RAG pipeline.")
        msg = "Could not create vector RAG pipeline."
        raise FlareAIKitError(msg) from e

    pipeline = VectorRAGPipeline(retriever=retriever, reranker=reranker)
    logger.info(
        "Vector RAG pipeline created successfully.",
        has_reranker=reranker is not None,
    )

    return pipeline
