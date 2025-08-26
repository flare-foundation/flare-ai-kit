"""VectorDB retriever using Qdrant."""

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchText,
    Record,
    ScoredPoint,
    VectorParams,
)

from flare_ai_kit.common import (
    SemanticSearchResult,
)
from flare_ai_kit.rag.vector.embedding import BaseEmbedding
from flare_ai_kit.rag.vector.settings import VectorDbSettings

from .base import BaseRetriever

# Initialize logger
logger = structlog.get_logger(__name__)


def convert_points_to_results(
    points: list[ScoredPoint] | list[Record], default_score: float = 1.0
) -> list[SemanticSearchResult]:
    """
    Convert a list of Qdrant PointStruct objects to SemanticSearchResult instances.

    Args:
        points: A list of Qdrant PointStruct objects.
        default_score: A fallback score value if a point doesn't have one.

    Returns:
        A list of SemanticSearchResult objects.

    """
    results: list[SemanticSearchResult] = []
    for point in points:
        payload = point.payload if point.payload is not None else {}
        text = payload.get("text", "")
        metadata = {k: v for k, v in payload.items() if k != "text"}
        # Use the point's score if available; otherwise, use the default score.
        score = getattr(point, "score", default_score)
        result = SemanticSearchResult(text=text, score=score, metadata=metadata)
        results.append(result)
    return results


class QdrantRetriever(BaseRetriever):
    """Interacting with Qdrant VectorDB, semantic search and indexing."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_client: BaseEmbedding,
        settings: VectorDbSettings,
    ) -> None:
        """
        Initialize the QdrantRetriever.

        Args:
            qdrant_client (QdrantClient): An initialized QdrantClient instance.
            embedding_client (BaseEmbedding): An embedding client
                (e.g., GeminiEmbedding).

            settings (VectorDbSettings): Configuration object containing
                settings like collection_name, vector_size, embedding models.


        """
        self.client = qdrant_client
        self.embedding_client = embedding_client
        self.vector_size = settings.qdrant_vector_size
        self.batch_size = settings.qdrant_batch_size
        self.collection_name = (
            settings.embeddings_model
        )  # You may want to use a dedicated collection name field

    def _create_collection(self, collection_name: str, vector_size: int) -> None:
        """
        Create or recreate a Qdrant collection.

        Warning: This will delete the collection if it already exists.

        Args:
            collection_name (str): Name of the collection.
            vector_size (int): Dimension of the vectors.

        """
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[SemanticSearchResult]:
        """

        Embed the query, search Qdrant for top-k similar vectors.

        Return SemanticSearchResult objects.


        Args:
            query (str): The search query string.
            top_k (int): Number of top results to return.

        Returns:
            list[SemanticSearchResult]: List of documents with content and metadata.

        """
        query_vec = self.embedding_client.embed_content(query)[0]
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vec,
            limit=top_k,
            with_payload=True,
        )
        return convert_points_to_results(search_result)

    def semantic_search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Perform semantic search using vector embeddings.

        Args:
            query (str): The input query string.
            collection_name (str): The name of the Qdrant collection.
            top_k (int): Number of top results to return.

            score_threshold (float | None): Optional minimum score threshold
                for results.


        Returns:
            list[SemanticSearchResult]: List of documents with content and metadata.

        """
        if not query or not query.strip():
            return []
        if not collection_name:
            return []
        query_vector = self.embedding_client.embed_content(query)[0]
        search_result = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return convert_points_to_results(search_result)

    def keyword_search(
        self, keywords: list[str], collection_name: str, top_k: int = 5
    ) -> list[SemanticSearchResult]:
        """
        Perform keyword search using Qdrant's scroll API.

        Args:
            keywords (List[str]): A list of keywords to match in the document payload.
            collection_name (str): The name of the Qdrant collection.
            top_k (int): Maximum number of results to return.

        Returns:
            list[SemanticSearchResult]: List of documents with content and metadata.

        """
        if not keywords:
            return []

        # Build filter conditions using MatchText for each keyword.
        keyword_conditions: list[FieldCondition] = [
            FieldCondition(key="text", match=MatchText(text=keyword))
            for keyword in keywords
        ]

        # Build a filter using a "should" clause (OR logic).
        scroll_filter = Filter(should=keyword_conditions)  # pyright: ignore[reportArgumentType]

        try:
            # Use client.scroll to retrieve matching points.
            points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=top_k,
            )
        except Exception as e:
            logger.exception(
                "Error during keyword search.",
                keywords=keywords,
                collection_name=collection_name,
                error=str(e),
            )
            return []

        # Convert results to SemanticSearchResult
        results: list[SemanticSearchResult] = []
        for hit in points:
            payload = hit.payload or {}
            results.append(
                SemanticSearchResult(
                    text=payload.get("text", ""),
                    metadata={k: v for k, v in payload.items() if k != "text"},
                    score=1.0,  # Keyword search doesn't provide a similarity score
                )
            )
        logger.info(
            "Keyword search performed successfully.",
            keywords=keywords,
            top_k=top_k,
            results_found=len(results),
        )
        return results
