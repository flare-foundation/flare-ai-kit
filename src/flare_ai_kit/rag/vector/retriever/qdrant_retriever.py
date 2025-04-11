"""VectorDB retriever using Qdrant."""

from typing import override

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchText,
    PointStruct,
    Record,
    ScoredPoint,
    VectorParams,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from flare_ai_kit.common import (
    Chunk,
    EmbeddingsError,
    SemanticSearchResult,
    VectorDbError,
)
from flare_ai_kit.rag.vector.embedding import BaseEmbedding
from flare_ai_kit.rag.vector.settings_models import VectorDbSettingsModel

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
        settings: VectorDbSettingsModel,
    ) -> None:
        """
        Initialize the QdrantRetriever.

        :param client: An initialized QdrantClient instance.
        :param retriever_config: Configuration object containing settings like
                                 collection_name, vector_size, embedding models.
        :param embedding_client: An embedding client (e.g., GeminiEmbedding).
        """
        self.client = qdrant_client
        self.embedding_client = embedding_client
        self.vector_size = settings.qdrant_vector_size
        self.batch_size = settings.qdrant_batch_size

    def _create_collection(self, collection_name: str, vector_size: int) -> None:
        """
        Creates or recreates a Qdrant collection.

        Warning: This will delete the collection if it already exists.

        :param collection_name: Name of the collection.
        :param vector_size: Dimension of the vectors.
        """
        try:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(
                "Successfully created/recreated collection",
                collection_name=collection_name,
                vector_size=vector_size,
            )
        except Exception as e:
            msg = "Failed to create/recreate Qdrant collection"
            logger.exception(
                msg,
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorDbError(msg) from e

    def _create_point(self, element: Chunk, idx: int) -> PointStruct | None:
        title = None
        try:
            contents = element.text
            title = element.metadata.original_filepath
            # Calculate embedding using Gemini
            embedding = self.embedding_client.embed_content(
                contents=contents, title=title, task_type="RETRIEVAL_DOCUMENT"
            )

        except Exception:
            logger.exception(
                "Error processing document for embedding.",
                index=idx,
                title=title,
            )
            return None

        if not embedding or len(embedding) == 0:
            msg = f"Empty embeddings returned for document {idx}"
            raise EmbeddingsError(msg)

        # Prepare payload, ensuring metadata is serializable
        payload = {
            "text": contents,
            "filename": title,
            "metadata": {
                "original_filepath": element.metadata.original_filepath,
                "chunk_id": element.metadata.chunk_id,
                "start_index": element.metadata.start_index,
                "end_index": element.metadata.end_index,
            },
        }

        return PointStruct(
            id=f"{element.metadata.original_filepath}_{element.metadata.chunk_id}",
            vector=embedding[0],  # Use the first embedding
            payload=payload,
        )

    @retry(
        retry=retry_if_exception_type(UnexpectedResponse),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            "Retrying upsert after error",
            attempt=retry_state.attempt_number,
            collection_name=retry_state.kwargs.get("collection_name"),
            batch_size=len(retry_state.kwargs.get("points", [])),
        ),
    )
    def _upsert_batch(
        self, collection_name: str, points: list[PointStruct], wait: bool = False
    ) -> None:
        """
        Upserts a batch of points to Qdrant with retry logic.

        Args:
            collection_name: Name of the collection.
            points: List of points to upsert.
            wait: Whether to wait for the upsert to complete.

        Raises:
            VectorDbError: If the upsert fails after retries.

        """
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=wait,
            )
        except Exception as e:
            msg = "Failed to upsert batch after retries"
            logger.exception(
                msg,
                collection_name=collection_name,
                batch_size=len(points),
                error=str(e),
            )
            raise VectorDbError(msg) from e

    def embed_and_upsert(
        self,
        data: list[Chunk],
        collection_name: str,
        continue_on_error: bool = True,
    ) -> tuple[int, int, list[tuple[int, VectorDbError]]]:
        """
        Indexes documents into the Qdrant collection with improved error handling.

        Args:
            data: List of Chunk objects to index.
            collection_name: Name of the collection.
            continue_on_error: If True, continue processing batches even
                               if a batch fails.

        Returns:
            A tuple containing:
                - Number of successfully processed chunks
                - Number of skipped chunks
                - List of (index, exception) tuples for failed chunks

        """
        # Ensure the collection exists (or is recreated)
        self._create_collection(collection_name, self.vector_size)

        points_batch: list[PointStruct] = []
        processed_count = 0
        skipped_count = 0
        failed_indices: list[tuple[int, VectorDbError]] = []
        total_docs = len(data)

        logger.info(
            "Starting indexing process",
            total_documents=total_docs,
            collection_name=collection_name,
            batch_size=self.batch_size,
        )

        for idx, element in enumerate(data):
            # Create point from chunk
            point = self._create_point(
                element=element,
                idx=idx,
            )
            if point is None:
                # If point creation failed, skip to the next element
                skipped_count += 1
                continue

            # Add point to the batch
            points_batch.append(point)

            # Upsert batch if it reaches the desired size
            if len(points_batch) >= self.batch_size:
                try:
                    # Set wait=False for potentially faster async upsert
                    self._upsert_batch(
                        collection_name=collection_name,
                        points=points_batch,
                        wait=False,
                    )
                    processed_count += len(points_batch)
                    logger.info(
                        "Upserted batch to Qdrant",
                        batch_size=len(points_batch),
                        processed_count=processed_count,
                        collection_name=collection_name,
                    )
                except VectorDbError as e:
                    logger.exception(
                        "Failed to upsert batch after retries",
                        collection_name=collection_name,
                        batch_size=len(points_batch),
                    )

                    if not continue_on_error:
                        # Add all documents in the failed batch to the failed indices
                        batch_start_idx = idx - len(points_batch) + 1
                        failed_indices.extend(
                            [(batch_start_idx + i, e) for i in range(len(points_batch))]
                        )
                        return processed_count, skipped_count, failed_indices

                # Clear the batch regardless of success or failure
                points_batch = []

        # Upsert any remaining points
        if points_batch:
            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points_batch,
                    wait=True,  # Wait for the final batch to ensure completion
                )
                processed_count += len(points_batch)
                logger.info(
                    "Upserted final batch to Qdrant",
                    batch_size=len(points_batch),
                    processed_count=processed_count,
                    collection_name=collection_name,
                )
            except VectorDbError as e:
                logger.exception(
                    "Failed to upsert final batch",
                    collection_name=collection_name,
                    batch_size=len(points_batch),
                )
                # Add all documents in the failed batch to the failed indices
                batch_start_idx = total_docs - len(points_batch)
                failed_indices.extend(
                    [(batch_start_idx + i, e) for i in range(len(points_batch))]
                )

        logger.info(
            "Indexing process completed.",
            collection_name=collection_name,
            total_documents=total_docs,
            successfully_processed=processed_count,
            skipped=skipped_count,
        )

        if failed_indices and not continue_on_error:
            logger.warning(
                "Some documents failed to index. Consider retry with failed indices.",
                collection_name=collection_name,
                failed_count=len(failed_indices),
            )

        return processed_count, skipped_count, failed_indices

    @override
    def semantic_search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Perform semantic search using the configured query embedding model.

        :param query: The input query string.
        :param top_k: Number of top results to return.
        :param score_threshold: Optional minimum score threshold for results.
        :return: A list of SemanticSearchResult.
        """
        # Validate inputs to provide clear error messages
        if not query or not query.strip():
            logger.warning("Empty query provided for semantic search")
            return []

        if not collection_name:
            logger.warning("Empty collection name provided for semantic search")
            return []

        try:
            # Convert the query into a vector embedding
            query_vector = self.embedding_client.embed_content(
                contents=query,
                task_type="RETRIEVAL_QUERY",
                title=None,
            )

            if not query_vector or len(query_vector) == 0:
                logger.warning("Empty embedding generated for query", query=query)
                return []

            # Search Qdrant for similar vectors.
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector[0],
                limit=top_k,
                score_threshold=score_threshold,  # Pass threshold if provided
                with_payload=True,  # Ensure payload is returned
            )

            # Process and return results.
            output = convert_points_to_results(search_result)

            logger.info(
                "Semantic search performed successfully.",
                query=query,
                top_k=top_k,
                results_found=len(output),
                collection_name=collection_name,
            )
        except Exception as e:
            logger.exception(
                "Error during semantic search.",
                query=query,
                collection_name=collection_name,
                error=str(e),
            )
            return []
        else:
            return output

    @override
    def keyword_search(
        self, keywords: list[str], collection_name: str, top_k: int = 5
    ) -> list[SemanticSearchResult]:
        """
        Perform keyword search using Qdrant's scroll API.

        Args:
            keywords: A list of keywords to match in the document payload.
            collection_name: The name of the Qdrant collection.
            top_k: Maximum number of results to return.

        Returns:
            A list of SemanticSearchResult objects containing the search results.

        """
        if not keywords:
            logger.warning("No keywords provided for keyword search.")
            return []

        # Build filter conditions using MatchText for each keyword.
        keyword_conditions = [
            FieldCondition(key="text", match=MatchText(text=keyword))
            for keyword in keywords
        ]

        # Build a filter using a "should" clause (OR logic).
        scroll_filter = Filter(should=keyword_conditions)  # pyright: ignore[reportArgumentType]

        try:
            # Use client.scroll to retrieve matching points.
            points = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=top_k,
            )[0]
        except Exception as e:
            logger.exception(
                "Error during keyword search.",
                keywords=keywords,
                collection_name=collection_name,
                error=str(e),
            )
            return []

        # Process and return results.
        output = convert_points_to_results(points, default_score=1.0)

        logger.info(
            "Keyword search performed successfully.",
            keywords=keywords,
            top_k=top_k,
            results_found=len(output),
            collection_name=collection_name,
        )
        return output
